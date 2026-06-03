# Layman-Friendly UI/UX Simplification Plan

## Purpose

The application has strong business functionality, but it still behaves like an expert tool. New or occasional users must understand the entire quotation process before they can complete a simple task.

The next UX pass should not add more visible functionality. It should make the existing functionality easier to discover, understand, and complete with fewer decisions.

The target experience is:

- **Slack-like orientation:** users always know where they are, what needs attention, and how to find work quickly.
- **Excel-like efficiency:** tabular work remains fast, familiar, filterable, and keyboard-friendly for experienced users.
- **Government-service clarity:** errors state exactly what is wrong and how to fix it.
- **Atlassian-like operational polish:** tables, statuses, empty states, inline edits, and notifications behave consistently.

This plan is based on a review of the active Next.js application, especially:

- `apps/web/components/app-shell/app-shell.tsx`
- `apps/web/app/dashboard/dashboard-client.tsx`
- `apps/web/app/quotes/quotes-client.tsx`
- `apps/web/app/history/history-client.tsx`
- `apps/web/app/doc-assistant/doc-assistant-client.tsx`
- `apps/web/app/vendor-enquiries/vendor-enquiries-client.tsx`
- `apps/web/app/settings/settings-client.tsx`

The earlier `UI_UX_IMPLEMENTATION_PLAN.md` remains useful for feature depth. This document is a simplification layer focused specifically on usability for layman users.

## Research Summary

### Slack: Orientation, Search, And Attention

Slack keeps a small number of primary navigation areas visible, groups secondary content into sidebar sections, and provides a single search entry point. Its simplified layout mode reduces distractions and presents a landing page, navigation toolbar, search, create action, help, and an activity view for items that need attention.

Apply this to GGPL Quote:

- Add one obvious home page: **My Work**.
- Keep a short sidebar with plain-language groups.
- Add one global search box for enquiry number, customer, quote number, PO number, and project.
- Add one **Needs Attention** view instead of scattering blockers across screens.
- Keep advanced tools available but visually secondary.

Sources:

