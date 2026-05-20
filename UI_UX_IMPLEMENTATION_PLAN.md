# UI/UX Implementation Plan

This plan upgrades the existing gasket enquiry and quotation application without replacing the current workflow. It is based on a review of the current implementation in:

- `apps/web/components/app-shell/app-shell.tsx`
- `apps/web/app/dashboard/dashboard-client.tsx`
- `apps/web/app/quotes/quotes-client.tsx`
- `apps/web/app/history/history-client.tsx`
- `apps/web/app/doc-assistant/doc-assistant-client.tsx`
- `apps/web/app/settings/settings-client.tsx`
- `apps/web/lib/api.ts`
- `apps/web/lib/material-planning.ts`
- `apps/api/app/routers/dashboard.py`
- `apps/api/app/schemas/quotes.py`
- `apps/api/app/db/repositories.py`
- `packages/core/quote_pdf.py`
- `packages/core/quote_exporter.py`

## Current Implementation Review

### What Is Correct And Should Be Preserved

- The application already has a useful workflow split: enquiry intake, material planning, final quotation, dashboard, history, document assistant, converter, and settings.
- `QuotesClient` is reused for draft, material planning, and final quotation sections. Keep this reuse, but break complex subviews into smaller components during implementation.
- The line-item table already supports sticky headers, frozen selection/tools columns, inline editing, status filtering, bulk editing, reprocessing, recompute, deletion, and regret marking.
- The app already has item quality scoring, derived missing/review notes, approval state, PDF preview/export, material planning output, and activity history.
- The API schema is flexible: `quote_data`, `stage_meta`, and `items` are JSON-capable, which allows incremental workflow metadata before adding hard database columns.
- The recent fixes are correct directionally: final/material stage filtering should not fall through to draft stages, duplicate final queue UI should stay removed, and customer line references should live on item rows and export into PDF/XLSX.

### Main Current Gaps

- Navigation is static and role-light. Current roles are only `admin`, `approver`, `sales`, and `viewer`; they do not map cleanly to estimation, purchase, planning, management, and coordination workflows.
- Dashboard metrics are too thin for operations. Backend currently returns total quotes, items, pending review, sent, PO, conversion, win rate, total value, stage counts, and gasket type distribution only.
- Enquiry queue does not expose owner, due date, priority, quote value, clarification status, delay, or next action.
- The line-item table is powerful but too wide. It needs task-specific column presets, better cell-level validation, confidence-first review, and a selected-row side panel.
- Technical review signals are present but not grouped into an engineer-friendly action checklist.
- Quote preparation lacks item cost, margin, margin threshold, discount approval logic, and a stronger approval banner.
- Material planning estimates stock needs, but does not include available stock, reserved stock, shortage, suggested purchase, vendor options, lead time, or cost impact.
- Vendor enquiry is not yet a first-class workflow.
- History is useful but should become both a per-quote timeline and an operational audit view.

## Implementation Principles

- Improve the existing app incrementally. Do not create a separate replacement UI.
- Keep `quote_data`, `stage_meta`, and item-level JSON as the first storage layer for new workflow metadata unless reporting/query needs require first-class columns.
- Keep visible pages dense and work-focused. This is an internal industrial SaaS tool, not a marketing site.
- Every new UI feature must answer one of these questions quickly: what is this enquiry, what is missing, who owns it, what is the next action, what is the risk, what is the value, and when is it due?
- Add tests where behavior is deterministic: filtering, status calculations, dashboard metric aggregation, export fields, material planning calculations, and helper functions.

## Data Model Plan

### Item-Level Fields

Use item JSON for these fields:

- `customer_sl_no`
- `customer_item_code`
- `owner_note`
- `clarification_note`
- `technical_review_status`
- `drawing_required`
- `is_non_gasket`
- `urgent`
- `duplicate_group_id`
- `validation_issues`
- `cost_price`
- `target_margin_pct`
- `selling_price`
- `vendor_quote_refs`

### Quote-Level `stage_meta`

Use `stage_meta` for workflow metadata:

- `owner_id`
- `owner_name`
- `priority`
- `due_date`
- `follow_up_at`
- `clarification_status`
- `clarification_requested_at`
- `clarification_resolved_at`
- `estimated_quote_value`
- `last_customer_contact_at`
- `next_action`
- `approval`
- `material_plan`
- `vendor_enquiries`
- `activity_flags`
- `saved_views`

