"use client";

import * as React from "react";
import { ChevronDown, PieChart } from "lucide-react";

import type { QuotePricingLine } from "@/components/quotes/pricing-utils";
import type { GasketItem } from "@/lib/api";
import { toNumber } from "@/lib/api";
import { cn } from "@/lib/utils";

// Price breakup in the GGPL document format (see the "PRICE BREAKUP - <customer>"
// sheets sales sends alongside a quotation): items are grouped by material
// specification — the GGPL description with the size dimension removed — and
// each numbered group lists SR.NO. / GGPL DESCRIPTION / QTY / UNIT PRICE /
// TOTAL PRICE with a subtotal, followed by a grand total across groups.

export type PriceBreakupLine = {
  srNo: number;
  description: string;
  quantity: number;
  unitPrice: number;
  total: number;
  // GTQ line: price still to come, shown as "Will quote soon" instead of a figure.
  isGtq: boolean;
};

export type PriceBreakupGroup = {
  number: number;
  key: string;
  title: string;
  lines: PriceBreakupLine[];
  quantity: number;
  amount: number;
  unpricedCount: number;
};

export type PriceBreakup = {
  groups: PriceBreakupGroup[];
  totalQuantity: number;
  totalAmount: number;
  pricedCount: number;
  unpricedCount: number;
};

/** The spec family an item belongs to: its GGPL description minus the size
 * segment (and minus a legacy "RATING :" segment), with the thickness kept.
 * Items that differ only by size share a key — exactly how the price breakup
 * documents group lines. */
export function specFamilyTitle(item: GasketItem): string {
  const desc = String(item.ggpl_description || "").trim();
  if (desc && desc.includes(",")) {
    const segments = desc.split(",").map((segment) => segment.trim());
    const kept = segments.filter((segment) => segment && !/^SIZE\s*:?|^RATING\s*:/i.test(segment));
    if (kept.length) {
      let title = kept.join(", ");
      const thkMatch = desc.match(/([\d.]+)\s*MM\s*THK/i);
      const thk = thkMatch ? thkMatch[1] : "";
      if (thk && !/MM\s*THK|THK\s*:/i.test(title)) title += `, ${thk}MM THK`;
      return title.replace(/\s+/g, " ").toUpperCase();
    }
  }
  // No usable description: fall back to the structured spec fields.
  const parts = [
    String(item.gasket_type || "").replace(/_/g, " "),
    String(item.moc || ""),
    String(item.face_type || ""),
    String(item.standard || ""),
    item.thickness_mm ? `${item.thickness_mm}MM THK` : "",
  ].filter(Boolean);
  return (parts.join(", ") || "UNSPECIFIED").toUpperCase();
}

export function buildPriceBreakup(items: GasketItem[], lines: QuotePricingLine[]): PriceBreakup {
  const groups: PriceBreakupGroup[] = [];
  const byKey = new Map<string, PriceBreakupGroup>();
  let pricedCount = 0;
  for (const line of lines) {
    const item = items[line.index];
    if (!item || item.status === "regret") continue;
    const title = specFamilyTitle(item);
    let group = byKey.get(title);
    if (!group) {
      group = { number: groups.length + 1, key: title, title, lines: [], quantity: 0, amount: 0, unpricedCount: 0 };
      byKey.set(title, group);
      groups.push(group);
    }
    group.lines.push({
      srNo: toNumber(item.line_no) || line.index + 1,
      description: String(item.ggpl_description || item.raw_description || ""),
      quantity: line.quantity,
      unitPrice: line.finalUnitPrice,
      total: line.lineTotal,
      isGtq: line.isGtq,
    });
    group.quantity += line.quantity;
    group.amount += line.lineTotal;
    if (line.finalUnitPrice > 0) pricedCount += 1;
    else group.unpricedCount += 1;
  }
  return {
    groups,
    totalQuantity: groups.reduce((sum, group) => sum + group.quantity, 0),
    totalAmount: groups.reduce((sum, group) => sum + group.amount, 0),
    pricedCount,
    unpricedCount: groups.reduce((sum, group) => sum + group.unpricedCount, 0),
  };
}

