import type { Quote } from "@/lib/api";

import { getString } from "./item-validation";

export type QuoteSection = "drafts" | "material" | "final" | "po";
export type EnquiryStageId = "draft" | "technical_clarification" | "material_planning" | "pricing" | "price_breakup";

export const DRAFT_STAGES = new Set(["initial", "review"]);
export const MATERIAL_STAGES = new Set(["initial", "review", "quote_prep", "repricing"]);
export const FINAL_STAGES = new Set(["quote_prep", "repricing", "sent", "po"]);
export const PO_STAGES = new Set(["po"]);

export const ENQUIRY_STAGES: Array<{ id: EnquiryStageId; label: string }> = [
  { id: "draft", label: "Draft" },
  { id: "technical_clarification", label: "Technical clarification" },
  { id: "material_planning", label: "Material planning" },
  { id: "pricing", label: "Pricing" },
  { id: "price_breakup", label: "Price breakup" },
];

const ENQUIRY_STAGE_IDS = new Set<EnquiryStageId>(ENQUIRY_STAGES.map((stage) => stage.id));
const OPEN_CLARIFICATION_STATUSES = new Set(["required", "drafted", "requested"]);

export function revisionLabel(quote: Quote): string {
  const revNo = getString(quote.quote_data?.rev_no);
  return revNo ? `Rev ${revNo}` : "";
}

export function stageLabel(stage: string) {
  const labels: Record<string, string> = {
    initial: "Enquiry",
    review: "Review",
    quote_prep: "Quotation prep",
    repricing: "Repricing",
    sent: "Sent",
    po: "PO",
  };
  return labels[stage] ?? stage.replace("_", " ");
}

export function enquiryStageFromQuote(quote: Quote): EnquiryStageId {
  const explicit = getString(quote.stage_meta?.enquiry_stage) as EnquiryStageId;
  if (ENQUIRY_STAGE_IDS.has(explicit)) return explicit;
  if (quote.stage_meta?.price_breakup || quote.stage_meta?.price_breakup_updated_at) return "price_breakup";
  if (quote.stage === "quote_prep" || quote.stage === "repricing" || quote.stage === "sent" || quote.stage === "po") return "pricing";
  if (quote.stage_meta?.material_planning_enabled === true) return "material_planning";
  if (OPEN_CLARIFICATION_STATUSES.has(getString(quote.stage_meta?.clarification_status)) || quote.items.some((item) => getString(item.clarification_note))) return "technical_clarification";
  return "draft";
}

export function enquiryStageLabel(quoteOrStage: Quote | EnquiryStageId | string): string {
  const stage = typeof quoteOrStage === "string" ? quoteOrStage : enquiryStageFromQuote(quoteOrStage);
  return ENQUIRY_STAGES.find((item) => item.id === stage)?.label ?? stage.replaceAll("_", " ");
}