### Quote-Level `quote_data`

Keep commercial quotation details here:

- Customer and buyer details
- Currency, FX rate, taxes, discount
- Unit prices
- Cost/margin summaries
- Packing, freight, delivery, payment terms
- Technical notes
- Revision details

### Backend Changes

Start with JSON metadata. Add hard database columns only after UI and reports prove they are needed for performance:

- Likely future columns: `owner_id`, `priority`, `due_date`, `estimated_quote_value`, `next_action`, `clarification_status`.
- Keep migrations small and backwards-compatible.

## Phase 0: Stabilize Current UI Before Feature Work

### Tasks

1. Keep the current queue filter fix in `apps/web/app/quotes/quotes-client.tsx`.
2. Keep duplicate final queue removal.
3. Keep item-level customer reference fields and export support:
   - `apps/web/lib/api.ts`
   - `apps/web/app/quotes/quotes-client.tsx`
   - `packages/core/quote_pdf.py`
   - `packages/core/quote_exporter.py`
   - `apps/api/tests/test_export_parity.py`
4. Extract reusable helpers from `QuotesClient` before adding more UI:
   - `components/quotes/stage-utils.ts`
   - `components/quotes/quality-utils.ts`
   - `components/quotes/item-validation.ts`
   - `components/quotes/quote-summary-row.tsx`

### Acceptance Criteria

- Final quotes show in `/quotes/final`.
- Material planning quotes show in `/material-planning`.
- Draft quotes show in `/quotes`.
- Customer line reference fields appear in draft/final tables and PDF/XLSX exports.
- No duplicate final queue.

### Validation

Run from Command Prompt:

```bat
cd C:\Users\Raj Gandhi\goodrich
cmd /c npm.cmd run build
cmd /c .venv\Scripts\python.exe -m pytest apps\api\tests\test_export_parity.py -q
cmd /c git diff --check
```

## Phase 1: Navigation And Role-Based Workspaces

### Must-Have

Create role-aware navigation and page grouping while preserving existing routes.

Current file:

- `apps/web/components/app-shell/app-shell.tsx`

Recommended structure:

- Work Queue
  - Dashboard
  - Enquiries
  - Clarifications
  - History
- Technical
  - Review Queue
  - Document Assistant
  - Converter
- Commercial
  - Final Quotation
  - Approvals
  - Follow-ups
- Planning/Purchase
  - Material Planning
  - Vendor Enquiries
- Admin
  - Settings

### Implementation Instructions

1. Extend roles in `apps/web/lib/auth/users.ts`:
   - `admin`
   - `management`
   - `approver`
   - `sales`
   - `estimation`
   - `technical`
   - `planning`
   - `purchase`
   - `viewer`
2. Add a `roles?: AppRole[]` property to nav items.
3. Filter nav items by the current user role.
4. Add grouped nav sections in `SidebarNav`.
5. Keep current URLs functional to avoid breaking bookmarks.
6. Add quick-create actions in the top header:
   - New enquiry
   - Upload documents
   - Search quote

### Should-Have

- Add recent enquiries in sidebar footer.
- Add saved views per role.
- Add global command/search shortcut later, for example `Ctrl+K`.

### Acceptance Criteria

- Sales users see enquiry, final quotation, follow-up, history.
- Estimation/technical users see enquiry review, doc assistant, converter.
- Planning/purchase users see material planning and vendor enquiries.
- Management users see dashboard, tracker, approvals, reports.
- Admin users see all pages.

## Phase 2: Dashboard Control Room

### Must-Have

Upgrade `apps/web/app/dashboard/dashboard-client.tsx` and `apps/api/app/routers/dashboard.py`.

Dashboard should show:

- New enquiries today
- Pending technical review
- Clarifications required
- Delayed enquiries
- Quotes pending approval
- Quotes submitted
- High-value enquiries
- Total open quote value
- Average quote cycle time
- Team workload

### Backend Implementation

Extend `/api/v1/dashboard/metrics` to return:

