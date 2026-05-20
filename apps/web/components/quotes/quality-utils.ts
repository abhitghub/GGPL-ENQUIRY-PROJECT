import { GasketItem, Quote, toNumber } from "@/lib/api";

import { getString, hasText, itemHasMaterial, itemHasSize } from "./item-validation";

export type QualityFinding = {
  severity: "high" | "medium" | "low";
  title: string;
  detail: string;
  rows?: number[];
};

export type QualityReport = {
  score: number;
  readiness: number;
  quoteScore: number;
  technicalScore: number;
  riskScore: number;
  missing: string[];
  risks: QualityFinding[];
};

function pushRisk(risks: QualityFinding[], finding: QualityFinding) {
  const existing = risks.find((risk) => risk.title === finding.title && risk.detail === finding.detail);
  if (existing) {
    existing.rows = Array.from(new Set([...(existing.rows ?? []), ...(finding.rows ?? [])])).sort((a, b) => a - b);
  } else {
    risks.push(finding);
  }
}

export function evaluateQuoteQuality(quote: Quote | null, quoteItems: GasketItem[], quoteData: Record<string, unknown>): QualityReport {
  const itemsToCheck = quoteItems.length ? quoteItems : [];
  const totalItems = quote?.n_items ?? itemsToCheck.length;
  const ready = quoteItems.length ? quoteItems.filter((item) => item.status === "ready").length : (quote?.n_ready ?? 0);
  const check = quoteItems.length ? quoteItems.filter((item) => item.status === "check").length : (quote?.n_check ?? 0);
  const missingCount = quoteItems.length ? quoteItems.filter((item) => item.status === "missing").length : (quote?.n_missing ?? 0);
  const readiness = totalItems ? Math.round((ready / totalItems) * 100) : 0;
  const quoteMissing = [
    !hasText(quote?.customer) ? "Customer name" : "",
    !hasText(quote?.project_ref) ? "Project / enquiry reference" : "",
    !hasText(quoteData.customer_enq_no) ? "Customer enquiry no" : "",
    !hasText(quoteData.attention) ? "Attention/contact person" : "",
    !hasText(quoteData.currency) ? "Currency" : "",
    !hasText(quoteData.delivery) ? "Delivery terms/time" : "",
    !hasText(quoteData.payment_terms) ? "Payment terms" : "",
  ].filter(Boolean);
  const quoteScore = Math.max(0, Math.round(((7 - quoteMissing.length) / 7) * 100));
  const technicalScore = totalItems ? Math.max(0, Math.round(100 - ((missingCount * 1.6 + check * 0.7) / totalItems) * 100)) : 0;
  const risks: QualityFinding[] = [];

  if (!totalItems) {
    pushRisk(risks, { severity: "high", title: "No line items", detail: "The enquiry has no parsed or manual gasket items yet." });
  }
  if (missingCount > 0) {
    pushRisk(risks, { severity: "high", title: "Missing technical fields", detail: `${missingCount} line item(s) are marked missing.` });
  }
  if (check > 0) {
    pushRisk(risks, { severity: "medium", title: "Defaults or review flags used", detail: `${check} line item(s) need review before quotation.` });
  }

  itemsToCheck.forEach((item, index) => {
    const row = index + 1;
    const type = getString(item.gasket_type).toUpperCase();
    const text = [item.raw_description, item.standard, item.rating, item.special].map(getString).join(" ").toUpperCase();
    if (!hasText(type)) {
      pushRisk(risks, { severity: "high", title: "Unknown gasket type", detail: "Gasket type is blank.", rows: [row] });
    }
    if (!itemHasSize(item)) {
      pushRisk(risks, { severity: "high", title: "Missing dimensions", detail: "Size, normalized size, OD/ID, or ring number is missing.", rows: [row] });
    }
    if (!itemHasMaterial(item)) {
      pushRisk(risks, { severity: "medium", title: "Missing material", detail: "Material/MOC is not clear enough for procurement or pricing.", rows: [row] });
    }
    if (!hasText(item.rating) && !hasText(item.standard) && type !== "RTJ") {
      pushRisk(risks, { severity: "medium", title: "Pressure class unclear", detail: "Rating/standard is missing.", rows: [row] });
    }
    if ((text.includes("ASME") || text.includes("ANSI")) && (text.includes("DIN") || text.includes("EN 1092"))) {
      pushRisk(risks, { severity: "high", title: "Standard mismatch", detail: "ASME/ANSI and DIN/EN references appear on the same line.", rows: [row] });
    }
    if (type === "RTJ" && (!hasText(item.rtj_groove_type) || !hasText(item.ring_no))) {
      pushRisk(risks, { severity: "medium", title: "RTJ details incomplete", detail: "Ring number and groove type should be checked.", rows: [row] });
    }
    if (type === "SPIRAL_WOUND" && (!hasText(item.sw_winding_material) || !hasText(item.sw_filler))) {
      pushRisk(risks, { severity: "medium", title: "Spiral wound material incomplete", detail: "Winding and filler material should be present.", rows: [row] });
    }
    if (toNumber(item.quantity, 0) <= 0) {
      pushRisk(risks, { severity: "high", title: "Invalid quantity", detail: "Quantity must be greater than zero.", rows: [row] });
    }
    if (text.includes("SPECIAL") || text.includes("CUSTOM") || text.includes("NON STANDARD") || text.includes("DRAWING")) {
      pushRisk(risks, { severity: "medium", title: "Non-standard item", detail: "Drawing/custom/non-standard wording requires engineering review.", rows: [row] });
    }
  });

  const highRiskPenalty = risks.filter((risk) => risk.severity === "high").length * 18;
  const mediumRiskPenalty = risks.filter((risk) => risk.severity === "medium").length * 8;
  const riskScore = Math.max(0, 100 - highRiskPenalty - mediumRiskPenalty);
  const score = Math.round(quoteScore * 0.3 + technicalScore * 0.5 + riskScore * 0.2);
  return { score, readiness, quoteScore, technicalScore, riskScore, missing: quoteMissing, risks };
}
