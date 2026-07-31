import type { GasketItem, Quote } from "@/lib/api";
import {
  ExtractionSummaryGroup,
  buildExtractionSummaryIndex,
  extractionSummaryItemSignature,
} from "@/lib/extraction-summary";

/**
 * Pricing formulas — the per-spec rate rule Ashwin sir writes against the
 * quotation summary before an enquiry is released to estimation.
 *
 * One enquiry carries many different specs, so there is no single formula for
 * it: the quotation summary collapses the line items into one row per spec
 * (see lib/extraction-summary.ts) and pricing enters a formula against EVERY
 * row. Estimation then works the pricing sheet with each line's spec formula
 * shown next to it, and orders the process/material against that spec.
 *
 * Stored on stage_meta.pricing_formulas so it travels with the enquiry:
 *
 *   {
 *     rows: [{ item, count, qty, formula, note }],
 *     set_by, set_at,
 *     item_signature,          // line items the formulas were written against
 *     stale, stale_at,         // set by the API when the line items change
 *   }
 */

export const PRICING_FORMULA_META_KEY = "pricing_formulas";

export type PricingFormulaRow = {
  /** The quotation-summary spec line the formula prices. */
  item: string;
  count: number;
  qty: number;
  lines: number[];
  formula: string;
  note: string;
};

export type StoredPricingFormulas = {
  rows: PricingFormulaRow[];
  set_by: string;
  set_at: string;
  item_signature: string;
  stale: boolean;
  stale_at: string;
};

function text(value: unknown): string {
  if (typeof value === "string") return value.trim();
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return "";
}

function count(value: unknown): number {
  const num = Number(value);
  return Number.isFinite(num) ? num : 0;
}

function lineNumbers(value: unknown): number[] {
  if (!Array.isArray(value)) return [];
  return value.map((entry) => count(entry)).filter((entry) => entry > 0);
}

export function normalizePricingFormulas(value: unknown): StoredPricingFormulas | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const rows = Array.isArray(raw.rows) ? raw.rows : [];
  return {
    rows: rows
      .map((row) => {
        const data = row && typeof row === "object" ? (row as Record<string, unknown>) : {};
        return {
          item: text(data.item),
          count: count(data.count),
          qty: count(data.qty),
          lines: lineNumbers(data.lines),
          formula: text(data.formula),
          note: text(data.note),
        };
      })
      .filter((row) => row.item),
    set_by: text(raw.set_by),
    set_at: text(raw.set_at),
    item_signature: typeof raw.item_signature === "string" ? raw.item_signature : "",
    stale: raw.stale === true,
    stale_at: text(raw.stale_at),
  };
}

export function readPricingFormulas(quote: Quote | null | undefined): StoredPricingFormulas | null {
  return normalizePricingFormulas((quote?.stage_meta ?? {})[PRICING_FORMULA_META_KEY]);
}

/**
 * The rows to show pricing: the summary rebuilt from the CURRENT line items —
 * never the stored copy, which can be a stale or coarser server-side render —
 * with any formula already written against a spec carried over by its text.
 */
export function pricingFormulaRows(
  items: GasketItem[],
  stored: StoredPricingFormulas | null,
): PricingFormulaRow[] {
  return mergePricingFormulaRows(buildExtractionSummaryIndex(items).groups, stored);
}

export function mergePricingFormulaRows(
  groups: ExtractionSummaryGroup[],
  stored: StoredPricingFormulas | null,
): PricingFormulaRow[] {
  const held = new Map((stored?.rows ?? []).map((row) => [row.item, row]));
  return groups.map((group) => ({
    item: group.item,
    count: group.count,
    qty: group.qty,
    lines: group.lines,
    formula: held.get(group.item)?.formula ?? "",
    note: held.get(group.item)?.note ?? "",
  }));
}

export type PricingFormulaCoverage = {
  total: number;
  filled: number;
  missing: string[];
  /** Every spec on the summary carries a formula (vacuously true when empty). */
  complete: boolean;
};

export function pricingFormulaCoverage(rows: PricingFormulaRow[]): PricingFormulaCoverage {
  const missing = rows.filter((row) => !row.formula.trim()).map((row) => row.item);
  return {
    total: rows.length,
    filled: rows.length - missing.length,
    missing,
    complete: missing.length === 0,
  };
}

/**
 * Formula text per line item, for the pricing sheet: every line inherits the
 * formula of the spec it collapsed onto. "" for a line with no spec row
 * (regret lines, and rows with no wording to summarise).
 */
export function pricingFormulaByLine(items: GasketItem[], rows: PricingFormulaRow[]): string[] {
  const { groupIndexByLine } = buildExtractionSummaryIndex(items);
  return items.map((_, index) => {
    const groupIndex = groupIndexByLine[index];
    return groupIndex === null || groupIndex === undefined ? "" : rows[groupIndex]?.formula ?? "";
  });
}

/** The record to persist on stage_meta. Writing it clears any stale marker. */
export function buildPricingFormulaRecord(
  items: GasketItem[],
  rows: PricingFormulaRow[],
  actor: string,
  at: string,
): StoredPricingFormulas {
  return {
    rows: rows.map((row) => ({ ...row, formula: row.formula.trim(), note: row.note.trim() })),
    set_by: actor,
    set_at: at,
    item_signature: extractionSummaryItemSignature(items),
    stale: false,
    stale_at: "",
  };
}