```ts
type DashboardMetrics = {
  total_quotes: number;
  items_processed: number;
  pending_review: number;
  quotes_sent: number;
  converted_to_po: number;
  conversion_rate: number;
  win_rate: number;
  avg_time_to_sent_days: number;
  total_quote_value: number;
  stage_counts: Record<string, number>;
  gasket_type_distribution: Record<string, number>;
  new_enquiries_today: number;
  clarification_required: number;
  delayed_enquiries: number;
  pending_approval: number;
  high_value_enquiries: number;
  owner_workload: Array<{ owner_id: string; owner_name: string; open_count: number; delayed_count: number; value: number }>;
  due_today: number;
  generated_at: string;
};
```

Use `stage_meta.due_date`, `stage_meta.owner_id`, `stage_meta.owner_name`, `stage_meta.clarification_status`, and `stage_meta.estimated_quote_value`.

### Frontend Implementation

1. Replace the current six equal cards with grouped KPI bands:
   - Intake
   - Review
   - Quote
   - Follow-up
   - Management
2. Add an urgent work table with:
   - Customer
   - Project/enquiry
   - Owner
   - Stage
   - Age
   - Due date
   - Value
   - Next action
3. Add workload view by owner.
4. Add stage funnel using existing `stage_counts`.
5. Keep gasket type distribution, but make it secondary.

### Should-Have

- Add date range filter.
- Add customer filter.
- Add “my work only” filter.
- Add export dashboard summary to Excel.

### Acceptance Criteria

- A manager can identify delayed, high-value, and blocked enquiries without opening each quote.
- A coordinator can identify who owns each pending quote.
- Dashboard still loads if `stage_meta` fields are missing.

## Phase 3: Enquiry Tracker And Work Queue

### Must-Have

Improve the existing queue inside `QuotesClient` before creating separate tracker pages.

Current file:

- `apps/web/app/quotes/quotes-client.tsx`

Add queue columns:

- Customer/workspace
- Stage
- Owner
- Priority
- Due date / age
- Items
- Review blockers
- Estimated value
- Next action
- Actions

### Implementation Instructions

1. Add helper functions:
   - `quoteAgeDays(quote)`
   - `quoteDueState(quote)`
   - `quoteEstimatedValue(quote)`
   - `quoteNextAction(quote, qualityReport)`
2. Store owner/priority/due date in `stage_meta`.
3. Add queue filters:
   - My work
   - Due today
   - Delayed
   - Clarification
   - High risk
   - High value
   - Stage
4. Add inline owner/priority edit from queue row or row action menu.
5. Preserve current search.

### Should-Have

Create `/tracker` later with:

- Kanban view by stage
- Table view
- Quote timeline view
- Follow-up calendar

### Acceptance Criteria

- Users can answer “what should I work on next?” from the queue.
- Delayed and clarification-required enquiries are visually obvious.
- Filters are usable without opening a quote.

## Phase 4: Line-Item Table Speed And Accuracy

### Must-Have

The existing table is strong but too wide. Improve it, do not replace it.

Current locations:

- `TABLE_COLUMNS`
- `COMPACT_TABLE_COLUMNS`
- `renderGridCell`
- `notesFor`
- `derivedNotesFor`
- `evaluateQuoteQuality`

### Implementation Instructions

1. Add column presets:
   - Review
   - Commercial
   - Soft cut
   - Spiral wound
   - RTJ
   - Kammprofile
   - DJI
   - ISK
   - Full technical
2. Add a preset selector above the table.
3. Add cell-level validation using `item-validation.ts`.
4. Highlight missing required cells:
   - Red for blocker
   - Amber for review
   - Muted for optional
5. Add confidence visual rules:
   - `>= 0.85` green
   - `0.65-0.84` amber
   - `< 0.65` red
6. Add smart filters:
   - Missing size
   - Missing material
   - Missing rating/class
   - Low confidence
   - Drawing required
   - Duplicate likely
   - Non-gasket
   - Regret
7. Add selected-row side panel:
   - Customer original description
   - GGPL generated description
   - Missing/review notes
   - All technical fields
   - Similar quote suggestions placeholder
   - Clarification note
8. Keep bulk edit, but add gasket-specific bulk templates.

### Should-Have

- Duplicate detection by normalized type/size/rating/material/quantity.
- Keyboard navigation:
  - Arrow keys move cells
  - Enter edits
  - `Ctrl+S` saves
  - `R` toggles regret for selected row
  - `F` focuses filters
- Export reviewed table to Excel.

### Acceptance Criteria

