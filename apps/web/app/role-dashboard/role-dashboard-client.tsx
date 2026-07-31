"use client";

import Link from "next/link";
import * as React from "react";
import { Calculator, ChevronDown, ChevronRight, ClipboardList, FileSpreadsheet, Loader2, RefreshCw, Save } from "lucide-react";
import { toast } from "sonner";

import { EmptyState } from "@/components/app-shell/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  API_BASE,
  GRANULAR_ENQUIRY_WORKFLOW_ACTIONS,
  GRANULAR_WORKFLOW,
  GRANULAR_WORKFLOW_STATE_INFO,
  Quote,
  advanceEnquiryWorkflow,
  canonicalGranularStep,
  exportEnquiryRegister,
  getCurrentAppUserRemote,
  getQuote,
  lastWorkflowActionOf,
  listQuotes,
  patchQuote,
  reviewLoopThread,
  workflowNoteRequirement,
} from "@/lib/api";
import { isUnclassifiedSummaryItem } from "@/lib/extraction-summary";
import {
  PRICING_FORMULA_META_KEY,
  PricingFormulaRow,
  buildPricingFormulaRecord,
  pricingFormulaCoverage,
  pricingFormulaRows,
  readPricingFormulas,
} from "@/lib/pricing-formulas";
import { PricingFormulaPanel } from "@/components/quotes/pricing-formula-panel";
import { WORK_NOTIFICATION_EVENT } from "@/components/providers/notification-listener";
import { getCurrentAppUser, setCurrentAppUser } from "@/lib/auth/users";

// Which granular state each role OWNS (mirrors GRANULAR_STAGE_OWNER_ROLES in
// apps/api/app/services/enquiry_workflow.py). A role's dashboard shows ONLY
// enquiries currently parked at a state it owns.
const STEP_OWNER_ROLES: Record<string, string[]> = {
  enquiry_received: ["estimation"],
  spec_check: ["estimation"],
  query_raised_to_customer: ["sales"],
  // Technical review is the manager's step. This is the ONLY state management
  // owns here: the backend lets management act on every step, but listing them
  // all would make the manager's queue every open enquiry instead of the work
  // actually waiting on him.
  technical_review_pending: ["management"],
  sent_for_pricing: ["admin"],
  pricing_decision: ["estimation"],
  pricing_submitted: ["sales", "admin"],
  quotation_generated: ["sales"],
  quotation_sent_to_customer: ["sales"],
};

const STEP_LABELS: Record<string, string> = Object.fromEntries(
  Object.entries(GRANULAR_WORKFLOW_STATE_INFO).map(([id, info]) => [id, info.label]),
);

const DEFAULT_STEP = "enquiry_received";

// The pricing desk (Ashwin sir) writes a formula against every spec here...
const PRICING_DESK_STEP = "sent_for_pricing";
// ...and it stays visible, read-only, to the teams that work off it: estimation
// prices each line against its spec formula, then hands it on for generation.
const FORMULA_STEPS = new Set([PRICING_DESK_STEP, "pricing_decision", "pricing_submitted"]);
// Releasing to estimation only makes sense once every spec carries a formula
// (mirrors the require_pricing_formulas gate on the API transition).
const FORMULA_GATED_ACTION = "open_pricing";

function currentStep(quote: Quote): string {
  const meta = (quote.stage_meta ?? {}) as Record<string, unknown>;
  const granular = (meta.granular_workflow ?? {}) as Record<string, unknown>;
  // Retired 13-step ids read as the surviving 6-step state.
  return canonicalGranularStep(String(granular.current_stage || meta.workflow_stage || DEFAULT_STEP));
}

// The one-line note the previous team left on the last handoff.
function workflowNote(quote: Quote): string {
  const meta = (quote.stage_meta ?? {}) as Record<string, unknown>;
  return typeof meta.workflow_comment === "string" ? meta.workflow_comment : "";
}

function lastWorkflowAction(quote: Quote): string {
  return lastWorkflowActionOf(quote.stage_meta as Record<string, unknown> | undefined);
}

// The reviewer's error list / estimation's reply, oldest first — the round trips
// this enquiry has already made through technical review.
function reviewThread(quote: Quote) {
  return reviewLoopThread(quote.stage_meta as Record<string, unknown> | undefined).filter((entry) => entry.comment);
}

// How many times the reviewer has sent this enquiry back so far.
function returnCount(quote: Quote): number {
  return reviewLoopThread(quote.stage_meta as Record<string, unknown> | undefined)
    .filter((entry) => entry.action === "return_spec_errors").length;
}

