# Streamlit Feature-Parity Sub-Plan

This sub-plan narrows the migration to replacing the existing Streamlit app first.
New product features from `plan.md` remain deferred until the Streamlit feature set
is complete in the new FastAPI + Next.js application.

## Scope

Build only the functionality required to reach Streamlit parity:

- Document intake and manual entry.
- Existing Smart Parse pipeline behavior.
- Working list editor.
- Quote generation.
- Existing Python PDF export behavior.
- Existing Excel export behavior.
- Quote history and pipeline dashboard.
- Unit converter.
- Document Q&A assistant.
- Floating gasket chat.
- API key entry from the UI.
- Persistence and local fallback behavior.

Deferred until after parity:

- RAG / embeddings for document assistant.
- Prompt A/B testing.
- Advanced analytics.
- PWA/offline install work.
- ERP, email-in, portal, and customer self-service integrations.
- Production hardening beyond what is needed for parity.
- Redis quote cache. Redis remains off by default and may later store only final
  approved quotations, never extraction drafts or attempted quotes.

## Non-Negotiables

- Preserve all current Streamlit functionality.
- Preserve the existing core Smart Parse pipeline:
  `read_document_smart -> apply_rules -> format_description`.
- Do not reintroduce legacy regex-only or extractor-only flows.
- Preserve PDF output by continuing to call the existing Python PDF exporter.
- Preserve Excel export behavior by continuing to call the existing Python Excel
  exporter.
- Keep existing root imports and package imports working.
- Run required verification after each relevant phase.
- If implementation conflicts with `plan.md`, stop and explain the conflict before
  changing behavior.

## Phase A: Persistence Before UI

Goal: make the API capable of replacing Streamlit state.

Tasks:

- Replace the API `InMemoryRepository` with real Postgres/Supabase-backed
  persistence.
- Preserve local fallback behavior for development/offline mode.
- Persist quotes, items, quote form data, stage history, stage metadata, and
  generated export metadata.
- Keep org/user columns in place, while allowing local development defaults.
- Keep Redis disabled by default.
- Ensure Redis, when explicitly enabled later, can cache only final approved
  `po` quotations.

Verification:

```cmd
python -m compileall app.py packages tests apps\api apps\streamlit core data domain services ui pages
pytest -q
```

Acceptance:

- Quote data survives API restart.
- Saved quote data can restore a working quote workspace.
- Persistence shape remains compatible with existing Streamlit history behavior.

## Phase B: Quote Workspace Web UI

Goal: rebuild the Streamlit quote workspace in Next.js.

Tasks:

- Add customer and project / PO reference capture.
- Add intake tabs for:
  - email body paste
  - Excel upload (`.xlsx`, `.xls`)
  - PDF upload
  - manual single-item entry
- Ensure all intake paths append to the current working list.
- Add clear/start-new behavior matching Streamlit.
- Add API key entry in the UI and pass the key to API extraction calls when an
  environment key is not configured.

Verification:

```cmd
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
pytest -q apps\api\tests
```

Acceptance:

- A user can create a quote workspace and add items through every Streamlit intake
  path.

## Phase C: Smart Parse Job Experience

Goal: preserve the current extraction experience.

Tasks:

- Wire web intake forms to API extraction endpoints.
- Ensure the API invokes existing `services.extraction.process_document`.
- Preserve `read_document_smart -> apply_rules -> format_description`.
- Surface existing error cases:
  - scanned PDF / no extractable text
  - OpenAI rate limit
  - invalid API key
  - no gasket items found
  - partial chunk failures
- Show progress and live preview in the web UI.
- Append extracted rows to the existing working list.
- Preserve truncation warnings beyond 400 rows.
- With Redis disabled, use database-backed job state and polling or SSE that does
  not depend on Redis pub/sub.

Acceptance:

- Extraction output, statuses, warnings, and append behavior match Streamlit for
  the same documents.

## Phase D: Working List Grid

Goal: replace Streamlit `st.data_editor` behavior.

Tasks:

- Add editable grid coverage for all current `GasketItem` fields.
- Show status icons and color coding for ready, check, missing, and regret.
- Add blank row at the end or after the selected row.
- Support multi-row selection and bulk delete.
- Support bulk edit of selected rows or all visible rows across current Streamlit
  bulk-edit fields:
  - type
  - MOC
  - rating
  - face
  - groove
  - thickness
  - BHN
  - UOM
  - SW winding
  - SW filler
  - SW outer ring
  - SW inner ring
  - standard
- Re-run rules and formatter after edits.
- Reprocess edited customer descriptions through Smart Parse.
- Mark and unmark regret.
- Filter by status.
- Add extraction summary.
- Add missing-field clarification panel.
- Add downloadable RFI `.txt` draft grouped by flag and line number.

Verification:

```cmd
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
pytest -q apps\api\tests
```