function money(value: number): string {
  return value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const HEAD = "border-b px-3 py-1.5 text-left text-xs font-medium text-muted-foreground";
const CELL = "border-b px-3 py-1.5 align-top";
const NUM = `${CELL} text-right tabular-nums whitespace-nowrap`;

function GroupSection({ group, currency }: { group: PriceBreakupGroup; currency: string }) {
  const [open, setOpen] = React.useState(false);
  return (
    <div className="rounded-md border">
      <button
        type="button"
        className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-muted/40"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <ChevronDown className={cn("h-4 w-4 shrink-0 text-muted-foreground transition-transform", !open && "-rotate-90")} />
        <span className="min-w-0 flex-1 truncate text-sm font-medium" title={group.title}>
          {group.number}. {group.title}
        </span>
        <span className="shrink-0 text-xs text-muted-foreground">{group.lines.length} item(s)</span>
        <span className="w-20 shrink-0 text-right text-sm tabular-nums">{group.quantity.toLocaleString("en-IN")}</span>
        <span className="w-32 shrink-0 text-right text-sm font-medium tabular-nums">{money(group.amount)}</span>
      </button>
      {open && (
        <div className="overflow-x-auto border-t">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className={`${HEAD} w-16`}>SR.NO.</th>
                <th className={HEAD}>GGPL DESCRIPTION</th>
                <th className={`${HEAD} w-20 text-right`}>QTY</th>
                <th className={`${HEAD} w-40 text-right`}>UNIT PRICE IN {currency}</th>
                <th className={`${HEAD} w-40 text-right`}>TOTAL PRICE IN {currency}</th>
              </tr>
            </thead>
            <tbody>
              {group.lines.map((line) => (
                <tr key={`${line.srNo}-${line.description}`} className="hover:bg-muted/30">
                  <td className={NUM}>{line.srNo}</td>
                  <td className={`${CELL} text-xs`}>{line.description || "—"}</td>
                  <td className={NUM}>{line.quantity.toLocaleString("en-IN")}</td>
                  <td className={NUM}>{line.isGtq ? "Will quote soon" : line.unitPrice > 0 ? money(line.unitPrice) : "—"}</td>
                  <td className={NUM}>{line.isGtq ? "—" : money(line.total)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="font-semibold">
                <td className="px-3 py-1.5" colSpan={2}>Subtotal</td>
                <td className="px-3 py-1.5 text-right tabular-nums">{group.quantity.toLocaleString("en-IN")}</td>
                <td className="px-3 py-1.5" />
                <td className="px-3 py-1.5 text-right tabular-nums">{money(group.amount)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  );
}

export function PriceBreakupPanel({
  items,
  lines,
  currency,
}: {
  items: GasketItem[];
  lines: QuotePricingLine[];
  currency: string;
}) {
  const breakup = React.useMemo(() => buildPriceBreakup(items, lines), [items, lines]);
  const displayCurrency = currency || "INR";

  return (
    <div className="rounded-md border bg-background p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-medium">
          <PieChart className="h-4 w-4" />
          Price breakup
        </div>
        <div className="text-xs text-muted-foreground">
          Grouped by material spec (as in the price breakup document) · amounts in {displayCurrency}, before header discount and GST
        </div>
      </div>
      {!breakup.groups.length ? (
        <div className="py-6 text-center text-sm text-muted-foreground">No quotable items on this quotation.</div>
      ) : !breakup.pricedCount ? (
        <div className="py-6 text-center text-sm text-muted-foreground">
          No prices entered yet — the breakup appears once pricing is done on the Items tab.
        </div>
      ) : (
        <div className="space-y-2">
          {breakup.unpricedCount > 0 && (
            <div className="rounded-md border border-amber-200 bg-amber-50/70 px-3 py-1.5 text-xs text-amber-950 dark:border-amber-900 dark:bg-amber-950/25 dark:text-amber-100">
              {breakup.unpricedCount} item(s) still without a unit price — their totals show as 0 below.
            </div>
          )}
          <div className="hidden items-center gap-3 px-3 text-[11px] font-medium text-muted-foreground sm:flex">
            <span className="h-4 w-4 shrink-0" />
            <span className="min-w-0 flex-1">MATERIAL SPEC</span>
            <span className="shrink-0">ITEMS</span>
            <span className="w-20 shrink-0 text-right">QTY</span>
            <span className="w-32 shrink-0 text-right">TOTAL IN {displayCurrency}</span>
          </div>
          {breakup.groups.map((group) => (
            <GroupSection key={group.key} group={group} currency={displayCurrency} />
          ))}
          <div className="flex items-center gap-3 rounded-md border bg-muted/40 px-3 py-2 font-semibold">
            <span className="h-4 w-4 shrink-0" />
            <span className="min-w-0 flex-1 text-sm">GRAND TOTAL</span>
            <span className="shrink-0 text-xs font-normal text-muted-foreground">
              {breakup.groups.reduce((sum, group) => sum + group.lines.length, 0)} item(s)
            </span>
            <span className="w-20 shrink-0 text-right text-sm tabular-nums">{breakup.totalQuantity.toLocaleString("en-IN")}</span>
            <span className="w-32 shrink-0 text-right text-sm tabular-nums">{money(breakup.totalAmount)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