// The banner to show on a queue row: what the previous team is waiting on, what
// the reviewer asked estimation to fix, or — on the reviewer's own queue — what
// estimation says it changed since the last time he sent it back.
function rowAlert(quote: Quote, step: string): string {
  const note = workflowNote(quote);
  if (!note) return "";
  if (step === "query_raised_to_customer") return `⚠ Missing: ${note}`;
  if (step === "spec_check" && lastWorkflowAction(quote) === "return_spec_errors") {
    return `⚠ Returned by review: ${note}`;
  }
  if (step === "technical_review_pending" && lastWorkflowAction(quote) === "send_to_technical_review") {
    const rounds = returnCount(quote);
    return rounds ? `↻ Re-submitted (round ${rounds + 1}) — changed: ${note}` : `From estimation: ${note}`;
  }
  return "";
}

const REVIEW_THREAD_LABELS: Record<string, string> = {
  send_to_technical_review: "Estimation → review",
  return_spec_errors: "Review → estimation (errors)",
  return_tr_spec: "Review cleared",
};

// The full back-and-forth, so the reviewer re-checking a spec can see what he
// flagged last round and estimation can see every note against it.
function ReviewThread({ quote }: { quote: Quote }) {
  const thread = reviewThread(quote);
  if (thread.length < 2) return null;
  return (
    <details className="mt-1 max-w-72">
      <summary className="cursor-pointer text-xs text-muted-foreground">Review thread ({thread.length})</summary>
      <div className="mt-1 space-y-1 border-l pl-2">
        {thread.map((entry, index) => (
          <div key={`${entry.at}-${index}`} className="text-xs text-muted-foreground">
            <span className="font-medium text-foreground">{REVIEW_THREAD_LABELS[entry.action] ?? entry.action}</span>
            {entry.by ? ` · ${entry.by}` : ""}
            {entry.at ? ` · ${new Date(entry.at).toLocaleString("en-GB")}` : ""}
            <div>{entry.comment}</div>
          </div>
        ))}
      </div>
    </details>
  );
}

const asText = (value: unknown): string =>
  typeof value === "string" ? value.trim() : typeof value === "number" ? String(value) : "";

const titleCase = (value: string): string => (value ? value.charAt(0).toUpperCase() + value.slice(1) : "");

function dateText(value: unknown): string {
  const text = asText(value);
  if (!text) return "";
  const parsed = new Date(text);
  return Number.isNaN(parsed.getTime()) ? text : parsed.toLocaleDateString("en-GB");
}

