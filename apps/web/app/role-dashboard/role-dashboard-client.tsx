"use client";

import Link from "next/link";
import * as React from "react";
import { ClipboardList, FileSpreadsheet, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { EmptyState } from "@/components/app-shell/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  API_BASE,
  GRANULAR_ENQUIRY_WORKFLOW_ACTIONS,
  GRANULAR_ENQUIRY_WORKFLOW_STEPS,
  GRANULAR_WORKFLOW,
  Quote,
  advanceEnquiryWorkflow,
  exportEnquiryRegister,
  getCurrentAppUserRemote,
  listQuotes,
} from "@/lib/api";
import { WORK_NOTIFICATION_EVENT } from "@/components/providers/notification-listener";
import { getCurrentAppUser, setCurrentAppUser } from "@/lib/auth/users";

// Which granular stage each role OWNS (mirrors GRANULAR_STAGE_OWNER_ROLES in
// apps/api/app/services/enquiry_workflow.py). A role's dashboard shows ONLY
// enquiries currently parked at a stage it owns.
const STEP_OWNER_ROLES: Record<string, string[]> = {
  enquiry_received: ["estimation"],
  forwarded_to_estimation: ["estimation"],
  spec_check: ["estimation"],
  query_raised_to_customer: ["sales"],
  converted_to_ggpl_format: ["estimation"],
  gasket_type_check: ["estimation"],
  technical_review_pending: ["technical"],
  combined_spec_review: ["estimation"],
  sent_for_pricing: ["admin"],
  pricing_decision: ["estimation"],
  pricing_submitted: ["sales", "admin"],
  quotation_generated: ["sales"],
  quotation_sent_to_customer: ["sales"],
};

const STEP_LABELS: Record<string, string> = Object.fromEntries(
  GRANULAR_ENQUIRY_WORKFLOW_STEPS.map((step) => [step.id, step.label]),
);

const DEFAULT_STEP = "enquiry_received";

function currentStep(quote: Quote): string {
  const meta = (quote.stage_meta ?? {}) as Record<string, unknown>;
  const granular = (meta.granular_workflow ?? {}) as Record<string, unknown>;
  return String(granular.current_stage || meta.workflow_stage || DEFAULT_STEP);
}

// The one-line note estimation left when sending an enquiry back to sales.
function workflowNote(quote: Quote): string {
  const meta = (quote.stage_meta ?? {}) as Record<string, unknown>;
  return typeof meta.workflow_comment === "string" ? meta.workflow_comment : "";
}

// From pricing onward the work happens on the Quotations screen (pricing sheet,
// generate, PDF) — link those rows there instead of the enquiry editor.
const PRICING_SCREEN_STEPS = new Set([
  "sent_for_pricing",
  "pricing_decision",
  "pricing_submitted",
  "quotation_generated",
  "quotation_sent_to_customer",
]);

function quoteHref(quote: Quote): string {
  return PRICING_SCREEN_STEPS.has(currentStep(quote)) ? `/quotes/final?quote=${quote.id}` : `/quotes?quote=${quote.id}`;
}

function ownedSteps(role: string): Set<string> {
  return new Set(
    Object.entries(STEP_OWNER_ROLES)
      .filter(([, roles]) => roles.includes(role))
      .map(([step]) => step),
  );
}

// Workflow actions available for a given step + role (mirrors the backend gate:
// current step in `from` AND role allowed, with admin bypass).
function actionsFor(step: string, role: string) {
  return GRANULAR_ENQUIRY_WORKFLOW_ACTIONS.filter(
    (item) =>
      (item.from as readonly string[]).includes(step) &&
      (role === "admin" || (item.roles as readonly string[]).includes(role)),
  );
}

