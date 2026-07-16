import type { Quote } from "@/lib/api";

// The customer-facing "Quotation stage" lifecycle (distinct from the primary
// quote.stage pipeline and from the enquiry->quotation handoff workflow). Stored
// on quote_data.quotation_stage with history in quote_data.quotation_stage_history.
// This is the single source of truth — quotes-client, the enquiries list, and the
// dashboard all read from here.
export type QuotationStageId =
  | "draft_preparation"
  | "technical_review"
  | "costing"
  | "commercial_review"
  | "approval"
  | "ready_to_send"
  | "sent_to_customer"
  | "negotiation"
  | "revision"
  | "po_received"
  | "lost";

export const QUOTATION_STAGES: Array<{
  id: QuotationStageId;
  label: string;
  owner: string;
  description: string;
}> = [
  { id: "draft_preparation", label: "Draft preparation", owner: "Sales", description: "Customer details, enquiry references, line descriptions, and quote header are prepared." },
  { id: "technical_review", label: "Technical review", owner: "Engineering", description: "Specs, materials, risk items, drawings, deviations, and regret rows are checked." },
  { id: "costing", label: "Costing", owner: "Planning / costing", description: "Material, bought-out, machining, packing, freight, and overhead cost inputs are entered." },
  { id: "commercial_review", label: "Commercial review", owner: "Sales / commercial", description: "Margins, discount, currency, taxes, delivery, validity, and payment terms are reviewed." },
  { id: "approval", label: "Internal approval", owner: "Approver", description: "Approval is requested when margins, discount, risk, or value require sign-off." },
  { id: "ready_to_send", label: "Ready to send", owner: "Sales", description: "Quotation PDF is approved and ready for customer release." },
  { id: "sent_to_customer", label: "Sent to customer", owner: "Sales", description: "Approved quotation has been shared with the customer." },
  { id: "negotiation", label: "Negotiation", owner: "Sales", description: "Customer feedback, commercial negotiation, alternates, and clarifications are being handled." },
  { id: "revision", label: "Revision", owner: "Sales / engineering", description: "A revised quotation is being prepared after customer or internal changes." },
  { id: "po_received", label: "PO received", owner: "Sales", description: "Customer PO is received and the quotation is ready for handover." },
  { id: "lost", label: "Lost / closed", owner: "Sales", description: "Opportunity is closed without order, with loss reason captured in notes." },
];

export const QUOTATION_STAGE_INDEX = new Map(QUOTATION_STAGES.map((stage, index) => [stage.id, index]));

// When a quotation stage hasn't been set explicitly, derive a sensible one from
// the enquiry->quotation workflow position, so records that have reached pricing
// don't show as "Draft preparation". Covers both the granular and legacy steps.
const WORKFLOW_TO_QUOTATION_STAGE: Record<string, QuotationStageId> = {
  sent_for_pricing: "costing",
  pricing_decision: "costing",
  pricing: "costing", // legacy
  estimation_final_review: "commercial_review", // legacy post-pricing review
  quotation_generated: "ready_to_send",
  ready_for_customer: "ready_to_send", // priced, returned to sales
  sales_final: "ready_to_send", // legacy ready-for-customer
  quotation_sent_to_customer: "sent_to_customer",
};

function workflowStageOf(quote: Quote | null): string {
  const meta = (quote?.stage_meta ?? {}) as Record<string, unknown>;
  const granular = (meta.granular_workflow ?? {}) as Record<string, unknown>;
  return String(granular.current_stage || meta.workflow_stage || "");
}

export function quotationStageFromData(qd: Record<string, unknown>, quote: Quote | null): QuotationStageId {
  const explicit = (typeof qd.quotation_stage === "string" ? qd.quotation_stage : "") as QuotationStageId;
  // A real, non-default explicit stage wins outright. "draft_preparation" is the
  // value stamped on every new quote, so treat it as "unset" and let the
  // enquiry->quotation workflow position decide — otherwise a record that has
  // reached pricing still reads as a draft in the Quotations section.
  if (QUOTATION_STAGE_INDEX.has(explicit) && explicit !== "draft_preparation") return explicit;
  const derived = WORKFLOW_TO_QUOTATION_STAGE[workflowStageOf(quote)];
  if (derived) return derived;
  if (quote?.stage === "po") return "po_received";
  if (quote?.stage === "sent") return "sent_to_customer";
  return "draft_preparation";
}

export function quotationStageBadgeVariant(stage: QuotationStageId) {
  if (stage === "po_received") return "secondary";
  if (stage === "lost") return "warning";
  if (stage === "approval" || stage === "negotiation" || stage === "revision") return "warning";
  if (stage === "sent_to_customer" || stage === "ready_to_send") return "outline";
  return "muted";
}

// Convenience for list/dashboard badges: derives the numbered label
// (e.g. "3. Costing") and badge variant for a quote in one call.
export function quotationStageBadge(quote: Quote): { index: number; label: string; variant: ReturnType<typeof quotationStageBadgeVariant> } {
  const qd = (quote.quote_data ?? {}) as Record<string, unknown>;
  const id = quotationStageFromData(qd, quote);
  const index = QUOTATION_STAGE_INDEX.get(id) ?? 0;
  return { index, label: QUOTATION_STAGES[index].label, variant: quotationStageBadgeVariant(id) };
}