function moneyText(value: unknown, currency: string): string {
  const num = Number(value);
  if (!Number.isFinite(num) || num === 0) return "";
  return `${currency || "INR"} ${num.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

/**
 * Everything about the enquiry that a pricing decision needs without opening
 * the record: who it is for, what kind of enquiry it is, how big it is and
 * when it is due.
 */
function enquirySummary(quote: Quote, detail: Quote | undefined, specs: PricingFormulaRow[]): Array<[string, string]> {
  const meta = (quote.stage_meta ?? {}) as Record<string, unknown>;
  const qd = { ...((detail?.quote_data ?? {}) as Record<string, unknown>), ...(quote.quote_data ?? {}) };
  const currency = asText(qd.currency) || "INR";
  const enquiryType = [titleCase(asText(meta.market_type)), titleCase(asText(meta.bid_type))].filter(Boolean).join(" · ");
  const location = [asText(meta.city), asText(meta.country)].filter(Boolean).join(", ");
  const lineItems = quote.n_items || detail?.items?.length || 0;
  const totalQty = specs.reduce((total, row) => total + row.qty, 0);
  return (
    [
      ["Enquiry type", enquiryType],
      ["Customer enq no", asText(qd.customer_enq_no) || asText(meta.customer_enq_no)],
      ["Quote no", asText(quote.quote_no)],
      ["Sales owner", asText(meta.owner_name) || asText(meta.owner_id)],
      ["EPC / end user", asText(meta.epc_name)],
      ["Location", location],
      ["Line items", lineItems ? String(lineItems) : ""],
      ["Specs to price", specs.length ? String(specs.length) : ""],
      ["Total qty", totalQty ? String(Number(totalQty.toFixed(3))) : ""],
      ["Est. value", moneyText(quote.estimated_quote_value, currency)],
      ["Currency", currency],
      ["Due date", dateText(meta.due_date)],
      ["Priority", titleCase(asText(meta.priority))],
      ["Delivery / lead time", asText(qd.delivery)],
      ["Payment terms", asText(qd.payment_terms)],
      ["Received", dateText(quote.created_at)],
    ] as Array<[string, string]>
  ).filter(([, value]) => value);
}

// Whether this action needs a note before it will go through — the reviewer's
// error list always, estimation's reply only when re-submitting a returned spec
// (mirrors require_comment / require_comment_after on the backend transitions).
function noteRequiredFor(quote: Quote, action: string): string {
  return workflowNoteRequirement(action, lastWorkflowAction(quote));
}

// Per-step placeholder for the row's note box. The pricing desk gets none: its
// input is the per-spec formula table on the row, not one free-text note.
const NOTE_PLACEHOLDER: Record<string, string> = {
  technical_review_pending: "Note for estimation — required when returning with errors",
  spec_check: "Note for the reviewer — what you changed",
};

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

type FormulaDraft = Record<string, { formula?: string; note?: string }>;

function applyDraft(rows: PricingFormulaRow[], draft: FormulaDraft | undefined): PricingFormulaRow[] {
  if (!draft) return rows;
  return rows.map((row) => ({
    ...row,
    formula: draft[row.item]?.formula ?? row.formula,
    note: draft[row.item]?.note ?? row.note,
  }));
}

export function RoleDashboardClient() {
  const [quotes, setQuotes] = React.useState<Quote[]>([]);
  const [currentUser, setCurrentUser] = React.useState(() => getCurrentAppUser());
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState<string | null>(null);
  const [registerExporting, setRegisterExporting] = React.useState(false);
  // Per-row note: the reviewer's error note.
  const [rowNotes, setRowNotes] = React.useState<Record<string, string>>({});
  // Full records (the queue list carries no line items) for the rows that show
  // the quotation summary, plus the unsaved formula edits against them.
  const [details, setDetails] = React.useState<Record<string, Quote>>({});
  const [detailsLoading, setDetailsLoading] = React.useState<Record<string, boolean>>({});
  const [expanded, setExpanded] = React.useState<string | null>(null);
  const [drafts, setDrafts] = React.useState<Record<string, FormulaDraft>>({});

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

  // The list endpoint returns summaries (no line items), so the quotation
  // summary is rebuilt from the full record — fetched for the pricing-stage
  // rows only, and refreshed whenever the queue reloads.
  const loadDetails = React.useCallback(async (requested: string[]) => {
    // A deep queue is fetched in the order it is shown; the rest fill in on the
    // next reload rather than firing dozens of requests at once.
    const ids = requested.slice(0, 30);
    if (!ids.length) return;
    setDetailsLoading((prev) => ({ ...prev, ...Object.fromEntries(ids.map((id) => [id, true])) }));
    const loaded = await Promise.all(
      ids.map(async (id) => {
        try {
          return await getQuote(id);
        } catch {
          return null;
        }
      }),
    );
    setDetails((prev) => {
      const next = { ...prev };
      loaded.forEach((quote) => {
        if (quote) next[quote.id] = quote;
      });
      return next;
    });
    setDetailsLoading((prev) => ({ ...prev, ...Object.fromEntries(ids.map((id) => [id, false])) }));
  }, []);

  const refresh = React.useCallback(async (options?: { silent?: boolean }) => {
    if (!options?.silent) setLoading(true);
    try {
      const [current, quoteData] = await Promise.all([getCurrentAppUserRemote(), listQuotes()]);
      setCurrentAppUser(current);
      setCurrentUser(current);
      setQuotes(quoteData);
      const mine = ownedSteps(current.role);
      const needsSummary = quoteData
        .filter((quote) => mine.has(currentStep(quote)) && FORMULA_STEPS.has(currentStep(quote)))
        .map((quote) => quote.id);
      void loadDetails(needsSummary);
    } catch (error) {
      if (!options?.silent) toast.error(error instanceof Error ? error.message : "Could not load your queue");
    } finally {
      if (!options?.silent) setLoading(false);
    }
  }, [loadDetails]);

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

  // The quotation summary + formulas for every pricing-stage row in the queue,
  // rebuilt from the current line items with unsaved edits laid over the top.
  const formulaRowsByQuote = React.useMemo(() => {
    const result: Record<string, PricingFormulaRow[]> = {};
    queue.forEach((quote) => {
      if (!FORMULA_STEPS.has(currentStep(quote))) return;
      const detail = details[quote.id];
      if (!detail) return;
      result[quote.id] = applyDraft(pricingFormulaRows(detail.items ?? [], readPricingFormulas(detail)), drafts[quote.id]);
    });
    return result;
  }, [queue, details, drafts]);

  function updateFormula(quoteId: string, item: string, field: "formula" | "note", value: string) {
    setDrafts((prev) => ({
      ...prev,
      [quoteId]: { ...prev[quoteId], [item]: { ...prev[quoteId]?.[item], [field]: value } },
    }));
  }

  async function saveFormulas(quote: Quote, options?: { silent?: boolean }): Promise<boolean> {
    const detail = details[quote.id];
    const rows = formulaRowsByQuote[quote.id];
    if (!detail || !rows) {
      toast.error("The quotation summary is still loading — try again in a moment");
      return false;
    }
    setBusy(`${quote.id}:formulas`);
    try {
      const record = buildPricingFormulaRecord(
        detail.items ?? [],
        rows,
        currentUser.name || currentUser.id,
        new Date().toISOString(),
      );
      // Only the formula key is sent: the API merges it into the record's
      // stage_meta, so a concurrent edit elsewhere on the enquiry is not lost.
      const saved = await patchQuote(quote.id, {
        stage_meta: { [PRICING_FORMULA_META_KEY]: record },
      } as Partial<Quote>);
      setDetails((prev) => ({ ...prev, [quote.id]: saved }));
      setDrafts((prev) => ({ ...prev, [quote.id]: {} }));
      if (!options?.silent) toast.success("Pricing formulas saved");
      return true;
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save the pricing formulas");
      return false;
    } finally {
      setBusy(null);
    }
  }

  async function runAction(quote: Quote, action: string) {
    const note = (rowNotes[quote.id] ?? "").trim();
    const noteRequired = noteRequiredFor(quote, action);
    if (noteRequired && !note) {
      toast.error(noteRequired);
      return;
    }
    // Releasing to estimation carries the formulas with it — flush any unsaved
    // edits first so what estimation receives is what is on screen.
    if (action === FORMULA_GATED_ACTION) {
      const rows = formulaRowsByQuote[quote.id] ?? [];
      const coverage = pricingFormulaCoverage(rows);
      if (!coverage.complete) {
        toast.error(`Enter a pricing formula against all ${coverage.total} spec(s) before sending to estimation`);
        setExpanded(quote.id);
        return;
      }
      if (Object.keys(drafts[quote.id] ?? {}).length && !(await saveFormulas(quote, { silent: true }))) return;
    }
    setBusy(`${quote.id}:${action}`);
    try {
      await advanceEnquiryWorkflow(quote.id, action, note);
      setRowNotes((prev) => ({ ...prev, [quote.id]: "" }));
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
                  <TableHead>Enquiry details</TableHead>
                  <TableHead>Stage</TableHead>
                  <TableHead>Note</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {queue.map((quote) => {
                  const step = currentStep(quote);
                  const actions = actionsFor(step, role);
                  const detail = details[quote.id];
                  const formulaRows = formulaRowsByQuote[quote.id] ?? [];
                  const coverage = pricingFormulaCoverage(formulaRows);
                  const summary = enquirySummary(quote, detail, formulaRows);
                  const notePlaceholder = NOTE_PLACEHOLDER[step];
                  const showsFormulas = FORMULA_STEPS.has(step);
                  const pricingDesk = step === PRICING_DESK_STEP;
                  const isExpanded = expanded === quote.id;
                  const dirty = Object.keys(drafts[quote.id] ?? {}).length > 0;
                  const unmatchedLines = (detail?.items ?? [])
                    .map((item, index) => (isUnclassifiedSummaryItem(item) ? index + 1 : 0))
                    .filter(Boolean);
                  return (
                    <React.Fragment key={quote.id}>
                      <TableRow className={isExpanded ? "border-b-0" : undefined}>
                        <TableCell className="align-top">
                          <Link href={quoteHref(quote)} className="font-medium hover:underline">
                            {quote.customer || "Customer not added"}
                          </Link>
                          <div className="max-w-56 truncate text-xs text-muted-foreground">
                            {quote.project_ref || quote.quote_no || "No reference added"}
                          </div>
                          {rowAlert(quote, step) ? (
                            <div className="mt-1 max-w-72 text-xs text-amber-700 dark:text-amber-300" title={workflowNote(quote)}>
                              {rowAlert(quote, step)}
                            </div>
                          ) : null}
                          <ReviewThread quote={quote} />
                        </TableCell>
                        <TableCell className="align-top">
                          {summary.length ? (
                            <div className="grid max-w-2xl gap-x-4 gap-y-0.5 text-xs sm:grid-cols-2 xl:grid-cols-3">
                              {summary.map(([label, value]) => (
                                <div key={label} className="truncate" title={`${label}: ${value}`}>
                                  <span className="text-muted-foreground">{label}: </span>
                                  <span className="font-medium">{value}</span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">No details added yet</span>
                          )}
                        </TableCell>
                        <TableCell className="align-top">
                          <Badge variant="outline">{STEP_LABELS[step] ?? step.replaceAll("_", " ")}</Badge>
                        </TableCell>
                        <TableCell className="align-top">
                          {notePlaceholder ? (
                            <textarea
                              value={rowNotes[quote.id] ?? ""}
                              onChange={(event) => setRowNotes((prev) => ({ ...prev, [quote.id]: event.target.value }))}
                              placeholder={notePlaceholder}
                              className="min-h-[52px] w-56 rounded-md border border-input bg-background px-2 py-1.5 text-xs outline-none focus:ring-2 focus:ring-ring"
                            />
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className="align-top">
                          <div className="flex flex-wrap gap-2">
                            {showsFormulas ? (
                              <Button
                                variant={pricingDesk && !coverage.complete ? "default" : "outline"}
                                size="sm"
                                onClick={() => setExpanded(isExpanded ? null : quote.id)}
                                title={pricingDesk ? "Enter the pricing formula against every spec" : "See the pricing formula for every spec"}
                              >
                                {isExpanded ? <ChevronDown className="mr-1 h-4 w-4" /> : <ChevronRight className="mr-1 h-4 w-4" />}
                                <Calculator className="mr-1 h-4 w-4" />
                                {pricingDesk ? "Pricing formulas" : "Formulas"} ({coverage.filled}/{coverage.total})
                              </Button>
                            ) : null}
                            {actions.map((item) => {
                              const gated = item.action === FORMULA_GATED_ACTION;
                              // Until the record's line items are in, the spec
                              // list is unknown — hold the release rather than
                              // let it fail the same check on the API.
                              const blocked = gated && (!coverage.complete || !detail);
                              const noteRequired = noteRequiredFor(quote, item.action);
                              const noteMissing = Boolean(noteRequired) && !(rowNotes[quote.id] ?? "").trim();
                              return (
                                <Button
                                  key={item.action}
                                  variant="secondary"
                                  size="sm"
                                  disabled={busy !== null || blocked || noteMissing}
                                  title={
                                    blocked
                                      ? detail
                                        ? `Enter a pricing formula against all ${coverage.total} spec(s) first`
                                        : "Loading the quotation summary…"
                                      : noteMissing
                                        ? noteRequired
                                        : undefined
                                  }
                                  onClick={() => runAction(quote, item.action)}
                                >
                                  {item.label}
                                </Button>
                              );
                            })}
                            <Button asChild variant="ghost" size="sm">
                              <Link href={quoteHref(quote)}>{PRICING_SCREEN_STEPS.has(step) ? "Open pricing" : "Open"}</Link>
                            </Button>
                          </div>
                          {pricingDesk && detail && !coverage.complete ? (
                            <div className="mt-1 max-w-64 text-xs text-amber-700 dark:text-amber-300">
                              {`${coverage.missing.length} spec(s) still need a formula.`}
                            </div>
                          ) : null}
                          {pricingDesk && detail && coverage.total === 0 ? (
                            <div className="mt-1 max-w-64 text-xs text-muted-foreground">
                              No priceable specs on this enquiry yet.
                            </div>
                          ) : null}
                        </TableCell>
                      </TableRow>
                      {isExpanded ? (
                        <TableRow className="hover:bg-transparent">
                          <TableCell colSpan={5} className="bg-muted/20">
                            <PricingFormulaPanel
                              rows={formulaRows}
                              editable={pricingDesk}
                              loading={Boolean(detailsLoading[quote.id]) && !detail}
                              stored={readPricingFormulas(detail)}
                              unmatchedLines={unmatchedLines}
                              onChange={(item, field, value) => updateFormula(quote.id, item, field, value)}
                            />
                            <div className="flex flex-wrap items-center gap-2 px-1 pb-2 text-xs text-muted-foreground">
                              {pricingDesk ? (
                                <>
                                  <Button
                                    size="sm"
                                    variant="secondary"
                                    disabled={busy !== null || !dirty}
                                    onClick={() => saveFormulas(quote)}
                                  >
                                    {busy === `${quote.id}:formulas` ? (
                                      <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                                    ) : (
                                      <Save className="mr-1 h-4 w-4" />
                                    )}
                                    Save formulas
                                  </Button>
                                  <span>
                                    {dirty ? "Unsaved changes." : "Saved."} The formulas travel with the enquiry to estimation, which
                                    prices each line against its spec and raises the process for those materials.
                                  </span>
                                </>
                              ) : (
                                <span>
                                  Pricing formulas set by the pricing desk. Price each line on the quotation sheet against its spec
                                  formula, then raise the process for the enquiry materials.
                                </span>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ) : null}
                    </React.Fragment>
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