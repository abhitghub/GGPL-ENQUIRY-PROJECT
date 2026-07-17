"use client";

import Link from "next/link";
import * as React from "react";
import { ClipboardList, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { EmptyState } from "@/components/app-shell/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  GRANULAR_ENQUIRY_WORKFLOW_ACTIONS,
  GRANULAR_ENQUIRY_WORKFLOW_STEPS,
  GRANULAR_WORKFLOW,
  Quote,
  advanceEnquiryWorkflow,
  getCurrentAppUserRemote,
  listQuotes,
} from "@/lib/api";
import { getCurrentAppUser, setCurrentAppUser } from "@/lib/auth/users";

// Which granular stage each role OWNS (mirrors GRANULAR_STAGE_OWNER_ROLES in
// apps/api/app/services/enquiry_workflow.py). A role's dashboard shows ONLY
// enquiries currently parked at a stage it owns.
const STEP_OWNER_ROLES: Record<string, string[]> = {
  enquiry_received: ["sales"],
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

  const refresh = React.useCallback(async () => {
    setLoading(true);
    try {
      const [current, quoteData] = await Promise.all([getCurrentAppUserRemote(), listQuotes()]);
      setCurrentAppUser(current);
      setCurrentUser(current);
      setQuotes(quoteData);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not load your queue");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const role = currentUser.role;
  const mine = ownedSteps(role);
  // Show only enquiries parked at a stage this role owns. listQuotes() is already
  // role-filtered server-side; this is the presentation-layer view of that.
  const queue = React.useMemo(
    () => quotes.filter((quote) => mine.has(currentStep(quote))),
    [quotes, mine],
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
        <Button variant="outline" size="sm" onClick={refresh} disabled={loading}>
          <RefreshCw className="mr-2 h-4 w-4" /> Refresh
        </Button>
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
                        <Link href={`/quotes?quote=${quote.id}`} className="font-medium hover:underline">
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
                            <Link href={`/quotes?quote=${quote.id}`}>Open</Link>
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
    </div>
  );
}