- [Slack sidebar preferences](https://slack.com/help/articles/212596808-Adjust-your-sidebar-preferences)
- [Slack simplified layout mode](https://slack.com/help/articles/41214514885907-Use-simplified-layout-mode-in-Slack)
- [Search in Slack](https://slack.com/help/articles/202528808-How-to-search-in-Slack)
- [Slack keyboard shortcuts](https://slack.com/help/articles/201374536-Slack-keyboard-shortcuts-and-commands)

### Excel: Familiar Tables, Frozen Context, And Quick Actions

Excel works for operational users because the grid is predictable. Users can keep headers and important columns visible, sort and filter data, use keyboard navigation, and place frequently used commands in a quick-access area. Excel also allows commands to collapse when users need more working space.

Apply this to GGPL Quote:

- Keep spreadsheet-style item editing.
- Freeze the item identity columns and header row.
- Show a small default column set and let users expand technical columns.
- Put the five most common row actions in a compact toolbar.
- Keep rare actions in a `More` menu.
- Preserve a fullscreen grid mode for expert users.

Sources:

- [Freeze panes in Excel](https://support.microsoft.com/en-us/office/freeze-panes-to-lock-rows-and-columns-dab2ffc9-020d-4026-8121-67dd25f2508f)
- [Sort data in Excel](https://support.microsoft.com/en-us/office/quick-start-sort-data-in-an-excel-worksheet-60153f94-d782-47e2-96a8-15cbb7712539)
- [Excel keyboard shortcuts](https://support.microsoft.com/en-us/office/keyboard-shortcuts-in-excel-1798d9d5-842a-42b8-9c99-9b7213f0040f)
- [Quick Access Toolbar](https://support.microsoft.com/en-gb/office/add-commands-to-the-quick-access-toolbar-f733e1a6-53b1-4388-a609-173d03895ab7)
- [Show or collapse the ribbon](https://support.microsoft.com/en-us/office/show-the-ribbon-26abd81c-b5ab-47a5-aabc-a9e5255862f4)

### Atlassian: Consistent Operational Components

Atlassian's design system treats dynamic tables, inline editing, status indicators, empty states, and event-driven messages as reusable patterns. Empty states should explain what happened and what the user can do next. Notifications should match the severity and context of the event.

Apply this to GGPL Quote:

- Use consistent status chips across dashboard, queue, workspace, material planning, and quotation.
- Make safe metadata editable in place.
- Use empty states with one clear next action.
- Use small toast notifications for confirmations and inline warnings for fixable problems.
- Reserve page-level banners for blocking conditions.

Sources:

- [Atlassian dynamic table](https://atlassian.design/components/dynamic-table/)
- [Atlassian inline edit](https://atlassian.design/components/inline-edit)
- [Atlassian empty state](https://atlassian.design/components/empty-state/)
- [Atlassian message guidance](https://atlassian.design/foundations/content/designing-messages/)

### GOV.UK: Clear Error Recovery

The GOV.UK Design System recommends showing a summary of errors and placing the same clear message beside the exact field that needs correction. Generic messages such as "An error occurred" are not sufficient.

Apply this to GGPL Quote:

- Add a visible `Fix 4 issues` summary above forms and item tables.
- Link each issue to the row or field that needs attention.
- Write specific messages such as `Enter the gasket size` or `Select a pressure class`.
- Separate user-fixable validation errors from system errors.

Sources:

- [GOV.UK error summary](https://design-system.service.gov.uk/components/error-summary/)
- [GOV.UK error messages](https://design-system.service.gov.uk/components/error-message/)

## Current UX Diagnosis

### What Should Be Preserved

- The app shell and role-aware navigation already provide a solid base.
- The workflow is correctly represented as enquiry, material planning, quotation, and customer PO.
- Dashboard urgency, owner workload, filters, undo, item presets, fullscreen grid, technical issue handling, quotation tabs, and vendor enquiries are valuable.
- The same `QuotesClient` supports multiple workflow stages. Preserve its behavior while extracting clearer subcomponents.

### Why Layman Users Still Struggle

#### 1. Too Many Actions Are Visible At The Same Time

The item workspace and material-planning screen expose many controls together. Expert users can interpret them, but new users must inspect buttons and infer the intended order.

#### 2. The App Shows Process Internals Instead Of A Guided Task

Terms such as `Phase 1 breakdown`, `Phase 2 material plan`, `repricing`, extraction options, review controls, and approval controls are meaningful to the implementation or experienced users. A new user needs a simple instruction: **what should I do next?**

#### 3. Information Hierarchy Is Too Flat

Primary actions, secondary actions, status indicators, and utility actions often compete visually. The interface needs one dominant action per task area and a quiet place for less common controls.

#### 4. The Quote Workspace Is Too Large

`apps/web/app/quotes/quotes-client.tsx` is a large multi-stage workspace. Even when the underlying logic is correct, presenting intake, rows, issue review, bulk tools, material operations, pricing, approval, exports, and integration utilities without a stronger task structure creates cognitive overload.

#### 5. Advanced And Beginner Workflows Are Mixed

Experienced estimators need dense editing, shortcuts, presets, bulk edits, and fullscreen spreadsheets. Occasional users need defaults, explanations, confirmation, and a guided path. Both can coexist, but the beginner path must be the default.

## Design Rules

Use these rules for every screen:

1. Show one clear primary action per section.
2. Use plain-language labels. Put technical terms in helper text when necessary.
3. Start with the minimum useful information. Reveal detail on demand.
4. Make status and next action visible without opening a record.
5. Use the same status names and colors everywhere.
6. Do not rely on color alone. Pair color with text and icons.
7. Keep dangerous actions behind a menu and require confirmation.
8. Keep expert efficiency features available without making them the default view.
9. Explain empty states and errors with a next step.
10. Avoid adding a new page unless it removes complexity from an existing one.

## Proposed App Structure

### Simplified Sidebar

Replace the current navigation wording with:

| Group | Visible Item | Purpose |
| --- | --- | --- |
| Start | **My Work** | Tasks assigned to the current user and items needing attention |
| Work | **Enquiries** | Create and review incoming customer enquiries |
| Work | **Material Planning** | Plan material only when an enquiry reaches that step |
| Work | **Quotations** | Prepare price, approval, and customer quote |
| Work | **Orders** | Accepted quotes and PO handover |
| More | **Vendor Enquiries** | Supplier requests and comparisons |
| More | **Document Assistant** | Ask questions about uploaded documents |
| More | **Reports** | History and analytics |
| Admin | **Settings** | User management and configuration |

Changes:

- Rename `Dashboard` to `My Work`.
- Rename `Enquiry` to `Enquiries`.
- Rename `Quotation` to `Quotations`.
- Rename `Customer PO` to `Orders`.
- Move low-frequency tools into a collapsed **More** section.
- Remove descriptive subtitles from expanded sidebar navigation. They increase visual noise. Use tooltips or a short onboarding tour instead.
- Keep step numbers only inside a quote workspace, not in global navigation. A user can enter the app at different stages depending on their role.

### Global Header

Add a clean header with:

- Search field: `Search customer, enquiry, quote, PO...`
- `New enquiry` primary button
- `Needs attention` icon with a count
- Help icon
- User menu

Move `Local workspace` into the user menu or environment tooltip. It is system context, not a daily action.

### My Work Home Page

The default landing page should answer: **What do I need to do today?**

Use four compact sections:

1. **Needs attention**
   - Overdue
   - Missing customer information
   - Technical review needed
   - Approval waiting

2. **My tasks**
   - Customer
   - Enquiry or quote number
   - Current step
   - Due date
   - Next action
   - One `Continue` button

3. **Recently opened**
   - Last five records

4. **Team overview**
   - Visible only for managers and admins

Do not start with analytics charts for normal users. Charts belong below the work list or in Reports.

## Guided Enquiry Workspace

### Replace The Flat Workspace With A Stepper

Inside one enquiry, show a horizontal progress tracker:

1. **Add enquiry**
2. **Review items**
3. **Resolve issues**
4. **Plan material**
5. **Prepare quote**
6. **Send quote**
7. **Record order**

Rules:

- Highlight the current step.
- Show completed steps with a check.
- Allow experienced users to open previous steps.
- Prevent moving forward only when a true blocker exists.
- Explain blockers next to the disabled button.

### Persistent Enquiry Header

Keep a compact sticky record header visible while scrolling:

- Customer
- Enquiry number
- Project
- Current step
- Owner
- Due date
- Save status
- Primary `Continue` button
- Secondary `More` menu

Move rare actions such as create revision, clear workspace, integration utilities, and secondary exports into `More`.

### Step 1: Add Enquiry

Make intake feel like a short guided start:

- Default choice: `Upload customer file`
- Secondary choices: `Paste email` and `Add manually`
- Show one sentence under each choice.
- After extraction, automatically move to `Review items`.
- Collapse the intake panel after successful extraction, with an `Add more files` action.

Replace implementation wording with user wording:

| Current Or Technical Wording | User-Friendly Wording |
| --- | --- |
| Capture enquiry | Add customer enquiry |
| Run extraction | Read file and add items |
| Reprocess | Read selected rows again |
| Manual | Add item manually |

### Step 2: Review Items

Default to a clean table with these visible columns:

- Row
- Customer item code
- Description
- Type
- Size
- Material
- Quantity
- Status

Keep remaining technical fields under:

- `Show more columns`
- Saved table presets
- Row detail side panel

Toolbar:

- Primary: `Add item`
- Common: `Filter`, `Columns`, `Edit selected`
- Secondary menu: `Read again`, `Mark regret`, `Delete`, `Export`

Table behavior:

- Freeze header and identity columns.
- Keep search and filters directly above the table.
- Show active filters as removable chips.
- Support keyboard navigation and `Ctrl+S`.
- Preserve fullscreen spreadsheet mode as an expert feature.

### Step 3: Resolve Issues

Create one clear issue checklist:

```text
4 issues need attention
[ ] Row 2: Enter gasket size
[ ] Row 4: Select pressure class
[ ] Row 7: Confirm material
[ ] Row 9: Customer clarification required
```

Clicking an issue should:

- Open the relevant row.
- Focus the exact field.
- Show the same message beside the field.

Use three issue levels:

- **Must fix:** cannot progress.
- **Please review:** user can confirm or proceed.
- **Information:** useful but not blocking.

Do not show confidence scores prominently to layman users. Translate them into `Ready`, `Please review`, and `Missing information`. Keep numeric confidence in row details for experts.

## Material Planning Simplification

The current screen should be presented as one guided task instead of two technical phases.

Use:

1. **Create breakdown**
   - Helper text: `Calculate the material needed from reviewed enquiry items.`

2. **Review purchase plan**
   - Show grouped material rows.
   - Highlight shortages.
   - Allow quantity and vendor edits.

3. **Finish planning**
   - Primary action: `Send to quotation`

Replace labels:

| Current Wording | User-Friendly Wording |
| --- | --- |
| Phase 1 breakdown | Material needed |
| Phase 2 material plan | Purchase plan |
| Generate breakdown | Create material breakdown |
| Finish material planning | Send to quotation |

Move CSV copy/download tools into an `Export` menu.

## Quotation Simplification

Keep the existing tabs, but turn them into a guided sequence:

1. **Customer details**
2. **Prices**
3. **Terms**
4. **Review**
5. **Approval**
6. **Download and send**

Changes:

- Show completion state on each tab.
- Put a sticky price summary on the right:
  - Subtotal
  - Discount
  - Tax
  - Total
  - Margin
- Show one primary action at a time:
  - `Continue to terms`
  - `Request approval`
  - `Download quotation`
  - `Mark as sent`
- Keep XLSX download, preview, revisions, and secondary export actions under `More`.
- Show approval blockers in plain language.

Example:

```text
Approval is required before download
Margin is below the allowed limit on 2 items.
[Review prices]
```

## Status Language

Create one centralized status vocabulary and use it everywhere:

| Internal State | Visible Label |
| --- | --- |
| draft / intake | New |
| review | Review items |
| clarification | Waiting for customer |
| material planning | Plan material |
| quote_prep | Prepare quote |
| approval pending | Waiting for approval |
| approved | Ready to send |
| sent | Sent to customer |
| po | Order received |
| regret | Not quoting |

Use a small, consistent set of colors:

- Gray: not started or neutral
- Blue: active work
- Amber: waiting or needs review
- Red: blocked or overdue
- Green: complete

## Empty States, Messages, And Confirmations

### Empty States

Every empty state should explain why the area is empty and provide at most one primary action.

Examples:

```text
No enquiries yet
Add the first customer enquiry to begin.
[New enquiry]
```

```text
No items need attention
All extracted items are ready for the next step.
[Continue to material planning]
```

### Save Feedback

Add a small persistent save indicator in the enquiry header:

- `Saving...`
- `Saved`
- `Could not save. Try again`

Avoid success toasts for every minor auto-save. Use toasts for meaningful events such as extraction completed, approval requested, PDF downloaded, or material plan finished.

### Destructive Actions

Use confirmation dialogs for delete, clear workspace, reject approval, and overwrite actions:

- State what will be removed.
- State whether undo is available.
- Use a specific action label such as `Delete 3 items`.

## Beginner And Expert Modes

Do not create separate products. Use progressive disclosure.

### Default View

- Guided stepper
- Minimal columns
- Plain-language labels
- One primary action
- Issue checklist
- Helper text

### Expert Features

- Fullscreen spreadsheet
- Table presets
- Bulk edits
- Keyboard shortcuts
- Detailed confidence values
- CSV tools
- Advanced technical fields
- Saved filters

Expose expert features through `Show more columns`, `More`, and keyboard shortcuts.

## Visual Cleanup

Use a quieter visual system:

- Reduce the number of bordered cards on a single screen.
- Use whitespace and headings to group content before adding another container.
- Keep one primary button color.
- Use destructive red only for destructive actions and blockers.
- Remove redundant page headings when the app header already names the page.
- Keep body copy short.
- Use sentence case consistently: `Material planning`, not `Material Planning`.
- Keep icons only when they improve recognition.
- Use tooltips for icon-only buttons.
- Avoid exposing raw IDs unless needed for support or auditing.

## Onboarding And Help

Add lightweight onboarding for occasional users:

1. First-login welcome panel with three actions:
   - `Add a new enquiry`
   - `Continue assigned work`
   - `Watch how the workflow works`

2. Five-step product tour:
   - Search
   - My Work
   - New enquiry
   - Workflow stepper
   - Needs attention

3. Contextual help:
   - `What does this mean?` beside technical terms
   - Short explanations, not a large manual

4. Demo workspace:
   - Add one sample enquiry that users can safely explore.

## Implementation Order

### Phase 1: Immediate Simplification

Highest impact, lowest risk:

1. Rename navigation and move secondary tools under `More`.
2. Change `Dashboard` into `My Work` with tasks first and analytics second.
3. Add global search in the header.
4. Add a sticky enquiry header with save state and one primary next action.
5. Move rare workspace actions into `More`.
6. Simplify material-planning wording.
7. Standardize status labels and colors.
8. Improve empty states and specific error messages.

### Phase 2: Guided Workflow

1. Add the enquiry stepper.
2. Add completion checks and blockers per step.
3. Add the issue summary linked to exact rows and fields.
4. Make the minimal item-table preset the default.
5. Add `Show more columns`, active filter chips, and a compact toolbar.
6. Reorganize quotation into a guided sequence with a sticky summary.

### Phase 3: Learnability And Speed

1. Add first-login onboarding.
2. Add contextual help for technical terms.
3. Add recently opened records.
4. Add `Needs attention`.
5. Add keyboard shortcut help.
6. Add saved views for expert users.

### Phase 4: Validate With Real Users

Test with at least:

- One sales user who is not technical
- One estimator
- One material-planning user
- One approver
- One new user with no training

Ask each user to complete:

1. Add an enquiry from a file.
2. Fix one missing item field.
3. Move an enquiry to material planning.
4. Prepare a quote and request approval.
5. Find a quote sent last week.

Measure:

- Completion rate without assistance
- Time per task
- Number of wrong clicks
- Number of times the user asks what to do next
- Fields or terms users do not understand

## Concrete First Refactor

Implement the first pass in these areas:

- `apps/web/components/app-shell/app-shell.tsx`
  - Simplify labels.
  - Add global search.
  - Add `Needs attention`.
  - Move environment status into the user menu.

- `apps/web/app/dashboard/dashboard-client.tsx`
  - Reframe as `My Work`.
  - Place the user's task list first.
  - Move charts below operational work.

- `apps/web/app/quotes/quotes-client.tsx`
  - Add sticky enquiry header.
  - Add workflow stepper.
  - Reduce visible buttons.
  - Move advanced actions into menus.
  - Make minimal columns the default.
  - Add linked issue summary.
  - Replace technical labels with user-facing labels.

- `apps/web/components/quotes/`
  - Extract `workflow-stepper.tsx`.
  - Extract `quote-workspace-header.tsx`.
  - Extract `quote-issues-summary.tsx`.
  - Extract `item-table-toolbar.tsx`.
  - Keep `QuotesClient` as the initial state owner.

## Definition Of Done

The simplification work is successful when:

- A new user can add and progress an enquiry without training.
- Every active quote shows a visible next action.
- Every blocker explains how to fix it.
- A normal screen has one visually dominant action.
- The default item table fits the common review task without excessive horizontal scrolling.
- Advanced tools remain available but do not distract occasional users.
- Navigation uses plain language and keeps secondary tools out of the main workflow.
- Sales, estimation, planning, and approval users can find their assigned work from the landing page.

## Code Review Findings

The usability work should begin with a stabilization pass. The active code already contains several defects and contract gaps that can make the interface misleading or cause avoidable data loss.

### Priority 0: Fix Before UI Simplification

#### 1. Queue Summaries Drop Item Data But Frontend Helpers Still Depend On Items

**Files**

- `apps/api/app/routers/quotes.py`
- `apps/web/lib/api.ts`
- `apps/web/components/quotes/quote-summary-row.tsx`
- `apps/web/components/quotes/queue-utils.ts`

`GET /api/v1/quotes?summary=true` intentionally returns each quote with `items: []`. The frontend queue uses this summary endpoint, but queue rows still call:

- `evaluateQuoteQuality(quote, quote.items, ...)`
- `quoteEstimatedValue(quote)`
- `quoteHasClarification(quote)`
- `quoteIsHighRisk(quote)`
- `quoteNextAction(quote)`

This causes misleading queue behavior:

- Risk badges can disappear because risk checks run against an empty item list.
- Clarification filters miss item-level clarification notes.
- High-risk filters miss item-level technical risks.
- Estimated value can show `-` unless `stage_meta.estimated_quote_value` was separately populated.
- High-value filtering can fail for quotes whose value exists only in line pricing.
- Next-action recommendations can be incomplete.

**Fix**

Extend the summary API contract with explicit derived fields:

```ts
type QuoteSummary = Quote & {
  estimated_quote_value: number;
  high_risk_count: number;
  has_clarification: boolean;
  next_action: string;
};
```

Calculate these fields on the backend from the full quote before stripping items. Do not recompute them from empty arrays on the client.

#### 2. Generic PATCH Authorization Allows Over-Broad Quote Changes

**Files**

- `apps/api/app/routers/quotes.py`
- `apps/web/app/quotes/quotes-client.tsx`

The API allows `PATCH /quotes/{quote_id}` when the user has any one of:

- `edit_sales_details`
- `edit_workflow`
- `edit_line_items`
- `edit_quotation`
- `edit_material_phase2`

The patch is then passed directly to `repo.update_quote(...)`. This means a user with only one narrow capability can submit fields outside that capability, such as items, quotation data, or workflow metadata.

The frontend attempts partial restriction with `canSavePayload`, but frontend checks are not an authorization boundary and can be bypassed.

**Fix**

Validate patch fields on the backend against the caller's capabilities. Prefer dedicated endpoints for:

- Sales details
- Workflow metadata
- Line items
- Material plan
- Quotation commercial data

Keep a generic admin patch only if genuinely required.

#### 3. Editing Items Invalidates Material Plan Only In Local State

**File**

- `apps/web/app/quotes/quotes-client.tsx`

`invalidateMaterialPlan()` calls only:

```ts
setMaterialPlan(null);
```

Item edit paths call this function and then save the changed items. They do not clear the persisted `stage_meta.material_plan`, `material_breakdown`, or material-plan status fields.

Result:

- A user edits gasket items after material planning.
- The local plan disappears during that session.
- Reloading the material-planning page restores the old persisted plan.
- Planning users can unknowingly work from stale material requirements.

**Fix**

Persist an invalidation marker whenever an item change affects planning:

```ts
stage_meta.material_plan_stale = true;
stage_meta.material_plan_stale_at = now;
```

Keep the prior plan visible but read-only with a warning. Require `Recalculate material needed` before submission or finishing.

### Priority 1: Correctness And Data-Loss Risks

#### 4. Unsaved-Change Warning Fires For Saved Records And Misses In-App Navigation

**File**

- `apps/web/app/quotes/quotes-client.tsx`

The `beforeunload` effect activates whenever a quote has items or is a quotation. It does not check `hasUnsavedLocalEdits`.

This creates two problems:

- Browsers warn users when leaving records that are already saved.
- In-app actions such as `Clear workspace`, `New enquiry`, and opening another quote do not consistently ask the user to save or discard actual unsaved changes.

**Fix**

- Register `beforeunload` only when `hasUnsavedLocalEdits === true`.
- Add one shared `confirmDiscardUnsavedChanges()` guard before record switches, workspace clearing, new enquiry creation, route changes, and quotation-screen transitions.
- Prefer an app dialog with `Save and continue`, `Discard changes`, and `Cancel`.

#### 5. Clarification Workflow Uses Conflicting Status Values

**Files**

- `apps/web/app/quotes/quotes-client.tsx`
- `apps/web/components/quotes/queue-utils.ts`
- `apps/web/components/quotes/stage-utils.ts`
- `apps/api/app/routers/dashboard.py`

Building a clarification email writes:

```ts
clarification_status: "requested"
```

Dashboard metrics and several frontend helpers only recognize:

```ts
clarification_status === "required"
```

Result:

- A drafted or requested clarification can disappear from dashboard counts.
- `Resolve clarification` may not appear as the next action.
- Stage labels and queue filters can disagree.

**Fix**

Centralize a typed clarification state:

```ts
type ClarificationStatus =
  | "none"
  | "required"
  | "drafted"
  | "requested"
  | "resolved";
```

Define which states count as blocked or waiting for customer, and use the same helper on frontend and backend.

#### 6. Dashboard Metrics Can Double Count Linked Enquiry And Quotation Records

**Files**

- `apps/web/app/quotes/quotes-client.tsx`
- `apps/api/app/routers/dashboard.py`

Creating a quotation creates a new `quote_prep` record and keeps the original enquiry record. The records are linked by:

- `stage_meta.linked_quote_id`
- `stage_meta.source_enquiry_id`

Dashboard metrics iterate over all quote records without distinguishing workflow records from unique opportunities.

Potentially inflated values:

- Total quotes
- Items processed
- New enquiries today
- High-value enquiries
- Gasket-type distribution
- Open quote value
- Team workload

**Fix**

Define dashboard entities explicitly:

- **Enquiry metrics:** count source enquiries only.
- **Quotation metrics:** count quotation records only.
- **Pipeline metrics:** group linked records under one opportunity id.

Add `stage_meta.opportunity_id` or derive it consistently from source links.

#### 7. Next-Action Logic Returns Blank For Common Enquiry States

**File**

- `apps/web/components/quotes/queue-utils.ts`

`quoteNextAction()` returns an empty string for `initial` and `review` stages unless another earlier condition matches. This leaves queue rows and dashboard work lists without a usable next action.

The delayed check also appears after several stage returns, so overdue work may not receive `Recover delay`.

**Fix**

Return explicit actions:

| Condition | Next Action |
| --- | --- |
| New enquiry without items | Add customer enquiry |
| Extracted rows need review | Review items |
| Clarification requested | Follow up customer |
| Material plan stale | Recalculate material needed |
| Material planning enabled | Plan material |
| Quote preparation | Prepare quotation |
| Approval pending | Follow up approval |
| Sent | Follow up customer |
| Overdue | Prefix action with `Overdue:` |

### Priority 2: Usability Gaps Already Visible In Code

#### 8. Spreadsheet Mode Is The Default Instead Of Guided Review

**File**

- `apps/web/app/quotes/quotes-client.tsx`

The code defaults to:

```ts
const DEFAULT_TABLE_MODE = "spreadsheet";
```

This is useful for experts but conflicts with the goal of making the app usable for layman users.

**Fix**

- Default new users to `guided`.
- Remember an explicit user preference.
- Keep spreadsheet mode one click away.

#### 9. Row Deletion Has Undo But No Confirmation Or Clear Scope Message

**File**

- `apps/web/app/quotes/quotes-client.tsx`

`deleteSelectedRows()` immediately saves the deletion. Undo is helpful, but the destructive button is visible beside common table tools and does not confirm the count or scope.

**Fix**

- Move delete into `More`.
- Confirm with `Delete 3 selected items?`
- Explain that undo is available until another row-changing action.

#### 10. Dashboard Is Team-Wide, Not A Personal My-Work View

**File**

- `apps/web/app/dashboard/dashboard-client.tsx`

The urgent table is built from every open quote. `currentUser` is loaded but not used to prioritize or filter assigned work.

**Fix**

- Default normal users to `My tasks`.
- Add a manager-only `Team overview`.
- Add a visible toggle for `My work` and `All work` when permitted.

#### 11. Queue Metadata Handler Is Passed To Rows But Not Used

**Files**

- `apps/web/app/quotes/quotes-client.tsx`
- `apps/web/components/quotes/quote-summary-row.tsx`

`QuoteSummaryRow` receives `onMetaChange`, but the component does not use it. Owner, due date, and priority edits are available only after opening the record.

**Fix**

Add a compact row action menu:

- Assign owner
- Set due date
- Set priority
- Copy link

Keep the main row clean.

#### 12. Technical Issue Count Overstates Unique Affected Rows

**File**

- `apps/web/components/quotes/technical-issues-panel.tsx`

The panel calculates:

```ts
summary.reduce((sum, group) => sum + group.rows.length, 0)
```

A single row can appear in multiple issue groups, so the displayed `issue row(s)` count can exceed the number of affected rows.

**Fix**

Display both:

- `4 rows need attention`
- `7 issues across 3 groups`

#### 13. Material Planning Uses Internal Phase Language

**File**

- `apps/web/app/quotes/quotes-client.tsx`

The UI contains repeated `Phase 1` and `Phase 2` labels. These reflect implementation order, but new users need task language.

**Fix**

Rename:

- `Phase 1 material breakdown` to `Material needed`
- `Start Phase 2` to `Create purchase plan`
- `Phase 2 material plan` to `Purchase plan`
- `Finish material planning` to `Send to quotation`

### Missing Tests

Add focused tests before the UI refactor:

1. Summary queue API returns derived value, risk, clarification, and next-action fields.
2. A sales-details-only user cannot patch items, approval metadata, or quotation pricing.
3. Editing an item marks a persisted material plan stale.
4. Clarification `required`, `drafted`, `requested`, and `resolved` states produce consistent queue and dashboard behavior.
5. Dashboard groups linked enquiry and quotation records correctly.
6. Saved records do not trigger unload warnings.
7. Unsaved changes are guarded before switching records.
8. Next action is non-empty for every open workflow state.

## Revised Stabilization Order

Complete these before visual restructuring:

1. Fix backend PATCH authorization.
2. Fix the quote-summary API contract.
3. Enforce material-plan staleness in the backend for every item mutation path.
4. Centralize clarification states.
5. Define allowed workflow transitions and linked-record deletion behavior.
6. Add optimistic concurrency protection for quote updates.
7. Correct dashboard grouping and local-date calculations.
8. Fix unsaved-change handling.
9. Make guided review the default.
10. Then proceed with navigation, My Work, workflow stepper, and visual cleanup.

## Second-Pass Safety Review

The usability direction is sound, but the initial rollout order was still too optimistic. The interface should not be simplified on top of ambiguous backend behavior. A cleaner stepper or more prominent next-action button would make those backend gaps easier to trigger.

The implementation must preserve existing routes, stored JSON metadata, exports, role behavior, linked enquiry-to-quotation behavior, and expert workflows while improving the default experience.

### Additional Priority 0 Findings

#### 14. Material-Plan Invalidation Must Be A Backend Invariant

**Files**

- `apps/api/app/routers/quotes.py`
- `apps/api/app/services/extraction_runner.py`
- `apps/api/app/db/repositories.py`
- `apps/web/app/quotes/quotes-client.tsx`

The first review correctly identified stale material plans, but the proposed fix must not live only in `QuotesClient`.

Items can change through several paths:

- Generic quote PATCH requests
- Bulk item updates
- Bulk recompute updates
- Background extraction append operations
- Frontend item edits and deletions

Any one of these paths can make a persisted material plan stale.

**Fix**

Create one backend item-update service or repository helper. Whenever persisted items change and a material breakdown or plan already exists:

```py
stage_meta["material_plan_stale"] = True
stage_meta["material_plan_stale_at"] = now
```

The previous breakdown and purchase plan should remain visible as read-only reference data until recalculated. The frontend should display the warning and block submission or completion, but the backend must enforce the invariant.

#### 15. Workflow Transitions Are Not Constrained

**Files**

- `apps/api/app/routers/quotes.py`
- `apps/api/app/db/repositories.py`
- `apps/web/app/quotes/quotes-client.tsx`

`POST /quotes/{quote_id}/stage` accepts any valid stage value for users with `edit_workflow`. Generic PATCH also permits `stage` changes under the current broad authorization check.

The API checks approval before marking a quotation as `sent`, but it does not enforce the rest of the workflow. A guided stepper built on this API could skip required review, stale-plan recalculation, clarification resolution, or quotation preparation.

**Fix**

Define backend transition rules with explicit blockers:

| Transition | Required Checks |
| --- | --- |
| Enquiry review to material planning | Items exist, technical blockers resolved or explicitly waived |
| Material planning to quotation | Material plan is not stale and required planning work is complete |
| Quotation to approval | Required commercial details and pricing are present |
| Approval to sent | Approval rule passes |
| Sent to PO | Sent state exists and user has workflow capability |

Do not allow `stage` in generic PATCH for normal users. The stepper should call transition endpoints and render backend blocker messages.

#### 16. Deleting A Linked Record Can Orphan Its Counterpart

**Files**

- `apps/api/app/routers/quotes.py`
- `apps/api/app/db/repositories.py`
- `apps/web/app/quotes/quotes-client.tsx`

An enquiry and its quotation are linked through JSON metadata. Deleting either record removes only that row. The surviving record can retain a dead `linked_quote_id` or `source_enquiry_id`, causing navigation and synchronization failures.

**Fix**

Choose and enforce one policy:

- Prefer soft archive for records that have linked workflow history.
- Allow hard delete only for unlinked drafts.
- If an admin hard-deletes a linked record, update the counterpart atomically and retain an audit event.

The UI confirmation must name the impact before deletion.

#### 17. Quote Updates Have Versions But No Conflict Protection

**Files**

- `apps/api/app/schemas/quotes.py`
- `apps/api/app/db/repositories.py`
- `apps/web/app/quotes/quotes-client.tsx`

Quotes expose a `version`, but updates do not require the caller's expected version. Two users can open the same enquiry, edit different fields, and silently overwrite each other's JSON objects or item arrays.

This risk increases when quick row actions, a sticky header, autosave, and a guided stepper add more update surfaces.

**Fix**

- Require `expected_version` for mutable quote operations.
- Update only when the stored version matches.
- Return `409 Conflict` with the latest version when another user has saved first.
- Let the UI offer `Reload latest` and preserve the user's unsaved draft where practical.
- Keep activity logging for meaningful workflow changes.

### Additional Priority 1 Findings

#### 18. Dashboard Date Metrics Use UTC Instead Of The User's Business Day

**File**

- `apps/api/app/routers/dashboard.py`

Dashboard calculations use:

```py
now = datetime.now(timezone.utc)
today = now.date()
```

Due dates are compared against UTC. For users operating in India, `Due today`, `Delayed`, and `New enquiries today` can change at the wrong local time. `due_today` also currently includes completed `sent` and `po` records, while delayed records exclude them.

**Fix**

- Define the organization timezone, initially `Asia/Kolkata` unless settings specify another value.
- Calculate operational day boundaries in that timezone.
- Count `due_today`, delayed, and high-value operational work only within clearly defined open-record scopes.
- Add boundary tests around local midnight.

#### 19. Quotation Number Generation Is Client-Side And Can Race

**Files**

- `apps/web/app/quotes/quotes-client.tsx`
- `apps/api/app/db/repositories.py`

The browser calls `listQuotes()`, calculates the next quotation number, and then creates the quotation. The database does not enforce uniqueness for `quote_no`.

Two users creating quotations close together can receive the same quotation number.

**Fix**

- Allocate quotation numbers on the backend inside a transaction.
- Add an organization-scoped uniqueness guarantee for non-empty quotation numbers.
- Keep enquiry numbering and quotation numbering rules explicit and tested.

#### 20. Read Access Is Not Enforced On Quote List, Detail, History, Or Dashboard Endpoints

**Files**

- `apps/api/app/routers/quotes.py`
- `apps/api/app/routers/dashboard.py`

Authenticated users are tenant-scoped, but quote list, detail, history, and dashboard routes do not require their corresponding view capabilities. Hiding links in the sidebar is not sufficient authorization.

This matters when the new navigation introduces `My Work`, global search, and role-specific entry points.

**Fix**

- Require `view_enquiry`, `view_quotation`, `view_dashboard`, or an explicit combined read capability as appropriate.
- Apply the same policy to global search results.
- Test that a restricted user cannot retrieve hidden workflow records by calling the API directly.

## Rollout Guardrails

### Keep Existing Workflow Data Compatible

- Do not rename stored `stage`, `stage_meta`, or `quote_data` keys solely for display wording.
- Change labels in the UI while preserving existing persisted values.
- Add tolerant readers for new metadata such as `material_plan_stale`, `opportunity_id`, and clarification states.
- Backfill only when needed for reporting or constraints. Existing quotes must continue to open before and after deployment.

### Separate UI Labels From Backend State

Use user-facing wording such as `Material needed` and `Purchase plan`, but keep stable backend identifiers. The stepper is a presentation of the workflow, not a second workflow engine.

### Define A Dedicated Summary Contract

Do not extend the full `Quote` type informally. Add a dedicated backend and frontend summary DTO, for example:

```ts
type QuoteSummary = {
  id: string;
  quoteNo: string;
  customer: string;
  stage: QuoteStage;
  counts: QuoteCounts;
  estimatedQuoteValue: number;
  highRiskCount: number;
  hasClarification: boolean;
  nextAction: string;
  owner: QuoteOwner | null;
  priority: string;
  dueDate: string | null;
};
```

Queue rows, `My Work`, and search results should use this stable contract. The workspace should fetch the full record only when opened.

### Add Global Search As A Backend Feature

Do not implement header search by downloading every quote into the browser. Add a tenant-scoped, permission-aware backend search endpoint with:

- Quote or enquiry number
- Customer
- Project reference
- Owner
- Status
- Optional item-description search when needed
- Bounded results and debouncing

### Preserve Expert Workflows

- Default new users to guided mode.
- Remember an explicit spreadsheet-mode preference.
- Keep direct URLs for existing pages.
- Keep existing PDF/XLSX export behavior and customer line-reference fields.
- Keep advanced actions accessible under `More`; do not remove them.
- Move sidebar entries without deleting route access or capability checks.

### Release In Small, Reversible Steps

1. Add backend tests for current behavior and defects.
2. Fix backend invariants, authorization, transition rules, numbering, and concurrency.
3. Introduce the dedicated summary DTO and update queue consumers.
4. Correct dashboard grouping and timezone behavior.
5. Add unsaved-change protection.
6. Change labels and navigation presentation without changing persisted workflow values.
7. Add guided defaults, sticky header, and stepper behind a feature flag.
8. Validate exports, permissions, and linked workflows in staging.
9. Roll out to a small user group before making guided mode the default.

## Expanded Regression Checklist

Before enabling the simplified interface, verify:

1. Existing enquiries open without metadata migration failures.
2. Existing quotations still export equivalent PDF and XLSX documents.
3. Customer serial numbers and customer item codes remain present in exports.
4. Every item mutation path marks existing material plans stale.
5. A stale material plan cannot be submitted or completed.
6. Background extraction cannot silently leave an old material plan active.
7. Invalid stage jumps return a useful backend blocker message.
8. Deleting or archiving a linked record does not leave broken navigation.
9. Concurrent saves produce a visible conflict instead of silent overwrite.
10. Two simultaneous quotation creations cannot receive the same number.
11. Queue summaries produce correct risk, clarification, value, and next-action data.
12. Dashboard totals group linked records according to the documented metric definition.
13. Dashboard due-date calculations match the organization timezone.
14. Completed records do not appear in open-work due-today or high-value counts.
15. Restricted users cannot access hidden quotes through list, detail, search, history, or dashboard APIs.
16. Saved records do not show false unload warnings.
17. Actual unsaved edits are guarded before route changes and record switches.
18. Guided and spreadsheet modes edit the same underlying record without data loss.
19. Existing deep links to `/quotes`, `/quotes/final`, `/material-planning`, `/dashboard`, `/history`, `/doc-assistant`, `/tools/converter`, and `/settings` continue to work.

## Additional User Requirements And Confirmed Gaps

The following requirements should be treated as part of the stabilization and enquiry-preparation redesign, not as optional polish.

### Assignment Visibility: Non-Admins See Only Their Work

**Current gap**

The quote queue loads every tenant quote through `GET /quotes?summary=true`. The frontend exposes `My work` as an optional filter, but the default filter is `all`. Dashboard data is also team-wide.

This is a data-access defect, not only a default-filter issue. A non-admin user can still retrieve another user's quote by calling list or detail APIs directly.

**Required behavior**

- Admin users can see all work and assign or reassign records.
- Every non-admin user sees only records assigned to them.
- A newly created enquiry is assigned to its creator unless an admin assigns it differently.
- A quotation created from an enquiry inherits the enquiry assignment.
- Search, dashboard, history, queues, linked-record navigation, background-job links, and direct record URLs apply the same assignment rule.
- Unassigned records appear in an admin-only `Needs assignment` queue.
- Reassignment is recorded in activity history.

**Backend rule**

Enforce record visibility in repository queries and detail lookup helpers. Do not rely on a frontend filter:

```py
def can_view_quote(user: CurrentUser, quote: QuoteRead) -> bool:
    return user.role == "admin" or quote.stage_meta.get("owner_id") == user.user_id
```

Use a tolerant owner match during migration for existing records that stored owner email or name, then normalize to stable `owner_id`.

### Admin Permission Management Must Be Reliable And Testable

**Current gap**

The settings screen updates role permissions optimistically in local storage and sends a full settings object to the API. On failure, the UI shows an error but does not restore the last confirmed server state. This can make a failed permission change appear saved until refresh.

The backend also deliberately forces admin to retain every capability:

```py
role_permissions["admin"] = _permissions(ALL_CAPABILITIES)
```

That should remain explicit in the UI. Admin permissions are system guarantees, not editable toggles.

**Required behavior**

- Clearly label the admin row as `Full access (locked)`.
- For editable roles, show `Saving`, `Saved`, and `Could not save` states.
- Revert optimistic toggles when the API save fails.
- Reload server-confirmed permissions after save.
- Add a permission preview: `Users with this role can access: ...`.
- Add tests that each role receives exactly its configured page and action capabilities.
- Keep assignment visibility separate from role capabilities: non-admin users still see only assigned records even if their role grants access to a page.

### Visible Enquiry-Processing Progress

**Current gap**

The extraction backend already stores:

- `status`
- `progress`
- `message`
- parsed count
- skipped count
- error

`BackgroundJobMonitor` polls this data, but it renders nothing. Users see only a start toast and a completion or failure toast.

**Required behavior**

- Show an in-workspace progress card immediately after processing begins.
- Display a progress bar, percentage, current message, elapsed time, and cancel-or-dismiss behavior where supported.
- Keep processing visible if the user navigates elsewhere, using a compact global jobs indicator.
- On completion, show parsed row count and skipped row count.
- On failure, keep the failure card visible with the error and a retry action.
- Refresh the open enquiry automatically after processing succeeds.
- Prevent duplicate processing clicks while a job is active.

### Excel-Like Enquiry Item Editing

**Current state**

The item grid already supports part of the expected spreadsheet interaction:

- Cell selection and range selection
- Arrow navigation
- `Tab` and `Shift+Tab`
- `Enter` and `Shift+Enter`
- `F2` editing
- Copy
- Paste into existing rows
- Clear selected cells with `Delete` or `Backspace`
- Undo for some grid actions

**Required improvements**

- Use the spreadsheet grid as the primary processed-row experience.
- Freeze the row number and important identity columns while horizontally scrolling.
- Wrap long descriptions, flags, and summary notes by default with an optional compact-row toggle.
- Support multiline cell editing without making every row excessively tall.
- Make validation errors visible at the cell level with plain-language messages.
- Add a visible shortcut-help menu.
- Preserve the expert spreadsheet mode while keeping a simpler guided preset for new users.

**Excel-like shortcuts**

| Shortcut | Behavior |
| --- | --- |
| Arrow keys | Move active cell |
| `Shift` + Arrow keys | Extend selection |
| `Tab` / `Shift+Tab` | Move across editable cells |
| `Enter` / `Shift+Enter` | Move down or up |
| `F2` | Edit active cell |
| `Ctrl+C` / `Ctrl+V` | Copy or paste rectangular ranges |
| `Delete` / `Backspace` | Clear selected cell contents |
| `Ctrl+-` | Delete selected item rows after confirmation |
| `Ctrl+Shift++` | Insert blank rows above selection |
| `Ctrl+Z` | Undo the last supported row or cell action |
| `Ctrl+D` | Fill selected cells downward |

Keep destructive row deletion distinct from clearing cell contents. Confirm the number of rows being deleted and provide undo.

### Bulk Row Entry And Paste From Excel

**Current gap**

The manual-entry tab adds one item at a time through a separate form. The spreadsheet paste handler updates existing rows only. If pasted rows extend past the end of the grid, extra rows are skipped.

**Required behavior**

- Replace the single-row manual form with a bulk-entry grid.
- Add `Insert 1 row`, `Insert 5 rows`, and `Insert 10 rows`.
- Allow users to paste a rectangular range copied from Excel.
- Automatically append enough blank rows when pasted data exceeds the current row count.
- Add a paste preview when column mapping is ambiguous.
- Support header detection and manual column mapping.
- Preserve customer serial number, item code, description, quantity, and UOM during paste.
- Run deterministic normalization and validation after import.
- Mark pasted rows as requiring review when parsing confidence is low.

### Email Body Table Paste Must Preserve Structure

**Current gap**

The email-body input is a plain textarea. Pasting a table from Excel or an email client can flatten or misalign the content before extraction.

**Required behavior**

- Detect HTML-table clipboard content and tab-separated clipboard text.
- Preserve rows and columns in a structured paste preview.
- Let the user choose:
  - `Process as email text`
  - `Import detected table`
- Normalize copied email tables without losing line boundaries.
- Show the number of detected rows before processing.
- Keep the original pasted text available for reference.
- Add tests for Excel TSV paste, Outlook-style HTML tables, multiline descriptions, blank cells, and mixed text-plus-table email bodies.

### Extraction Summary Must Be Deterministic And Reviewable

**Current gap**

The extraction summary is derived in the frontend and can also be manually edited and stored in `stage_meta.extraction_summary_rows`. The summary table uses single-line inputs for summary item and notes, which makes long content difficult to review. There is no explicit discrepancy check between item rows and saved summary rows.

**Required behavior**

- Regenerate the base summary deterministically from the processed item rows.
- Display the generation timestamp and source item version.
- Highlight discrepancies when saved summary totals no longer match current item rows.
- Provide `Regenerate summary` and `Keep manual notes` actions.
- Separate generated fields from editable note fields.
- Wrap summary item text and notes.
- Show totals and skipped or unmatched rows.
- Prevent stale summary data from appearing current after item edits, extraction reruns, or row deletion.

**Data rule**

Store:

```ts
stage_meta.extraction_summary = {
  source_quote_version: number;
  generated_at: string;
  rows: SummaryRow[];
  unmatched_item_rows: number[];
};
```

Manual notes should be preserved separately by a stable summary key so regeneration does not discard user input.

## Additional Implementation Order

Fold these requirements into the stabilization work in this order:

1. Enforce assigned-record visibility for all non-admin API requests.
2. Fix admin permission saves, rollback behavior, and role-capability tests.
3. Add visible extraction progress using the existing job status data.
4. Fix deterministic extraction-summary generation and stale-summary detection.
5. Upgrade the spreadsheet grid with wrapping, row insertion, row deletion, undo, and shortcut help.
6. Replace single-row manual entry with a bulk-entry grid and Excel paste append behavior.
7. Add structured email-body table detection and paste preview.
8. Validate these changes with real enquiry files and copied tables before enabling the guided workflow by default.

## Additional Regression Checks

1. A non-admin list request returns only records assigned to that user.
2. A non-admin direct detail URL for another user's quote returns `403` or `404`.
3. A non-admin search request cannot reveal another user's records.
4. Admin users can see assigned, unassigned, and all records.
5. New enquiries and linked quotations inherit a valid owner.
6. Failed permission saves revert the settings UI to server-confirmed values.
7. Role-capability changes survive refresh and affect both page access and API authorization.
8. Processing progress appears immediately and updates while extraction runs.
9. Extraction failure remains visible and can be retried.
10. Completing extraction refreshes the open enquiry without a manual reload.
11. Pasting five Excel rows into a two-row grid appends the missing rows.
12. Row deletion, cell clearing, and undo remain distinct operations.
13. Multiline descriptions and summary notes wrap without hiding content.
14. Summary totals match processed item rows after extraction, edits, paste, and deletion.
15. Regenerating a stale summary preserves manual notes.
16. Excel TSV and Outlook HTML-table paste preserve row boundaries and important columns.
