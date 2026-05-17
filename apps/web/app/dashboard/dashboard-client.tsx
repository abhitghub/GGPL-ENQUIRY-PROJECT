"use client";

import * as React from "react";
import { ClipboardList, FileText, History, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { DashboardMetrics, Quote, getDashboardMetrics, listQuotes } from "@/lib/api";
import { EmptyState } from "@/components/app-shell/empty-state";
import { MetricCard } from "@/components/app-shell/metric-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const stages = ["initial", "review", "quote_prep", "repricing", "sent", "po"] as const;
const finalStages = new Set(["quote_prep", "repricing", "sent", "po"]);

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function quoteHref(quote: Quote) {
  return finalStages.has(quote.stage) ? `/quotes/final?quote=${quote.id}` : `/quotes?quote=${quote.id}`;
}

export function DashboardClient() {
  const [metrics, setMetrics] = React.useState<DashboardMetrics | null>(null);
  const [quotes, setQuotes] = React.useState<Quote[]>([]);

  async function refresh() {
    try {
      const [metricData, quoteData] = await Promise.all([getDashboardMetrics(), listQuotes()]);
      setMetrics(metricData);
      setQuotes(quoteData);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Dashboard load failed");
    }
  }

  React.useEffect(() => {
    refresh();
  }, []);

  const active = quotes.filter((quote) => !["sent", "po"].includes(quote.stage)).slice(0, 6);

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button variant="secondary" onClick={refresh}>
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        <MetricCard label="Total quotes" value={String(metrics?.total_quotes ?? 0)} hint="Saved workspaces" />
        <MetricCard label="Items processed" value={String(metrics?.items_processed ?? 0)} hint="Across all quotes" />
        <MetricCard label="Pending review" value={String(metrics?.pending_review ?? 0)} hint="Initial and review stages" />
        <MetricCard label="Quotes sent" value={String(metrics?.quotes_sent ?? 0)} hint="Sent or PO" />
        <MetricCard label="Won quotes" value={String(metrics?.converted_to_po ?? 0)} hint="PO stage" />
        <MetricCard label="Win rate" value={pct(metrics?.win_rate ?? 0)} hint={`Conversion ${pct(metrics?.conversion_rate ?? 0)}`} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
        {active.length ? (
          <Card>
            <CardHeader>
              <CardTitle>Active quotations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {active.map((quote) => (
                <a key={quote.id} href={quoteHref(quote)} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm hover:bg-muted">
                  <div>
                    <div className="font-medium">{quote.customer || "Untitled customer"}</div>
                    <div className="text-xs text-muted-foreground">{quote.project_ref || quote.quote_no || quote.id}</div>
                  </div>
                  <Badge variant="outline">{quote.stage}</Badge>
                </a>
              ))}
            </CardContent>
          </Card>
        ) : (
          <EmptyState
            icon={ClipboardList}
            title="No active quotations"
            body="Create a quote workspace when the first enquiry is ready for intake."
            action={{ label: "Open quotes", href: "/quotes" }}
          />
        )}

        <Card>
          <CardHeader>
            <CardTitle>Pipeline</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {stages.map((stage) => (
              <div key={stage} className="flex items-center justify-between rounded-md border px-3 py-2">
                <span className="text-sm font-medium">{stage.replace("_", " ")}</span>
                <span className="text-sm text-muted-foreground">{metrics?.stage_counts?.[stage] ?? 0}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Gasket type distribution</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(metrics?.gasket_type_distribution ?? {}).map(([type, count]) => (
              <div key={type} className="flex items-center gap-3">
                <div className="w-40 truncate text-sm">{type}</div>
                <div className="h-2 flex-1 overflow-hidden rounded bg-muted">
                  <div className="h-full bg-secondary" style={{ width: `${Math.min(100, count * 12)}%` }} />
                </div>
                <div className="w-10 text-right text-sm text-muted-foreground">{count}</div>
              </div>
            ))}
            {!Object.keys(metrics?.gasket_type_distribution ?? {}).length && <div className="text-sm text-muted-foreground">No item data yet.</div>}
          </CardContent>
        </Card>
        <div className="grid gap-4">
          <EmptyState
            icon={FileText}
            title="Quote drafts"
            body={`${quotes.filter((quote) => quote.stage === "quote_prep").length} quotation(s) are in quote preparation.`}
          />
          <EmptyState
            icon={History}
            title="Average time to sent"
            body={`${(metrics?.avg_time_to_sent_days ?? 0).toFixed(1)} days across sent quotations.`}
          />
        </div>
      </div>
    </div>
  );
}
