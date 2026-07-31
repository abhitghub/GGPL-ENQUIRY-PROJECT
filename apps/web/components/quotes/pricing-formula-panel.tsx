"use client";

import * as React from "react";
import { Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { PricingFormulaRow, StoredPricingFormulas } from "@/lib/pricing-formulas";

/**
 * The quotation summary with a pricing-formula column against every spec row.
 *
 * Pricing (Ashwin sir) fills this in while the enquiry sits in the pricing
 * queue; estimation then reads it — same table, read-only — and prices each
 * line item against its spec formula.
 */
export function PricingFormulaPanel({
  rows,
  editable,
  loading,
  stored,
  unmatchedLines = [],
  onChange,
}: {
  rows: PricingFormulaRow[];
  editable: boolean;
  loading: boolean;
  stored: StoredPricingFormulas | null;
  /** Line numbers that only reached the summary through their raw wording. */
  unmatchedLines?: number[];
  onChange: (item: string, field: "formula" | "note", value: string) => void;
}) {
  const filled = rows.filter((row) => row.formula.trim()).length;
  const totalQty = rows.reduce((total, row) => total + row.qty, 0);

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-4 text-xs text-muted-foreground">
        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading the quotation summary…
      </div>
    );
  }

  return (
    <div className="space-y-2 px-1 py-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        <span className="font-medium text-foreground">Quotation summary — one row per spec</span>
        <Badge variant={filled === rows.length && rows.length > 0 ? "secondary" : "outline"}>
          {filled}/{rows.length} priced
        </Badge>
        <span>
          {rows.reduce((total, row) => total + row.count, 0)} line item(s) · {Number(totalQty.toFixed(3))} total qty
        </span>
        {stored?.set_by ? (
          <span>
            Last set by {stored.set_by}
            {stored.set_at ? ` on ${stored.set_at.slice(0, 16).replace("T", " ")}` : ""}
          </span>
        ) : null}
        {stored?.stale ? (
          <span className="text-amber-700 dark:text-amber-300">
            ⚠ Line items changed after these formulas were entered — re-check every row.
          </span>
        ) : null}
      </div>

      {unmatchedLines.length > 0 ? (
        <div className="text-xs text-amber-700 dark:text-amber-300">
          ⚠ Line {unmatchedLines.join(", ")} could not be matched to a house spec and is listed from the raw wording — price it with care.
        </div>
      ) : null}

      <div className="max-h-96 overflow-auto rounded-md border bg-background">
        <Table className="min-w-[820px]">
          <TableHeader className="sticky top-0 z-10 bg-muted/80 backdrop-blur">
            <TableRow>
              <TableHead className="w-10">#</TableHead>
              <TableHead className="min-w-72">Spec</TableHead>
              <TableHead className="w-16 text-right">Items</TableHead>
              <TableHead className="w-16 text-right">Qty</TableHead>
              <TableHead className="w-28">Lines</TableHead>
              <TableHead className="min-w-56">Pricing formula</TableHead>
              <TableHead className="min-w-44">Note for estimation</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-xs text-muted-foreground">
                  No priceable specs on this enquiry yet — add line items and update the extraction summary first.
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row, index) => (
                <TableRow key={row.item} className={!row.formula.trim() ? "bg-amber-50/50 dark:bg-amber-950/20" : undefined}>
                  <TableCell className="text-xs text-muted-foreground">{index + 1}</TableCell>
                  <TableCell className="max-w-96 whitespace-normal break-words text-xs font-medium">{row.item}</TableCell>
                  <TableCell className="text-right text-xs">{row.count}</TableCell>
                  <TableCell className="text-right text-xs">{row.qty || "—"}</TableCell>
                  <TableCell className="max-w-28 truncate text-xs text-muted-foreground" title={row.lines.join(", ")}>
                    {row.lines.join(", ")}
                  </TableCell>
                  <TableCell>
                    {editable ? (
                      <textarea
                        value={row.formula}
                        onChange={(event) => onChange(row.item, "formula", event.target.value)}
                        placeholder="e.g. OD/ID weight × ₹/kg + 18% margin"
                        className="min-h-[48px] w-full rounded-md border border-input bg-background px-2 py-1.5 text-xs outline-none focus:ring-2 focus:ring-ring"
                      />
                    ) : (
                      <div className="whitespace-pre-wrap text-xs">
                        {row.formula || <span className="text-muted-foreground">Not priced yet</span>}
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    {editable ? (
                      <textarea
                        value={row.note}
                        onChange={(event) => onChange(row.item, "note", event.target.value)}
                        placeholder="Optional"
                        className="min-h-[48px] w-full rounded-md border border-input bg-background px-2 py-1.5 text-xs outline-none focus:ring-2 focus:ring-ring"
                      />
                    ) : (
                      <div className="whitespace-pre-wrap text-xs text-muted-foreground">{row.note || "—"}</div>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}