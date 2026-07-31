import type { Quote } from "@/lib/api";

/**
 * Mandatory enquiry details (mirrors REQUIRED_ENQUIRY_DETAILS and
 * DETAIL_GATE_EXEMPT_ACTIONS in app/services/enquiry_workflow.py).
 *
 * Estimation files the enquiry and owns its header. Every team after it — the
 * reviewer, the pricing desk, sales — plus the enquiry register and the
 * quotation itself read those fields, and none of them can recover one that was
 * left blank. So an incomplete enquiry does not move on: not into spec check,
 * and not into any later step.
 *
 * The API enforces this; the portal mirrors it so the blocked handoff is shown
 * as a checklist before the button is pressed rather than as a 422 after it.
 * Keep the two tables in step.
 */

type DetailSource = "quote" | "quote_data" | "stage_meta";

/**
 * A detail counts as filled when ANY of its sources carries text. Several are
 * captured in more than one place (choosing a customer master fills the name,
 * choosing a contact fills the person), so any one source is enough.
 *
 * Deliberately NOT required: the internal notes and the Outlook thread (the
 * form marks both optional), the customer's own RFQ number (not every customer
 * sends one), and priority / enquiry stage (the system applies a default).
 */
export const REQUIRED_ENQUIRY_DETAILS: ReadonlyArray<{
  label: string;
  sources: ReadonlyArray<readonly [DetailSource, string]>;
}> = [
  { label: "Customer", sources: [["quote", "customer"], ["stage_meta", "customer_master_id"]] },
  { label: "Contact person", sources: [["quote_data", "attention"], ["stage_meta", "customer_contact_id"]] },
  { label: "Contact person email", sources: [["quote_data", "email"]] },
  {
    label: "Contact number",
    sources: [["quote_data", "contact_no"], ["quote_data", "mobile_no"], ["quote_data", "telephone_no"]],
  },
  { label: "Email subject", sources: [["quote", "custom_label"]] },
  { label: "Enquiry reference", sources: [["quote", "quote_no"]] },
  { label: "Quote type (export or domestic)", sources: [["stage_meta", "market_type"]] },
  { label: "Bidding or firm", sources: [["stage_meta", "bid_type"]] },
  { label: "Project name", sources: [["quote", "project_ref"]] },
  { label: "Country", sources: [["stage_meta", "country"]] },
  { label: "City", sources: [["stage_meta", "city"]] },
  { label: "EPC / project company", sources: [["stage_meta", "epc_name"]] },
  { label: "Sales rep", sources: [["stage_meta", "owner_id"]] },
  { label: "Due date", sources: [["stage_meta", "due_date"]] },
];

export const LINE_ITEMS_DETAIL_LABEL = "Line items (at least one)";

/**
 * The handoffs that stay open while details are missing: the ones whose whole
 * point is to GET the enquiry corrected. Anything absent from this set is gated,
 * so a transition added later is mandatory-by-default.
 */
export const DETAIL_GATE_EXEMPT_ACTIONS: ReadonlySet<string> = new Set([
  "raise_customer_query",
  "answer_customer_query",
  "return_spec_errors",
  // Legacy-machine equivalents: both return the enquiry to the team that has to
  // fix the specs.
  "return_to_estimation",
  "pricing_to_technical",
]);

function sourceText(quote: Quote, source: DetailSource, key: string): string {
  const container: Record<string, unknown> =
    source === "quote" ? (quote as unknown as Record<string, unknown>) : (quote[source] ?? {});
  const value = container[key];
  if (typeof value === "string") return value.trim();
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return "";
}

/**
 * The mandatory enquiry details still blank on this record, by label. Records
 * fetched as list summaries carry no line items, so the item count falls back to
 * n_items.
 */
export function enquiryDetailGaps(quote: Quote | null | undefined): string[] {
  if (!quote) return [];
  const gaps = REQUIRED_ENQUIRY_DETAILS.filter(
    (detail) => !detail.sources.some(([source, key]) => sourceText(quote, source, key)),
  ).map((detail) => detail.label);
  if (!(quote.items?.length ?? 0) && !(quote.n_items ?? 0)) gaps.push(LINE_ITEMS_DETAIL_LABEL);
  return gaps;
}

/** The mandatory details holding a given handoff back — empty when it may go. */
export function enquiryDetailBlockers(action: string, quote: Quote | null | undefined): string[] {
  if (DETAIL_GATE_EXEMPT_ACTIONS.has(action)) return [];
  return enquiryDetailGaps(quote);
}

/** The message to block a handoff with, or "" when the enquiry is complete. */
export function enquiryDetailGateMessage(action: string, quote: Quote | null | undefined): string {
  const gaps = enquiryDetailBlockers(action, quote);
  if (!gaps.length) return "";
  return `Fill in every enquiry detail before this enquiry can move forward — ${gaps.length} still missing: ${gaps.join(", ")}`;
}