- Estimation engineer can review low-confidence and missing rows first.
- The most important columns stay visible without full horizontal scrolling.
- Missing technical fields are visible in the cell, not only in a notes column.

## Phase 5: Technical Review Workspace

### Must-Have

Create a technical review panel inside the enquiry page before adding a new route.

### Implementation Instructions

1. Add a `TechnicalIssuesPanel` component that groups issues:
   - Missing size/dimensions
   - Missing class/rating/standard
   - Missing material/MOC
   - Missing SW winding/filler/ring details
   - Missing RTJ ring/groove/hardness
   - Conflicting fields
   - Drawing required
   - Non-gasket items
2. Add row badges:
   - `Drawing`
   - `Non-gasket`
   - `Clarification`
   - `Urgent`
   - `Duplicate`
3. Add clarification note fields at item level and quote level.
4. Add “Build clarification email” using existing RFI flow.
5. Add customer-specific requirements placeholder in `stage_meta.customer_requirements`.

### Should-Have

- Similar previous quotes panel:
  - Search by customer, gasket type, size, rating, material.
  - Initially use client-side search over `listQuotes()` results.
  - Later add backend endpoint for indexed search.
- Side-by-side source document preview for uploaded files.

### Acceptance Criteria

- Technical team has one visible list of blockers.
- Clarification requests can be built from grouped missing data.
- Non-gasket/drawing-based lines are not accidentally treated as ready.

## Phase 6: Quote Preparation And Approval

### Must-Have

Improve the existing final quotation screen.

Current section:

- `isFinalSection`
- `Quotation preparation`
- `approvalState`
- `requestApproval`
- `decideApproval`
- `exportCurrent`

### Implementation Instructions

1. Split final quote UI into compact sections:
   - Customer details
   - Item pricing
   - Cost/margin
   - Terms
   - Approval
   - Preview/export
2. Add item pricing fields:
   - Cost price
   - Margin %
   - Selling price
   - Discount impact
3. Add quote summary:
   - Subtotal
   - Discount
   - Tax
   - Grand total
   - Gross margin
   - Lowest line margin
4. Add approval thresholds:
   - Discount above threshold requires approval.
   - Margin below threshold requires approval.
   - High-risk technical issues require approval.
5. Improve approval banner:
   - Status
   - Requested by/at
   - Approved/rejected by/at
   - Comment/rejection reason
   - Required changes
6. Keep PDF preview/export, but make preview area easier to access.

### Should-Have

- Live PDF preview pane on wide screens.
- Revision comparison: changed price, changed quantity, changed terms.
- Customer-specific default terms.
- One-click copy quote summary for email.

### Acceptance Criteria

- Sales can see price, margin, discount, approval status, and PDF export in one workflow.
- Quote export remains locked when approval is required.
- Rejected approvals show clear reason and next required action.

## Phase 7: Material Planning With Stock And Shortage

### Must-Have

Extend current `MaterialPlan` rather than replacing it.

Current files:

- `apps/web/lib/material-planning.ts`
- material planning section in `QuotesClient`

### Implementation Instructions

1. Extend `MaterialPlanRow`:
   - `available_qty`
   - `reserved_qty`
   - `shortage_qty`
   - `suggested_purchase_qty`
   - `lead_time_days`
   - `preferred_vendor`
   - `estimated_material_cost`
   - `production_priority`
2. Add editable planning columns in the material planning table.
3. Add grouped summary:
   - By material
   - By stock form
   - By thickness
   - By vendor
4. Add shortage warnings.
5. Save updated material plan into `stage_meta.material_plan`.

### Should-Have

- Import stock from CSV/Excel.
- Add vendor options per material.
- Add cost impact back into quote costing.
- Add production priority queue.

### Acceptance Criteria

- Planning team can identify what is available, what is short, and what must be purchased.
- Purchase quantities are grouped by material and stock type.
- Material plan remains reviewable and saved on the quote.

## Phase 8: Vendor Enquiry Workflow

### Must-Have

Create a first version using `stage_meta.vendor_enquiries`; do not start with a separate database table unless persistence/reporting requires it.

### Implementation Instructions

1. Add route:
   - `apps/web/app/vendor-enquiries/page.tsx`
   - `apps/web/app/vendor-enquiries/vendor-enquiries-client.tsx`
