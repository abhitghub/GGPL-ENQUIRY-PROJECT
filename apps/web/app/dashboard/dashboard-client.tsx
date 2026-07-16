"use client";

import Link from "next/link";
import * as React from "react";
import { CheckCircle2, ClipboardList, History, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { EmptyState } from "@/components/app-shell/empty-state";
import { MetricCard } from "@/components/app-shell/metric-card";
import { quotationStageBadge } from "@/components/quotes/quotation-stage";
import { formatCurrencyValue, quoteDueState, quoteEstimatedValue, quoteIsHighRisk } from "@/components/quotes/queue-utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DashboardMetrics, Quote, getCurrentAppUserRemote, getDashboardMetrics, listAppUsers, listQuotes } from "@/lib/api";
import { ACCESS_SETTINGS_CHANGED_EVENT, canRole, getAccessSettings } from "@/lib/auth/access-control";
import { getAppUsers, getCurrentAppUser, resolveAppUserName, setCurrentAppUser, USERS_CHANGED_EVENT } from "@/lib/auth/users";

const finalStages = new Set(["quote_prep", "repricing", "sent", "po"]);

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function quoteHref(quote: Quote) {
  if (quote.stage === "po") return `/purchase-orders?quote=${quote.id}`;
  return finalStages.has(quote.stage) ? `/quotes/final?quote=${quote.id}` : `/quotes?quote=${quote.id}`;
}

function dueLabel(quote: Quote) {
  const state = quoteDueState(quote);
  if (state === "delayed") return "Overdue";
  if (state === "today") return "Due today";
  const raw = String(quote.stage_meta?.due_date || "").trim();
  if (!raw) return "No due date";
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? raw : date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function workStepLabel(stage: string) {
  const labels: Record<string, string> = {
    initial: "Review enquiry",
    review: "Review items",
    quote_prep: "Prepare quotation",
    repricing: "Review prices",
    sent: "Sent to customer",
    po: "Order received",
  };
  return labels[stage] ?? stage.replaceAll("_", " ");
}

function nextActionLabel(quote: Quote) {
  if (quote.stage_meta?.clarification_status === "required") return "Check customer information";
  if (quoteIsHighRisk(quote)) return "Review item details";
  if (quoteDueState(quote) === "delayed") return "Update overdue work";
  if (quote.stage === "initial") return "Review enquiry";
  if (quote.stage === "review") return "Review items";
  if (quote.stage === "quote_prep" || quote.stage === "repricing") return "Prepare quotation";
  if (quote.stage === "sent") return "Follow up with customer";
  return "Review progress";
}

export function DashboardClient() {
  const [metrics, setMetrics] = React.useState<DashboardMetrics | null>(null);
  const [quotes, setQuotes] = React.useState<Quote[]>([]);
  const [currentUser, setCurrentUser] = React.useState(() => getCurrentAppUser());
  const [appUsers, setAppUsers] = React.useState(() => getAppUsers());
  const [accessSettings, setAccessSettings] = React.useState(() => getAccessSettings());
  const [loading, setLoading] = React.useState(true);

  async function refresh() {
    setLoading(true);
    try {
      const [current, metricData, quoteData, userData] = await Promise.all([
        getCurrentAppUserRemote(),
        getDashboardMetrics(),
        listQuotes(),
        listAppUsers().catch(() => []),
      ]);
      setCurrentAppUser(current);
      setCurrentUser(current);
      setMetrics(metricData);
      setQuotes(quoteData);
      setAppUsers(userData);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not load My work");
    } finally {
      setLoading(false);
    }
  }

  React.useEffect(() => {
    refresh();
  }, []);

  React.useEffect(() => {
    const refreshUser = () => {
      setCurrentUser(getCurrentAppUser());
      listAppUsers().then(setAppUsers).catch(() => setAppUsers([]));
      setAccessSettings(getAccessSettings());
    };
    window.addEventListener(USERS_CHANGED_EVENT, refreshUser);
    window.addEventListener(ACCESS_SETTINGS_CHANGED_EVENT, refreshUser);
    window.addEventListener("storage", refreshUser);
    return () => {
      window.removeEventListener(USERS_CHANGED_EVENT, refreshUser);
      window.removeEventListener(ACCESS_SETTINGS_CHANGED_EVENT, refreshUser);
      window.removeEventListener("storage", refreshUser);
    };
  }, []);

  const openQuotes = quotes.filter((quote) => !["sent", "po"].includes(quote.stage));
  const workItems = [...openQuotes]
    .sort((left, right) => {
      const dueRank = { delayed: 0, today: 1, future: 2, none: 3 };
      const leftRank = dueRank[quoteDueState(left)];
      const rightRank = dueRank[quoteDueState(right)];
      if (leftRank !== rightRank) return leftRank - rightRank;
      return quoteEstimatedValue(right) - quoteEstimatedValue(left);
    })
    .slice(0, 10);
  const stageMax = Math.max(1, ...Object.values(metrics?.stage_counts ?? {}));
  const showTeamOverview = currentUser.role === "admin";

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-3">
        <div>
          <h2 className="text-lg font-semibold">Priority work</h2>
          <div className="mt-1 text-xs text-muted-foreground">
          {metrics?.generated_at ? `Updated ${new Date(metrics.generated_at).toLocaleString("en-GB")}` : "Loading current work..."}
          </div>
        </div>
        <Button variant="secondary" size="sm" onClick={refresh} disabled={loading}>
          <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
          Refresh
        </Button>
      </div>

      <section className="space-y-2">
        <div className="grid grid-cols-2 gap-2 xl:grid-cols-5">
          <MetricCard label="Overdue" value={String(metrics?.delayed_enquiries ?? 0)} hint="Past the due date" />
          <MetricCard label="Due today" value={String(metrics?.due_today ?? 0)} hint="Needs action today" />
          <MetricCard label="Waiting for customer" value={String(metrics?.clarification_required ?? 0)} hint="Customer information needed" />
          <MetricCard label="Review items" value={String(metrics?.pending_review ?? 0)} hint="Item details need checking" />
          <MetricCard label="Waiting for approval" value={String(metrics?.pending_approval ?? 0)} hint="Ready for an approver" />
        </div>
      </section>

      <section className="space-y-2">
        <div className="flex items-end justify-between gap-3">
          <div>
          <h3 className="text-sm font-semibold">{showTeamOverview ? "Open work" : "My tasks"}</h3>
          <p className="text-xs text-muted-foreground">{showTeamOverview ? "Highest-priority open enquiries across the team." : "Your assigned enquiries, ordered by due date."}</p>
          </div>
          <Badge variant="outline">{workItems.length} shown</Badge>
        </div>
        {loading && !quotes.length ? (
          <Card>
            <CardContent className="p-6 text-sm text-muted-foreground">Loading assigned work...</CardContent>
          </Card>
        ) : workItems.length ? (
          <Card>
            <CardContent className="p-0">
              <Table className="min-w-[760px]">
                <TableHeader>
                  <TableRow>
                    <TableHead>Customer / enquiry</TableHead>
                    {showTeamOverview ? <TableHead>Owner</TableHead> : null}
                    <TableHead>Current step</TableHead>
                    <TableHead>Due</TableHead>
                    <TableHead>Next action</TableHead>
                    <TableHead className="w-24"><span className="sr-only">Continue</span></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {workItems.map((quote) => (
                    <TableRow key={quote.id}>
                      <TableCell>
                        <Link href={quoteHref(quote)} className="font-medium hover:underline">{quote.customer || "Customer not added"}</Link>
                        <div className="max-w-56 truncate text-xs text-muted-foreground">{quote.project_ref || quote.quote_no || "No reference added"}</div>
                      </TableCell>
                      {showTeamOverview ? (
                        <TableCell>{resolveAppUserName([quote.stage_meta?.owner_name, quote.stage_meta?.owner_email, quote.stage_meta?.owner_id], appUsers, "Needs assignment")}</TableCell>
                      ) : null}
                      <TableCell>
                        <div className="flex flex-col items-start gap-1">
                          <Badge variant="outline">{workStepLabel(quote.stage)}</Badge>
                          {(() => { const qs = quotationStageBadge(quote); return <Badge variant={qs.variant}>{qs.index + 1}. {qs.label}</Badge>; })()}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={quoteDueState(quote) === "delayed" ? "warning" : quoteDueState(quote) === "today" ? "secondary" : "outline"}>{dueLabel(quote)}</Badge>
                      </TableCell>
                      <TableCell className="text-sm">{nextActionLabel(quote)}</TableCell>
                      <TableCell>
                        <Button asChild variant="secondary" size="sm">
                          <Link href={quoteHref(quote)}>Continue</Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        ) : (
          <EmptyState
            icon={CheckCircle2}
            title="No open work needs attention"
            body={showTeamOverview ? "There are no open enquiries in the current workspace." : "You have no assigned enquiries to continue. New assignments will appear here."}
            action={canRole(currentUser.role, "create_enquiry", accessSettings) ? { label: "New enquiry", href: "/quotes?new=1" } : undefined}
          />
        )}
      </section>

      {showTeamOverview ? (
        <section className="space-y-2">
          <div>
            <h3 className="text-sm font-semibold">Team overview</h3>
            <p className="text-xs text-muted-foreground">Open work and overdue items by owner.</p>
          </div>
          <Card>
            <CardContent className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">
              {(metrics?.owner_workload ?? []).map((owner) => (
                <div key={owner.owner_id} className="rounded-md border p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="truncate font-medium">{resolveAppUserName([owner.owner_name, owner.owner_id], appUsers, "Needs assignment")}</div>
                    <Badge variant={owner.delayed_count ? "warning" : "outline"}>{owner.open_count} open</Badge>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    {owner.delayed_count} overdue / {formatCurrencyValue(owner.value)} open value
                  </div>
                </div>
              ))}
              {!(metrics?.owner_workload ?? []).length ? <div className="text-sm text-muted-foreground">No open team work to show.</div> : null}
            </CardContent>
          </Card>
        </section>
      ) : null}

      <section className="space-y-2">
        <div>
          <h3 className="text-sm font-semibold">Overview</h3>
          <p className="text-xs text-muted-foreground">A compact view of incoming work and results.</p>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:gap-3 xl:grid-cols-4">
          <MetricCard label="New today" value={String(metrics?.new_enquiries_today ?? 0)} hint="Customer enquiries received" />
          <MetricCard label="Open work" value={String(openQuotes.length)} hint="Enquiries still in progress" />
          <MetricCard label="Open value" value={formatCurrencyValue(metrics?.open_quote_value ?? metrics?.total_quote_value ?? 0)} hint={`${metrics?.high_value_enquiries ?? 0} high-value enquiries`} />
          <MetricCard label="Win rate" value={pct(metrics?.win_rate ?? 0)} hint={`${metrics?.converted_to_po ?? 0} orders received`} />
        </div>

        <div className="grid gap-3 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
          <Card>
            <CardHeader className="border-b px-4 py-3">
              <CardTitle className="flex items-center gap-2 text-base"><ClipboardList className="h-4 w-4" />Work by step</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 p-4">
              {Object.entries(metrics?.stage_counts ?? {}).map(([stage, count]) => (
                <div key={stage} className="flex items-center gap-3">
                  <div className="w-36 truncate text-sm">{workStepLabel(stage)}</div>
                  <div className="h-2 flex-1 overflow-hidden rounded bg-muted">
                    <div className="h-full bg-primary" style={{ width: `${Math.max(4, (count / stageMax) * 100)}%` }} />
                  </div>
                  <div className="w-10 text-right text-sm text-muted-foreground">{count}</div>
                </div>
              ))}
              {!Object.keys(metrics?.stage_counts ?? {}).length ? <div className="text-sm text-muted-foreground">No workflow data yet.</div> : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b px-4 py-3">
              <CardTitle className="flex items-center gap-2 text-base"><History className="h-4 w-4" />Results</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 p-4 text-sm">
              <div className="flex items-center justify-between gap-3"><span className="text-muted-foreground">Quotes sent</span><span className="font-medium">{metrics?.quotes_sent ?? 0}</span></div>
              <div className="flex items-center justify-between gap-3"><span className="text-muted-foreground">Orders received</span><span className="font-medium">{metrics?.converted_to_po ?? 0}</span></div>
              <div className="flex items-center justify-between gap-3"><span className="text-muted-foreground">Average time to send</span><span className="font-medium">{(metrics?.avg_time_to_sent_days ?? 0).toFixed(1)} days</span></div>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}