Acceptance:

- Every Streamlit working-list action has an equivalent web action.

## Phase E: Quote Generation

Goal: rebuild the Streamlit quote page exactly in the new web app.

Tasks:

- Add buyer details form:
  - buyer name/address
  - customer enquiry number
  - attention
  - designation
  - contact number
  - email
- Add GGPL sales representative fields:
  - name
  - designation
  - contact number
  - email
- Add quote reference fields:
  - quote number
  - quote date
  - revision number
  - revision date
- Add 12-currency selection with editable FX rates.
- Add pricing editor:
  - quantity override
  - UOM display
  - base INR unit price
  - converted unit price
  - total price
- Preserve GST and discount behavior:
  - discount applies before tax
  - GST applies only for INR quotes
  - IGST / CGST+SGST / UGST supported
- Add all terms and conditions fields:
  - price basis
  - validity
  - packing
  - freight
  - payment terms
  - bank charges
  - delivery
  - inspection
  - insurance
  - HSN code
  - LD clause
  - cancellation
  - minimum order value
- Add technical notes.
- Generate PDF through existing `core.quote_pdf.build_quotation_pdf`.
- Generate Excel through existing `core.quote_exporter.build_quotation_excel`.
- Save generated export metadata into quote history.
- Add start-new behavior matching Streamlit.

Acceptance:

- Generated PDF and Excel are downloadable from the new app and produced by the
  existing Python exporters.

## Phase F: Export Parity Harness

Goal: prove output preservation before cutover.

Tasks:

- Add an Excel comparison harness using `openpyxl`:
  - sheet dimensions
  - cell values
  - number formats
  - styles/fills/fonts where applicable
- Add a PDF comparison harness:
  - extracted text comparison
  - page raster diff when local tooling is available
- Add fixtures covering:
  - INR quote with GST and discount
  - non-INR quote
  - regret rows
  - multi-page quote
  - long terms and technical notes

Acceptance:

- Excel has zero structural/style diffs for test fixtures.
- PDF text matches exactly.
- PDF visual diff stays within the tolerance from `plan.md` when raster tooling is
  available.

## Phase G: History And Pipeline Dashboard

Goal: rebuild Streamlit dashboard behavior.

Tasks:

- Add dashboard metrics:
  - total quotes
  - items processed
  - pending review
  - conversion rate
  - converted to PO
  - win rate
  - average time to sent
- Add gasket type distribution.
- Add pipeline stages:
  - initial
  - review
  - quote_prep
  - repricing
  - sent
  - po
- Add quote history search and filtering.
- Add open/resume quote behavior.
- Add rename and delete.
- Add stage advancement with metadata:
  - sent recipient/date/note
  - repricing note
  - PO number/value/date
- Add won/lost/reopen handling.
- Add generated PDF download from history.

Acceptance:

- Existing Streamlit history records can be found, reopened, staged, and
  downloaded in the new app.

## Phase H: Auxiliary Parity

Goal: rebuild the remaining Streamlit tools.

Tasks:

- Add unit converter page with:
  - length
  - DN/NPS pipe size
  - pressure
  - ASME Class / PN rating
  - temperature
  - torque
  - force
- Add document Q&A assistant:
  - PDF upload
  - DOCX upload
  - XLSX/XLS/XLSM upload
  - CSV upload
  - TXT upload
  - loaded document list
  - remove single document
  - clear all/reset
  - quick-question buttons
  - large-file warning
  - clear conversation
- Add floating gasket-domain chat widget:
  - bottom-right launcher
  - last 20 messages
  - API key handling
  - same gasket-domain behavior as Streamlit

Acceptance:

- Streamlit auxiliary workflows have equivalent web pages/components.

## Phase I: Cutover Readiness

Goal: prove parity before retiring Streamlit.

Tasks:

- Run backend and frontend verification.
- Run extraction fixture checks.
- Run export parity harness.
- Run manual smoke coverage:
  - login
  - create enquiry
  - extract from email
  - extract from Excel
  - extract from PDF
  - manual add
  - edit/bulk edit/regret/RFI
  - generate PDF
  - generate Excel
  - reopen from history
  - stage to sent
  - stage to PO
  - confirm Redis remains off/empty
- Keep Streamlit available until GGPL signoff.

Verification:

```cmd
python -m compileall app.py packages tests apps\api apps\streamlit core data domain services ui pages
pytest -q
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
docker compose ps
```

Acceptance:

- All Streamlit parity flows work in the new app.
- Core extraction and export behavior is preserved.
- Redis is still disabled by default and contains no extraction drafts or
  attempted quotes.
- Streamlit can remain as fallback until formal cutover.

## Recommended Next Step

Start with Phase A. More UI work on top of the current in-memory API will create
avoidable rework because Streamlit parity depends on saved quote continuity,
restore/resume, history, and export download behavior.
