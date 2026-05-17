# Streamlit Parity Gaps

This file lists functionality that existed in the original Streamlit workspace but is not mirrored exactly in the new application yet.

Source references:
- Legacy workspace: [pages/2_Quote_Workspace.py](C:/Users/Raj%20Gandhi/goodrich/pages/2_Quote_Workspace.py)
- Legacy quote page: [ui/quote_page.py](C:/Users/Raj%20Gandhi/goodrich/ui/quote_page.py)
- New workspace: [apps/web/app/quotes/quotes-client.tsx](C:/Users/Raj%20Gandhi/goodrich/apps/web/app/quotes/quotes-client.tsx)

## Implemented

1. Clear working list / reset enquiry inputs
   - The new app now has a `Clear workspace` action that resets the current quote view and clears the workspace inputs.

2. Unsaved-progress browser warning
   - The new app now installs a `beforeunload` guard while a quote workspace or quotation screen is open.

3. Separate quotation-page flow
   - The new app now switches into a dedicated quotation screen with back and start-new actions, instead of keeping the entire quotation form inline in the working list.

## Still Missing Or Not Mirrored Exactly

1. Persistent in-page chat widget
   - The Streamlit workspace rendered the chat widget directly on the page.
   - The new app has a separate assistant route, but it does not mirror the always-available workspace chat panel from the original app.

2. Currency option parity
   - The legacy quotation screen offered more currency choices, including `AUD`, `CAD`, and `CNY`.
   - The new app currently exposes a shorter list of currencies.

3. Exact manual-add behavior
   - The old manual form required at least `Size` or `MOC`, then built the row description before rules were applied.
   - The new app’s manual row entry is simpler and does not reproduce that same validation and description-building flow.

## Changed Behavior That Still Exists In Some Form

1. Save and export workflow
   - The Streamlit app exposed a dedicated `Save form` action before PDF / Excel generation.
   - The new app auto-persists edits and exports from the workspace, so the behavior is present but not shaped the same way.

2. Quotation completion state
   - The Streamlit app showed a separate download-ready state after quotation generation.
   - The new app can still export PDF / Excel, but it does not present the same staged completion screen.
