# RULE Z — SPW CONVERSION, MAPPED TO THE GGPL CAPTURE TABLE
### Spiral Wound · customer description → 46-column capture row → GGPL description
### Built from 21,814 real GGPL SPW pairs (Gasket.xlsx: Description / GGPL / Deviations / make / NON-STANDARD)

> Written to fill **your existing columns** — no new blocks. One field must be added:
> **`Deviation`** (customer-facing). Your source file carries it and the register is heavily
> used (the single phrase *"We are proceeding Winding & Inner ring material as SS316 and Outer
> ring material as CS"* appears 467 times). `Notes / Flags` is internal and cannot do both jobs.

---

## PART 1 — DETECT → `Type` = SPW
`SPIRAL WOUND` · `SPIRALLY WOUND` · `SPIRAL WOUNDED` · `SPIRAL` · `SPW` · `SWG` · `S P W D` ·
`SW` · `WINDING` · `CENTERING RING` · `CGI / CG / RWI / RW / WRI / WR / 913 / 913M` (brand
style codes) · `SPV2F` and similar ERP type codes.
Never SPW when the text says GROOVED METAL / CAMPROFILE / KAMMPROFILE / PROFILE GASKET.

---

## PART 2 — COLUMN FILL MAP (who fills what)

**AI fills only what the text states. CODE fills everything derivable.** That split is what
removes hallucination from ring numbers, standards and thicknesses.

| Column | Source | SPW content |
|---|---|---|
| `Status` | **CODE** | QUOTE · WILL QUOTE SOON · OUT OF SCOPE · REGRET (Part 8) |
| `#` | CODE | bot line number |
| `Cust Sl.No` | AI | verbatim; gaps and repeats are normal |
| `Customer Item Code` | AI | material / part code |
| `Customer Description` | AI | raw text as received |
| `GGPL Description` | **CODE** | assembled per Part 3 — never written by the model |
| `Type` | AI | `SPW` |
| `Size` | AI | size **as stated** (`2"`, `DN50`, `50 NB`, `1/2`, `2 IN`) |
| `Size (in)` | CODE | normalised inches: `2`, `1-1/2`, `1/2`, `3/4`. **Blank for W2 / W3 lines.** |
| `OD (mm)` | AI | non-standard only — **winding (element) OD** |
| `ID (mm)` | AI | non-standard only — **winding (element) ID** |
| `Rating` | AI | `150#` · `300#` · `PN16` · `150/300#` when dual-stated |
| `Standard` | **CODE** | Part 5 |
| `MOC` | AI | material exactly as the customer wrote it (`AISI 316`, `SS-321`, `Alloy 825`) |
| `Face` | AI | RF / FF / RTJ-groove note |
| `Series` | CODE | A / B — only when NPS ≥ 26 (Part 5) |
| `Thk (mm)` | CODE | Part 4 — default `4.5` |
| `Ring No` `Groove` `BHN` | — | **blank for SPW** (RTJ fields) |
| `SW Winding` | AI→CODE | normalised: SS316 · SS316L · SS304 · SS304L · SS321 · SS316/SS316L · ALLOY 825 · ALLOY 20 · 6MO · UNS S31803 · TITANIUM GRADE 2 |
| `SW Filler` | AI→CODE | copied exactly when stated; `GRAPHITE FILLER` only on silence |
| `SW Inner Ring` | AI→CODE | material, or blank; mandate may force it (Part 4) |
| `SW Outer Ring` | AI→CODE | material; `CS` on silence; `WITHOUT` when explicitly none |
| ISK / KAMM / DJI blocks | — | **blank for SPW** |
| `Qty` | AI | as stated; missing → Part 8 |
| `UoM` | AI | NOS / EA / SET |
| `Special` | CODE | TRUE for low-stress, non-standard, drawing-based, or exotic-alloy work |
| `Regret` | CODE | TRUE only when `Status` = REGRET |
| `AI` | CODE | model / bot version |
| `Notes / Flags` | CODE | internal: assumptions, confirmations, overall-vs-element dims, ring thickness |
| **`Deviation`** ← ADD | CODE | **customer-facing** register text (Part 7) |

---

## PART 3 — ASSEMBLY TEMPLATE (code builds this from the columns)

### 3.1 Standard, inch/class (the dominant form — 90 %+ of the set)
```
SIZE: {Size (in)}" X {Rating} X {Thk}MM THK, {SW Winding} SPIRAL WOUND GASKET WITH
{SW Filler} + {SW Inner Ring} INNER RING & {SW Outer Ring} OUTER RING, {Standard}
```
`SIZE: 2" X 300# X 4.5MM THK, SS316 SPIRAL WOUND GASKET WITH GRAPHITE FILLER + SS316 INNER RING & CS OUTER RING, ASME B16.20`

### 3.2 Metric (NB / DN)
```
SIZE: {Size} NB X {Rating} X {Thk}MM THK, {winding} SPIRAL WOUND GASKET WITH {filler} + {IR} INNER RING & {OR} OUTER RING, {Standard}
```
No inch mark on NB/DN, ever.

### 3.3 Non-standard — OD before ID
> ★ **SUPERSEDED 2026-07-29.** This section originally specified ID-before-OD for
> SPW, contradicting **Rule V §116** and **Rule J-2 §92**, which both specify
> OD-first and are what the engine implements. GGPL's ruling: **OD-first stands
> for every family**; Rule Z is amended to match. The ID-first strings in the
> historical set (3 of 11 non-standard SPW rows in `ground_truth.csv`) are legacy
> drift, not a family convention.

```
SIZE : OD {OD}MM X ID {ID}MM X {Thk}MM THK, {winding} SPIRAL WOUND GASKET WITH {filler} + {IR} INNER RING & {OR} OUTER RING
```
`SIZE : OD 404MM X ID 330MM X 4.5MM THK, SS321 SPIRAL WOUND GASKET WITH GRAPHITE FILLER + SS321 INNER RING & CS OUTER RING`
(Same order as KAMM Y1 — the two families are deliberately unified here.)

### 3.4 Ring variants
- No inner ring: `… WITH {filler} + {OR} OUTER RING, {Standard}`
- Winding only: `… WITH {filler} FILLER (WINDING ONLY)`
- Explicitly no outer ring: `… + {IR} INNER RING & WITHOUT OUTER RING`

**House spacing:** `SIZE:` + one space, `{n}MM THK,` closed up, ` + `, ` & `, and a comma
before the standard. (The set contains `SIZE :`, `N MM THK ,` and `,ASME` variants — pick
one form and hold it.)

---

## PART 4 — `Thk (mm)`, RINGS AND THE MANDATE

**Thickness** — 4.5 MM in 20,828 of 21,814 rows.
| Customer states | `Thk (mm)` |
|---|---|
| nothing | **4.5** + register line `WE ARE PROCEEDING STANDARD THICKNESS AS "4.5MM"` |
| 4.5 / 0.175" / 4.45 | 4.5 |
| 3.2 / 0.125" **next to a ring** | 4.5 — that figure is the **ring** thickness → `Notes / Flags` |
| "3.2 compressed", "seated" | 4.5 — service dimension, never the quoted thickness |
| 1/4" / 6.35 | 6.35 (also seen: 3.175 = 1/8", 3, 3.5, 5, 1.5) |
| `635` | 6.35 — decimal lost in transcription |

