# RULE V — STANDARDS SELECTION ENGINE (DATA-MAPPED EDITION)
### Only the standards that actually appear in GGPL's own enquiry data
### GGPL Enquiry Bot · applies across all quoted ranges (SC, SPW, RTJ, KAMM, DJI, ISK, specials)

> **Scope discipline:** this rule lists ONLY standards observed in the shared GGPL data
> (35k conversion pairs, ASME reference sheet, UNIQUE REQUIREMENT / FEEDBACK sheets, and
> the 23 real enquiry files). Nothing speculative. Any standard NOT listed here is handled
> by the catch-all in Part 5 — kept verbatim and flagged, never substituted.

---

## PART 1 — THE THREE KINDS OF STANDARD (only one goes in the slot)

| Kind | Observed in your data | Where it goes |
|---|---|---|
| **1. GASKET DIMENSIONAL** | ASME B16.20 · ASME B16.21 · ASME B16.47 (SERIES A) · ASME B16.47 (SERIES B) · API 6A · EN 1514 | **THE STANDARD SLOT** |
| **2. FLANGE / EQUIPMENT (context)** | ASME B16.5 ("to suit / for B16.5 flanges") · ASME B16.47 · API 6B / 6BX · API pressure classes 2000/3000/5000/10000/15000 PSI · ISO 27509 (compact flange) · client special flange codes (SP-FL25CK1S0216) | Context only. Drives the choice; appears in output only as `TO SUIT {flange std}` for ISK. **Never the slot.** |
| **3. MATERIAL / TEST / CERT** | NACE MR0175 / MR-01-75 / ISO 15156 · API 6FB (fire test) · BS 7531 GR X / GR Y · EN 10204 (2.2 / 3.1 / 3.1B) · ASTM (incl. A262 Practice E IGC) · PMI · EN 681 (elastomer) · client specs: KNPC EXH-SU-5150/5151, GS EP PVV147, SAIL, EIL, ADNOC AVL | **Side-fields** (material string, requirements, deviation, tech-review flags). NACE is the only one that may join the slot line when explicitly demanded. |

**Consequences seen in your files:**
- `International Standa : ASTM` (MTO email) → ASTM is a material standard → slot derived per Part 2.
- `RTJ Face as per ASME B16.5, 2500Lbs` → B16.5 is the FLANGE → slot = ASME B16.20.
- `API 6FB` on the FRSFE kit → fire-safe attribute in the string, not the dimensional standard.
- `EN 681 & EN 1514` (DN insulation kit) → EN 681 = material side-field; EN 1514 = slot.

---

## PART 2 — THE OBSERVED MAPPING (product × size world → slot)