export function RoleDashboardClient() {
  const [quotes, setQuotes] = React.useState<Quote[]>([]);
  const [currentUser, setCurrentUser] = React.useState(() => getCurrentAppUser());
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState<string | null>(null);
  const [registerExporting, setRegisterExporting] = React.useState(false);

  async function downloadEnquiryRegister() {
    setRegisterExporting(true);
    try {
      const response = await exportEnquiryRegister();
      const url = response.signed_url.startsWith("http") ? response.signed_url : `${API_BASE}${response.signed_url}`;
      window.open(url, "_blank");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not download the enquiry register");
    } finally {
      setRegisterExporting(false);
    }
  }

  const refresh = React.useCallback(async (options?: { silent?: boolean }) => {
    if (!options?.silent) setLoading(true);
    try {
      const [current, quoteData] = await Promise.all([getCurrentAppUserRemote(), listQuotes()]);
      setCurrentAppUser(current);
      setCurrentUser(current);
      setQuotes(quoteData);
    } catch (error) {
      if (!options?.silent) toast.error(error instanceof Error ? error.message : "Could not load your queue");
    } finally {
      if (!options?.silent) setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  // Live updates: the global NotificationListener re-broadcasts every pushed
  // work notification as a window event — reload the queue in place so new
  // work appears without a manual refresh.
  React.useEffect(() => {
    const onWorkNotification = () => {
      void refresh({ silent: true });
    };
    window.addEventListener(WORK_NOTIFICATION_EVENT, onWorkNotification);
    return () => window.removeEventListener(WORK_NOTIFICATION_EVENT, onWorkNotification);
  }, [refresh]);

  const role = currentUser.role;
  const mine = ownedSteps(role);
  // Show only enquiries parked at a stage this role owns. listQuotes() is already
  // role-filtered server-side; this is the presentation-layer view of that.
  const queue = React.useMemo(
    () => quotes.filter((quote) => mine.has(currentStep(quote))),
    [quotes, mine],
  );
  // Completed quotations (generated / sent) — a read-only section for admin & sales.
  const showCompleted = role === "admin" || role === "sales" || role === "management";
  const completed = React.useMemo(
    () => quotes.filter((quote) => ["quotation_generated", "quotation_sent_to_customer"].includes(currentStep(quote))),
    [quotes],
  );

  async function runAction(quote: Quote, action: string) {
    setBusy(`${quote.id}:${action}`);
    try {
      await advanceEnquiryWorkflow(quote.id, action);
      toast.success("Workflow updated");
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update workflow");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-3">
        <div>
          <h2 className="text-lg font-semibold">My queue</h2>
          <div className="mt-1 text-xs text-muted-foreground">
            Enquiries waiting on your team ({role}). You can only act on stages your role owns.
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={downloadEnquiryRegister}
            disabled={registerExporting}
            title="Download the enquiry register — one Excel row per enquiry with a generated quotation"
          >
            {registerExporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileSpreadsheet className="mr-2 h-4 w-4" />}
            Register
          </Button>
          <Button variant="outline" size="sm" onClick={() => refresh()} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" /> Refresh
          </Button>
        </div>
      </div>

      {!GRANULAR_WORKFLOW ? (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">
            The granular workflow is disabled. Set NEXT_PUBLIC_ENABLE_GRANULAR_WORKFLOW=true
            (and ENABLE_GRANULAR_WORKFLOW on the API) to activate role-routed queues.
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Assigned to your role</CardTitle>
        </CardHeader>
        <CardContent>
          {queue.length === 0 ? (
            <EmptyState
              icon={ClipboardList}
              title={loading ? "Loading…" : "Nothing waiting on you"}
              body="Enquiries appear here when they reach a stage your role owns."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Customer</TableHead>
                  <TableHead>Stage</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {queue.map((quote) => {
                  const step = currentStep(quote);
                  const actions = actionsFor(step, role);
                  return (
                    <TableRow key={quote.id}>
                      <TableCell>
                        <Link href={quoteHref(quote)} className="font-medium hover:underline">
                          {quote.customer || "Customer not added"}
                        </Link>
                        <div className="max-w-56 truncate text-xs text-muted-foreground">
                          {quote.project_ref || quote.quote_no || "No reference added"}
                        </div>
                        {step === "query_raised_to_customer" && workflowNote(quote) ? (
                          <div className="mt-1 max-w-72 text-xs text-amber-700 dark:text-amber-300" title={workflowNote(quote)}>
                            ⚠ Missing: {workflowNote(quote)}
                          </div>
                        ) : null}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{STEP_LABELS[step] ?? step.replaceAll("_", " ")}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-2">
                          {actions.map((item) => (
                            <Button
                              key={item.action}
                              variant="secondary"
                              size="sm"
                              disabled={busy !== null}
                              onClick={() => runAction(quote, item.action)}
                            >
                              {item.label}
                            </Button>
                          ))}
                          <Button asChild variant="ghost" size="sm">
                            <Link href={quoteHref(quote)}>{PRICING_SCREEN_STEPS.has(step) ? "Open pricing" : "Open"}</Link>
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {showCompleted ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Completed quotations</CardTitle>
          </CardHeader>
          <CardContent>
            {completed.length === 0 ? (
              <div className="py-4 text-sm text-muted-foreground">
                No generated quotations yet. Quotations appear here once they are generated and sent.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Customer</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Open</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {completed.map((quote) => {
                    const step = currentStep(quote);
                    return (
                      <TableRow key={quote.id}>
                        <TableCell>
                          <Link href={`/quotes/final?quote=${quote.id}`} className="font-medium hover:underline">
                            {quote.customer || "Customer not added"}
                          </Link>
                          <div className="max-w-56 truncate text-xs text-muted-foreground">
                            {quote.project_ref || quote.quote_no || "No reference added"}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={step === "quotation_sent_to_customer" ? "secondary" : "outline"}>
                            {step === "quotation_sent_to_customer" ? "Sent to customer" : "Quotation generated"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Button asChild variant="ghost" size="sm">
                            <Link href={`/quotes/final?quote=${quote.id}`}>Open quotation</Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