**Rings on silence:** `SW Outer Ring` = **CS** (15,061 of 21,814) · `SW Inner Ring` =
winding material. Shorthand `I & O RING-SS304` → both SS304. `CS centering ring` → OR = CS.
`Zinc plated CS` → keep as `ZINC PLATED-CARBON STEEL` when stated.

**Inner-ring mandate (B16.20) — CODE adds it even if the customer omitted it:**
CL900 NPS ≥ 24 · CL1500 NPS ≥ 12 · CL2500 NPS ≥ 4 · **all PTFE-filled** · flexible graphite
where buckling risk. Note the addition in `Notes / Flags`.

**Fillers seen (copy exactly — filler fidelity):** GRAPHITE FILLER · FLEXIBLE GRAPHITE FILLER ·
`FLEXIBLE GRAPHITE FILLER ( 95% MIN. )` · FLEXIBLE INHIBITED GRAPHITE FILLER ·
EXFOLIATED EXPANDED GRAPHITE FILLER · GRAPHITE TAPE · PTFE FILLER · CNAF FILLER ·
NON-ASBESTOS FILLER · MICA FILLER · `THERMICULITE 835/EQUIVALENT FILLER`.
Graphite is the **silence default only**.

---

## PART 5 — `Standard` AND `Series` (code-filled)
| Case | `Standard` | `Series` |
|---|---|---|
| NPS ≤ 24 | `ASME B16.20` | blank |
| NPS ≥ 26 | `ASME B16.47 (SERIES A)` or `(SERIES B)` **as stated by the customer**; if unstated, apply the house default and emit `WE ARE PROCEEDING AS " SERIES-A"` (or `"SERIES-B"`) | A / B |
| Low seating stress specified | `ASME B16.20 (LOW STRESS)` | blank |
| Mo-content spec quoted | `ASME B16.20 ( 2 %MO TO 2.5% MOLLY CONTENT )` | blank |
| Non-standard dims | leave blank; `Special` = TRUE, NON-STD noted | — |
| DN/PN European project | `EN 1514` when the customer cites EN, else B16.20 house style | — |
| API 601 / 605 cited | successor: `ASME B16.20` / `ASME B16.47 (SERIES B)` + deviation | — |