| Product | ASME inch/class ≤24" | ASME inch/class 26"+ | DN / PN work | API wellhead |
|---|---|---|---|---|
| **SC** | `ASME B16.21` | `ASME B16.47 (SERIES A)` | `EN 1514` (or customer's citation) | — |
| **SPW** | `ASME B16.20` | `ASME B16.47 (SERIES A)`; SERIES B only if stated | `ASME B16.20` (GGPL house style, observed) or `EN 1514` if the customer works in EN | **never API** |
| **KAMM** | `ASME B16.20` | `ASME B16.47 (SERIES A)` or `(SERIES - B)` as stated | as SPW | — |
| **DJI** | `ASME B16.20` | `ASME B16.47` | — | — |
| **RTJ** | `ASME B16.20` (R11–R79) | `ASME B16.47 (SERIES-A)` / rings R93–R105, classes 300–900 only | — | `API 6A` (BX); `NACE MR-01-75 / ISO 15156, API 6B` (RX) |
| **ISK** | `ASME B16.20` / `ASME B16.5` / `TO SUIT ASME B16.5` (all observed) | `ASME B16.47 (SERIES-A)` | `EN 1514` + EN 681 material | `TO SUIT API 6A` |
| **Specials** (sheet, O-ring, plug, lip seal, diaphragm, manhole, corrugated, lens, transition) | `(NON STANDARD)` or `(AS PER DRAWING)` — no dimensional standard observed in your data | same | same | — |

**Observed legacy typos to normalise (from the FEEDBACK / historical data):**
`ASME 16.20` → ASME B16.20 · `ASME B16..20` → ASME B16.20 · `B-16.21` → ASME B16.21 ·
bare `16.5` / `16.20` → ASME B16.x · `ASME B16.50` on an ISK line → **ASME B16.5** ·
`B16.6 / B16.7 … B16.12` on sequential rows → Excel fill-handle artifact (Rule D).

---

## PART 3 — ASME RANGE GATES (from your own ASME reference sheet)

- Soft cut / SPW / KAMM / DJI: B16.5 world = NPS ½–24; B16.47 world = 26"–60".
- **RTJ rings exist ONLY** for NPS ½–24 (R11–R79) and NPS 26–36 (R93–R105, classes 300–900).
  NPS 22 has no listed ring. Everything else → Part 5.
- Class gaps: no CL400 at NPS ½–3 (use 600) · no CL900 at NPS ½–2½ (use 1500 dims) ·
  no CL2500 at NPS 14 and above (so `16" 2500#` in the KOC spares list is not a B16.5 item).
- 900#+ columns are the shift zones: 2"@900/1500 = R-24 · 3"@1500 = R-35 · 14"@900 = R-62 ·
  16"@900 = R-66 · 2"@2500 = R-26 · 1"@2500 = R-18.

---

## PART 4 — OBSOLETE CITATIONS OBSERVED (quote successor + one deviation)

| Cited in your data | Quote instead |
|---|---|
| `API 601` (GeM tender) | **ASME B16.20** |
| `API 605` (GeM tender) | **ASME B16.47 (SERIES B)** |
| `ANSI B16.x` (several files) | **ASME B16.x** — same number |
| `CAF` / asbestos jointing | material substitution to CNAF + mandatory deviation |
| `B16.21` on a spiral wound line (SAP PO short text) | product-correct `ASME B16.20` + deviation |
| `B16.47 Series B` on a 15mm soft-cut line (GeM tender) | `ASME B16.21` + deviation (ghost standard) |

Deviation wording: `API 601 CITED — SUPERSEDED; QUOTED TO ASME B16.20`

---

## PART 5 — THE NON-STANDARD TEST

### PART 5.0 — THE OD × ID LAW (fires on most non-standard work — read this first)

> **If the customer gives OD × ID × THK (or L × W × THK, or obround axes) and does NOT
> give a size + class / size + PN, the gasket is NON-STANDARD — for EVERY product family
> without exception: SC, SPW, RTJ, KAMM, DJI, ISK, sheet, O-ring, plug, lip seal,
> diaphragm, manhole, corrugated, lens, transition.**

Reason: a dimensional standard is a *table* keyed by size and class. With no size and no
class there is no table row to look up, so no standard can govern the dimensions. The
customer has supplied the dimensions precisely because no standard does.

Output: W3 template + `(NON STANDARD)`, or `(AS PER DRAWING)` when a drawing is
referenced/attached (Rule K). Never map the dims to the "nearest" standard size.

**Three cases to keep straight:**

| What the customer gives | Verdict | Slot |
|---|---|---|
| **Dims only** — `OD 2126 x ID 2100 x 4.5 THK, SS304 SPWD` | **NON-STANDARD** | `(NON STANDARD)` — or `(AS PER DRAWING)` if a drawing exists |
| **Size + class** (dims absent, or dims given as confirmation) — `2" x 300#, SPW SS316` | **STANDARD** | normal Part 2 slot. Given dims *corroborate*; if they contradict the standard dims for that size/class → **flag, do not silently pick** |
| **Dims only + a standard cited** — `OD 669/643 x 4.5 T, SS304L double jacketed, ASME B16.20` | **NON-STANDARD size** | `(NON STANDARD)` / `(AS PER DRAWING)`. The citation may be retained as a *construction* reference only: `CONSTRUCTION PER ASME B16.20`. B16.20 governing winding profile, ring thickness and materials does **not** make a non-tabulated size standard. |

**Do not** promote a dims-only line to standard just because the numbers happen to look
close to a flange gasket size. The only route from non-standard to standard is a human
decision — the STD / NON-STD column in the Rule K-2 DIM-FILL worksheet, where the bot may
*suggest* a match (±2mm) but the estimator confirms it.

### THE OTHER FIVE TRIGGERS (all evidenced in your files)

| # | Trigger | Example from your data |
|---|---|---|
| 2 | **Size/class outside the standard's range** | `56" x 300#` RTJ (rings stop at 36") · `16" 2500#` (no CL2500 ≥14") · `30" 1500#` RTJ |
| 3 | **Product/facing combination not covered** | round-to-REC transition gaskets; kammprofile with pass partitions / ribs; corrugated to mfr standard; damper & blower gaskets |
| 4 | **Special or proprietary flange** | `SP-FL25CK1S0216` (client flange spec) · `ISO 27509` compact flange seal rings |
| 5 | **Mating part is equipment, not piping** | HX shell/channel covers, tank & manway gaskets, glass-lined reactor lip seals, slug-catcher nozzles per drawing |
| 6 | **No standard identifiable and none inferable** | bare "IDK"/illegible rows → `KINDLY PROVIDE CLEAR SPEC` |

### How to write it
| Situation | Output |
|---|---|
| Dims given, no drawing | `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, {construction} (NON STANDARD)` |
| Dims given, drawing referenced/attached | `… (AS PER DRAWING)` + Rule K verify alert |
| Drawing-dependent, dims unread | Rule K-2 DIM-FILL placeholders + one worksheet |
| RTJ outside ring range | `AS PER ASME STANDARD RING NUMBER IS NOT AVAILABLE SO KINDLY PROVIDE DIMENSIONS` |
| Other products outside range | quote with `(NON STANDARD)` if dims derivable; else `KINDLY PROVIDE DIMENSIONS` |
| Special/proprietary flange | `KINDLY PROVIDE DIMENSIONS` + note the flange code for tech review |

### CATCH-ALL for standards not listed in Part 1
Keep the customer's citation **verbatim** in the slot, add
`FLAG: STANDARD {x} NOT IN GGPL LIBRARY — TECH REVIEW`, and never substitute an ASME
equivalent by guess. When it recurs, sales adds one row to Part 1/2 — the library grows
from real enquiries only.

*(Deliberately NOT pre-loaded, because they have not appeared in GGPL's enquiry data:
AWWA, JIS, GOST, GB/T, AS 2129, SANS, EN 12560, DIN 2690-series, ISO 7483, TEMA.
If one arrives, the catch-all handles it and it earns a library row then.)*

---

## PART 6 — CANONICAL SLOT FORMS (write exactly these)

```
ASME B16.20                  ASME B16.21                 ASME B16.47 (SERIES A)
ASME B16.47 (SERIES B)       ASME B16.47 (SERIES-A)      [RTJ large-size house form]
ASME B16.47 (SERIES - B)     [observed KAMM house form]
API 6A                       NACE MR-01-75 / ISO 15156, API 6B     [RX template]
EN 1514                      TO SUIT ASME B16.5          [ISK]
(NON STANDARD)               (AS PER DRAWING)
```
With explicit NACE demand: `…, NACE MR0175, ASME B16.20` — the dimensional standard stays last.
ISK lines additionally end with `(FIRE SAFE)` or `(NON FIRE SAFE)`; `API 6FB` may precede it
when the customer cites the fire test.

---

## PART 7 — OVERRIDE HIERARCHY (single source of truth)

```
1. RANGE VALIDITY      (size/class outside the standard beats everything -> NON-STANDARD)
2. PRODUCT CORRECTNESS (SPW is never B16.21 and never API; BX is always API 6A)
3. CUSTOMER'S EXPLICIT GASKET-DIMENSION CITATION   (honoured when 1-2 permit)
4. CUSTOMER'S FLANGE / MATERIAL / TEST CITATIONS   (context and side-fields only)
```
Every departure from what the customer wrote produces exactly ONE deviation note naming
both readings. Never silent; never argued inside the GGPL string.

---

## WORKED EXAMPLES (all drawn from your shared files)

```
1) "NPS 4, CNAF flat ring, Cl.150, as per ASME B16.21 for B16.5 flanges"
   SIZE: 4" X 150# X 3MM THK,CNAF,RF,ASME B16.21

2) "NPS 30 SPW SS316/flex graphite, Cl.150, as per ASME B16.20 for B16.5 flanges"
   SIZE: 30" X 150# X 4.5MM THK,SS316 SPIRAL WOUND ... ,ASME B16.47 (SERIES A)
   [30" leaves the B16.5 world; engine switches family]

3) "GSKT SPW 1 1/2" B16.21 #150 SS316 4.5THK"  (SAP short text)
   SIZE: 1-1/2" X 150# X 4.5MM THK,SS316 SPIRAL WOUND ... ,ASME B16.20
   DEV: SHORT TEXT CITES B16.21 - SPW QUOTED TO ASME B16.20

4) "SUPPLY OF SPIRAL WOUND GASKET 300#, 200MM ... confirming to API 601 or API 605"
   SIZE: NB 200 X 300# X 4.5MM THK, ... ,ASME B16.20
   DEV: API 601/605 CITED - SUPERSEDED; QUOTED TO ASME B16.20

5) "GASKET,RTJ,BX-162 ... FOR API-6BX FLANGE, PRESSURE ENERGISED TO API SPEC 6A"
   SIZE: BX-162,RTJ,OCTAGONAL,SOFT IRON CADMIUM PLATED,90 BHN HARDNESS,API 6A

6) "Insulation gasket kit EPDM EN 681 & EN 1514, 25 PN16, sewerage/hot water"
   SIZE: 25 DN X PN16#, INSULATING GASKET KIT, G10 WITH EPDM "O" RING, G10 WASHER,
   MS WASHER, G10 SLEEVES, WITHOUT STEEL CORE, FF, EN 1514, (NON-FIRE SAFE)
   [EN 681 -> material side-field]

7) "RING JOINT GASKET 22in 1500 lb; ISO 27509; seal ring for compact flange"
   AS PER ASME STANDARD RING NUMBER IS NOT AVAILABLE SO KINDLY PROVIDE DIMENSIONS

8) "Octagonal ring 56" x #300 (As per B16.47 Series A), SS 304H"
   AS PER ASME STANDARD RING NUMBER IS NOT AVAILABLE SO KINDLY PROVIDE DIMENSIONS
   [B16.47-A rings stop at 36" / R98]

9) "CAMPROFILE core SS316L 3.0MM + 0.5 graphite both sides, OD=560 ID=536, dwg attached"
   SIZE: 560MM OD X 536MM ID X 4MM THK (3MM CORE THK), SS316L KAMMPROFILE GASKET
   WITH GRAPHITE LAYERS ON BOTH SIDES (AS PER DRAWING)
   ALERT: DRAWING ATTACHED - VERIFY BEFORE RELEASE
```

---

## FAILURE MODES THIS RULE PREVENTS (all observed or near-missed in your data)

1. SPW quoted to `API 601` / `API 6A` — impossible or dead standard.
2. `B16.21` from an ERP short text stamped onto spiral wound lines.
3. Material/test standards (ASTM, NACE, EN 10204, API 6FB, BS 7531) landing in the slot.
4. `B16.47 Series B` ghost citation applied to a 15mm soft-cut gasket.
5. Out-of-range items (56" RTJ, 16" 2500#, 30" 1500# RTJ) force-fitted to the nearest ring.
6. Equipment/HX gaskets quoted as if a piping standard governed their dims.
7. A standard outside the library silently swapped for ASME instead of flagged.

## VALIDATION ADDITIONS (extend Section 7.2 checklist)

- **29.** Slot holds a Part-1 kind-1 dimensional standard, `(NON STANDARD)`, or
  `(AS PER DRAWING)` — never a flange, material, or test standard.
- **30.** Size + class verified inside range; out-of-range ⇒ non-standard route, no invented ring.
- **31.** BX ⇒ API 6A · RX ⇒ API 6B + NACE line · SPW ⇒ never API · 26"+ ⇒ B16.47.
- **32.** Every engine-vs-customer standard difference carries exactly one deviation note;
  unlisted standards carry the catch-all TECH REVIEW flag.

## REGRESSION FIXTURE (add to Section 8)

| Fixture | Tests | Must produce |
|---|---|---|
| Standards-selection set (the 9 worked examples) | Rule V: three-kinds separation, size-world switch at 26", ERP short-text override, API 601/605 successors, BX→API 6A, EN 1514 vs EN 681, ISO 27509 + 56" range gates, equipment/drawing route | The 9 outputs exactly as written, each with its deviation/alert; zero flange or material standards in slots; zero invented rings |
