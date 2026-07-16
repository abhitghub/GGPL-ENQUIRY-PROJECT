import type { GasketItem } from "@/lib/api";
import { toNumber } from "@/lib/api";

export type QuotePricingLine = {
  index: number;
  quantity: number;
  costPrice: number;
  sellingPrice: number;
  targetMarginPct: number;
  lineDiscountPct: number;
  finalUnitPrice: number;
  lineTotal: number;
  costTotal: number;
  marginPct: number | null;
  discountImpact: number;
};

export type QuotePricingSummary = {
  lines: QuotePricingLine[];
  subtotal: number;
  discountPct: number;
  discount: number;
  taxable: number;
  gstPct: number;
  gst: number;
  grandTotal: number;
  costTotal: number;
  grossMargin: number;
  grossMarginPct: number | null;
  lowestLineMarginPct: number | null;
  approvalRequired: boolean;
  approvalReasons: string[];
};

export function buildQuotePricingSummary({
  items,
  unitPrices,
  costPrices,
  targetMargins,
  lineDiscountsPct = [],
  discountPct,
  gstPct,
  riskCount,
  fxRate = 1,
  isForeignCurrency = false,
}: {
  items: GasketItem[];
  unitPrices: number[];
  costPrices: number[];
  targetMargins: number[];
  lineDiscountsPct?: number[];
  discountPct: number;
  gstPct: number;
  riskCount: number;
  fxRate?: number;
  isForeignCurrency?: boolean;
}): QuotePricingSummary {
  const divisor = isForeignCurrency ? fxRate || 1 : 1;
  const lines = items.map((item, index) => {
    const quantity = item.status === "regret" ? 0 : toNumber(item.quantity, 0);
    const sellingPrice = (unitPrices[index] ?? 0) / divisor;
    const costPrice = costPrices[index] ?? 0;
    // Per-line discount % applied to the unit price. Zero (the default) keeps
    // finalUnitPrice === sellingPrice, so totals match the pre-discount behaviour.
    const lineDiscountPct = Math.max(lineDiscountsPct[index] ?? 0, 0);
    const finalUnitPrice = sellingPrice * (1 - lineDiscountPct / 100);
    const lineTotal = quantity * finalUnitPrice;
    const costTotal = quantity * costPrice;
    const marginPct = finalUnitPrice > 0 ? ((finalUnitPrice - costPrice) / finalUnitPrice) * 100 : null;
    return {
      index,
      quantity,
      costPrice,
      sellingPrice,
      targetMarginPct: targetMargins[index] ?? 0,
      lineDiscountPct,
      finalUnitPrice,
      lineTotal,
      costTotal,
      marginPct,
      discountImpact: quantity * sellingPrice * (lineDiscountPct / 100),
    };
  });

  const subtotal = lines.reduce((sum, line) => sum + line.lineTotal, 0);
  const discount = subtotal * Math.max(discountPct, 0) / 100;
  const taxable = subtotal - discount;
  const gst = taxable * Math.max(gstPct, 0) / 100;
  const grandTotal = taxable + gst;
  const costTotal = lines.reduce((sum, line) => sum + line.costTotal, 0);
  const grossMargin = taxable - costTotal;
  const grossMarginPct = taxable > 0 ? (grossMargin / taxable) * 100 : null;
  const pricedMargins = lines
    .map((line) => line.marginPct)
    .filter((value): value is number => value !== null && Number.isFinite(value));
  const lowestLineMarginPct = pricedMargins.length ? Math.min(...pricedMargins) : null;
  const approvalReasons: string[] = [];

  void riskCount;

  return {
    lines,
    subtotal,
    discountPct,
    discount,
    taxable,
    gstPct,
    gst,
    grandTotal,
    costTotal,
    grossMargin,
    grossMarginPct,
    lowestLineMarginPct,
    approvalRequired: approvalReasons.length > 0,
    approvalReasons,
  };
}