**Never** `ASME B16.21` on an SPW line (67 such rows exist — see Part 9), and **never** API 6A/6B.

---

## PART 6 — NON-STANDARD SPW: ELEMENT vs OVERALL DIMS
Customers supply four diameters. GGPL quotes the **sealing element**:
```
OROD 576  = outer ring OD      -> Notes / Flags
GOD  404  = gasket/winding OD  -> OD (mm)   <-- quoted
GID  330  = gasket/winding ID  -> ID (mm)   <-- quoted
IRID 310  = inner ring ID      -> Notes / Flags
```
`OD (mm)` and `ID (mm)` always hold the **winding** dims. Ring dimensions and ring thickness
(`CENTERING RING THICKNESS : 3.2 MM`) go to `Notes / Flags`.
When only two bare diameters are given with rings in the construction, ask:
`KINDLY CONFIRM — STATED OD/ID ARE SEALING ELEMENT OR OVERALL (OVER RINGS)?`

---

## PART 7 — `Deviation` REGISTER (verbatim house phrases)
```
We are proceeding Winding & Inner ring material as "SS316" and Outer ring material as "CS"
WE ARE PROCEEDING INNER RING MATERIAL AS "SS316" & OUTER RING MATERIAL AS "CS"
WE ARE PROCEEDING WINDING & INNER RING MOC: "SS316"
WE ARE PROCEEDING WINDING, INNER RING MATERIAL AS SS316, FILLER MATERIAL AS GRAPHITE AND
   OUTER RING MATERIAL AS CS
WE ARE PROCEEDING INNER & OUTER RING MATERIAL AS "SS304"
WE ARE PROCEEDING INNER RING & OUTER RING AS "UNS N06625"
WE ARE PROCEEDING OUTER RING AS "CS"
We are proceeding Outer ring material as "Zinc Plated-Carbon Steel" and filler material as "Graphite"
We are proceeding Filler material as "Mica"
We are proceeding Outer ring material as "CS" and Thermiculite Equivalent of Vermiculite
WE ARE PROCEEDING STANDARD THICKNESS AS "4.5MM"
WE ARE PROCEEDING AS " SERIES-A"   |   WE ARE PROCEEDING "SERIES-B"
We are proceeding Winding and Inner ring material as "SS316" and Pressure Rating as 150#"
```
Rule: **every default the code applies produces one register line.** Materials, filler,
thickness, series, rating — if GGPL chose it, the customer is told.

---

## PART 8 — `Status`, `Regret`, ESCALATIONS
| Situation | `Status` | Output |
|---|---|---|
| Convertible | QUOTE | the GGPL string |
| **Qty missing** | QUOTE | quote the line, `Deviation` = `KINDLY PROVIDE QUANTITY` (136 rows) |
| Winding material unidentifiable | WILL QUOTE SOON | `KINDLY PROVIDE WINDING MATERIAL & CLEAR SPECIFICATION` |
| Drawing-based, dims incomplete | DIM PENDING / WILL QUOTE SOON | DIM-FILL worksheet |
| Not supplied by GGPL | REGRET | `REGRET`, `Regret` = TRUE (9 rows) |
| Spec unusable | WILL QUOTE SOON | `KINDLY PROVIDE CLEAR SPEC` |