2. Add nav item under Planning/Purchase.
3. Allow users to create vendor enquiry from:
   - Selected quote items
   - Selected material plan rows
4. Vendor enquiry fields:
   - Vendor name
   - Contact
   - Material/group
   - Quantity
   - Required date
   - Status: draft, sent, replied, selected, rejected
   - Quoted price
   - Lead time
   - Remarks
5. Save into `stage_meta.vendor_enquiries`.
6. Add compare view for vendor price and lead time.

### Should-Have

- Vendor master list.
- Email template generation.
- Attach vendor quote files.
- Push selected vendor price into item/material costing.

### Acceptance Criteria

- Purchase can generate supplier enquiries without leaving the quote workflow.
- Vendor responses can be compared and used for costing.

## Phase 9: History, Timeline, Saved Filters, And Micro-Interactions

### Must-Have

Improve operational confidence and reduce mistakes.

### Implementation Instructions

1. Add per-quote timeline component using existing `stage_history` and `stage_meta.exports`.
2. Add activity log entries for:
   - Owner change
   - Priority change
   - Due date change
   - Clarification requested/resolved
   - Approval requested/approved/rejected
   - Vendor enquiry sent/replied
3. Add auto-save indicator where edits are local but unsaved.
4. Add undo for row delete and bulk regret.
5. Add saved filters in local storage:
   - Per page
   - Per role
6. Add recently viewed quotes.

### Should-Have

- Global smart search.
- Keyboard shortcuts.
- Toasts with action links.
- “Copy link to quote” action.

### Acceptance Criteria

- Users can recover from accidental delete.
- Users can return to recent work quickly.
- Quote history shows meaningful workflow events, not only stage/export events.

## Suggested Component Refactor

Before adding large features, split `QuotesClient` into smaller components:

- `components/quotes/quote-queue.tsx`
- `components/quotes/enquiry-intake.tsx`
- `components/quotes/item-review-table.tsx`
- `components/quotes/item-detail-panel.tsx`
- `components/quotes/technical-issues-panel.tsx`
- `components/quotes/material-plan-panel.tsx`
- `components/quotes/final-quotation-panel.tsx`
- `components/quotes/approval-panel.tsx`
- `components/quotes/quote-kpi-strip.tsx`

Keep state ownership in `QuotesClient` initially. Move state only after components stabilize.

## Test Plan

### Frontend

Run:

```bat
cd C:\Users\Raj Gandhi\goodrich\apps\web
cmd /c npm.cmd run build
```

Add focused tests later if a frontend test runner is introduced. Until then, keep logic-heavy code in pure helper functions that can be unit tested from TypeScript if test tooling is added.

### Backend And Export

Run:

```bat
cd C:\Users\Raj Gandhi\goodrich
cmd /c .venv\Scripts\python.exe -m pytest apps\api\tests\test_export_parity.py -q
cmd /c .venv\Scripts\python.exe -m pytest -q
```

Add tests for:

- Dashboard metrics with `stage_meta` owner/due/clarification/value.
- Export of customer line reference fields.
- Material planning shortage calculations.
- Stage transition history metadata.

### Manual QA Checklist

- Draft queue shows only initial/review quotes.
- Material queue shows initial/review/quote_prep/repricing quotes.
- Final queue shows quote_prep/repricing/sent/po quotes.
- Search works in all queues.
- New enquiry intake still supports email, Excel, and manual rows.
- Line-item edits save and survive refresh.
- Bulk edit still works.
- RFI draft still works.
- Material plan generation still works.
- Approval request/approve/reject still works.
- PDF preview and PDF download still work.
- Exported PDF/XLSX include customer serial and customer item code fields.

## Recommended Delivery Order

1. Phase 0 stabilization and component extraction.
2. Phase 2 dashboard metrics and dashboard UI.
3. Phase 3 queue owner/due/priority/next-action improvements.
4. Phase 4 table presets, validation, and side panel.
5. Phase 6 quote preparation margin/approval improvements.
6. Phase 7 material planning stock/shortage columns.
7. Phase 8 vendor enquiry workflow.
8. Phase 1 full role-based navigation once the target role pages exist.
9. Phase 5 similar quotes and source document preview.
10. Phase 9 saved filters, timeline, and micro-interactions.

This order delivers management visibility and daily processing speed first, while keeping the current workflow usable throughout the upgrade.