---

## PART 9 — QC FLAGS FOUND IN YOUR OWN SET (your `make` column already flags 38)
1. ★ **`DN` + a fraction is INCHES, not DN.** `GASKET SPIRALDN1/2;CL150RF;TYPE SPV2F316L/GRAPH`
   was quoted `SIZE: 1/2 DN X 150#…`. **DN has no fractional sizes** — DN1/2 is the ERP's `DN`
   prefix on a 1/2" size. Correct: `SIZE: 1/2" X 150# X 4.5MM THK, …`.
   Test: a fractional or decimal-inch value after DN/NB ⇒ inches; only whole metric values
   from the DN series are true DN.
2. **`SPIRAL WOUND GASKET` dropped** from those same rows (`SS316L WITH GRAPHITE FILLER…`) —
   the product phrase is mandatory in every SPW string.
3. **`ASME B16.21` in the standard slot** (67 rows) → `ASME B16.20`.
4. **`ASME B16.20 (SERIES B)`** (81 rows) — Series belongs to B16.47, not B16.20 →
   `ASME B16.47 (SERIES B)`.
5. **`635` for 6.35 MM** and **`TITATNIUM`** → 6.35, TITANIUM GRADE 2.
6. Inconsistent spacing (`SIZE :`, `N MM THK ,`, `,ASME`) → one house form.
7. `ALLOY 825 … + CS INNER RING & ALLOY 825 OUTER RING` — an exotic outer with a CS **inner**
   is unusual (the inner ring is the wetted part). Verify the ring order on those rows.

---

## PART 10 — WORKED EXAMPLES (full column fills)
```
A) IN : "NPS 4, Gasket, Spiral wound, SS316 with flexible graphite filler, SS 316 inner &
        outer ring, Cl.150 as per ASME B16.20 for B16.5 flanges, NACE, Lethal"
   Type SPW | Size 4" | Size (in) 4 | Rating 150# | MOC SS316 | Face RF | Thk 4.5
   SW Winding SS316 | SW Filler FLEXIBLE GRAPHITE FILLER | SW IR SS316 | SW OR SS316
   Standard ASME B16.20 | Status QUOTE | Special FALSE
   GGPL: SIZE: 4" X 150# X 4.5MM THK, SS316 SPIRAL WOUND GASKET WITH FLEXIBLE GRAPHITE
         FILLER + SS316 INNER RING & SS316 OUTER RING, ASME B16.20
   Notes: NACE/Lethal are service notes — not in the string

B) IN : "1/2",150#,GASKET SPIRAL WOUND SS316+ GRAPHITE FILLED ASME B16.20 / ANSI B16.5"
   Size 1/2" | Size (in) 1/2 | Rating 150# | Thk 4.5 | Winding SS316 | Filler GRAPHITE FILLER
   IR SS316 | OR CS | Standard ASME B16.20 | Status QUOTE
   GGPL: SIZE: 1/2" X 150# X 4.5MM THK, SS316 SPIRAL WOUND GASKET WITH GRAPHITE FILLER +
         SS316 INNER RING & CS OUTER RING, ASME B16.20
   Deviation: We are proceeding Winding & Inner ring material as "SS316" and Outer ring
              material as "CS"

C) IN : "GASKET SPIRALDN1/2;CL150RF;TYPE SPV2F316L/GRAPH.ASME B16.20"
   Size DN1/2 (as stated) | Size (in) 1/2 | Rating 150# | Face RF | Winding SS316L
   Filler GRAPHITE FILLER | IR SS316L | OR CS | Thk 4.5 | Standard ASME B16.20
   GGPL: SIZE: 1/2" X 150# X 4.5MM THK, SS316L SPIRAL WOUND GASKET WITH GRAPHITE FILLER +
         SS316L INNER RING & CS OUTER RING, ASME B16.20
   Notes: "DN1/2" IS AN ERP PREFIX ON AN INCH SIZE — DN HAS NO FRACTIONAL SIZES (Part 9.1)

D) IN : "GASKET, SPIRAL WOUND; (FOR 14" ASME APP.2 RF FLANGE); OROD: 576 x GOD: 404 x
        GID: 330 x IRID: 310 x 4.50 THK; INNER RING SS-321; WINDING SS-321; CS CENTERING RING"
   Size — | Size (in) blank | OD (mm) 404 | ID (mm) 330 | Thk 4.5 | Winding SS321
   Filler GRAPHITE FILLER | IR SS321 | OR CS | Standard blank | Special TRUE | Status QUOTE
   GGPL: SIZE : OD 404MM X ID 330MM X 4.5MM THK, SS321 SPIRAL WOUND GASKET WITH GRAPHITE
         FILLER + SS321 INNER RING & CS OUTER RING          [OD-first per amended 3.3]
   Notes: NON-STD · OROD 576 / IRID 310 (overall dims) · APP.2 (B16.47 App.2) 14" flange

E) IN : "GASKET SPIRAL WOUND W/SS CENTERING RING & SS INNER RING 2" 3.2 MM THICK SS316L +
        THERMICULITE FILLER NACE CL 300 ASME B16.20"
   Size 2" | Rating 300# | Thk 4.5 | Winding SS316L | Filler THERMICULITE 835/EQUIVALENT
   FILLER | IR SS316L | OR SS316L | Standard ASME B16.20 | Status QUOTE
   GGPL: SIZE: 2" X 300# X 4.5MM THK, SS316L SPIRAL WOUND GASKET WITH THERMICULITE 835/
         EQUIVALENT FILLER + SS316L INNER RING & SS316L OUTER RING, ASME B16.20
   Deviation: We are proceeding Outer ring material as "CS" and Thermiculite Equivalent of
              Vermiculite   [only if OR is substituted]
   Notes: 3.2MM = ring thickness, gasket 4.5MM

F) IN : "NPS 30, SPW SS316 / flexible graphite, SS316 IR & OR, Cl.150, B16.5 flanges"
   Size 30" | Size (in) 30 | Rating 150# | Series A | Standard ASME B16.47 (SERIES A)
   GGPL: SIZE: 30" X 150# X 4.5MM THK, SS316 SPIRAL WOUND GASKET WITH FLEXIBLE GRAPHITE
         FILLER + SS316 INNER RING & SS316 OUTER RING, ASME B16.47 (SERIES A)
   Deviation: WE ARE PROCEEDING AS " SERIES-A"
```

---

## PART 11 — VALIDATION (SPW rows of the checklist)
1. `Type` = SPW; the string contains `SPIRAL WOUND GASKET` (Part 9.2).
2. `Standard` is never B16.21 and never API; Series only appears with B16.47.
3. `Thk (mm)` present; a compressed or ring figure never became the thickness.
4. `SW Filler` = the customer's filler exactly; graphite only on silence.
5. Both rings present when both stated; the B16.20 mandate applied and noted.
6. `Size (in)` blank for W2/W3 lines; NB/DN carries no inch mark; a fraction after DN is inches.
7. NPS ≥ 26 ⇒ B16.47 with Series set (stated or defaulted + register line).
8. Non-standard strings written **OD before ID** (amended 3.3); `OD/ID (mm)` hold the **winding** dims.
9. Every applied default has a matching `Deviation` line.
10. RTJ / ISK / KAMM / DJI columns blank; `Status` set on every row; `Regret` only with REGRET.

## REGRESSION FIXTURE
| Fixture | Tests | Must produce |
|---|---|---|
| GGPL SPW set (6 worked examples, 21,814 pairs) | Rule Z: column fill map, 4.5MM default + register, CS outer default, mandate additions, filler fidelity incl. Thermiculite/Mica/exfoliated, LOW STRESS and Mo-content standard variants, Series A for ≥26", non-standard OD-before-ID form, element-vs-overall dims, DN+fraction correction, qty-missing handling | The 6 outputs and their deviations exactly as written; zero B16.21 slots; zero missing `SPIRAL WOUND GASKET` phrases; zero `{n} DN` on fractional sizes |

Implemented in `tests/test_rule_x2_y_z.py` (Rule Z section).
