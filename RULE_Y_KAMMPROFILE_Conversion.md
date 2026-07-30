# RULE Y — KAMMPROFILE CONVERSION (full-proof)
### Customer description → GGPL description · the complete KAMM decision procedure
### Built from 496 real GGPL KAMM pairs (Gasket.xlsx, incl. deviations + NON-STD flags)

> KAMM is GGPL's most geometrically varied family: round, oval, crowned (convex), ribbed and
> crossbarred, quoted in three size worlds, with seven distinct house output forms. This rule
> fixes detection, the thickness engine, ring logic, geometry variants, the standard slot, and
> the deviation register — and lists the drift in the historical set that must not be repeated.

---

## PART 1 — DETECT (ISK and RTJ excepted, KAMM wins over SPW)

Spellings and synonyms observed: `KAMMPROFILE` · `KAMPROFILE` · `KAMM PROFILE` ·
`CAMPROFILE` · `CAM PROFILE` · `CAMP` · `KMP` · `KAMM` · `GROOVED METAL` ·
`GROOVED METAL GASKET` · `GRVD` · `MET GRVD` · `SERRATED METAL` · **`PROFILE GASKET`** ·
`GASKET, METAL GROOVED` · brands `FLEXPRO · KAMMPRO · MAXIPROFILE · LEADER-KAM · METAKAMM ·
A-TYPE / B-TYPE / K-TYPE FLEXITALLIC`.

**Hard traps:**
- `PROFILE GASKET` is ALWAYS KAMM — even with an FKM/rubber facing.
- `GROOVED METAL` + `covering layers` is KAMM, never SPW. (Two historical rows converted
  a *Camprofile* enquiry into a SPIRAL WOUND quote — see Part 11.)
- `MET GRVD` / `GRVD` in a short text = grooved metal = KAMM.
- A KAMM enquiry may carry the word *filler* — that is the covering layer, not a winding.

---

## PART 2 — INPUT GRAMMARS (all observed; parse before extraction)

```
1216 1184 16 SS 347 KAMM PROFILE
   -> three bare numbers = OD 1216 / ID 1184 / SEAL WIDTH 16   [(OD-ID)/2 = 16 confirms]
(3.2 CORE + 0.5 FACING) THK x 1506 ID x 1532 ODGROOVED METAL GRAPHITE
   -> core 3.2 + facing 0.5/side -> TOTAL 4.2 ; ID 1506 ; OD 1532 ; glued at "OD|GROOVED"
4 THK X 1980 OD X 1950 ID WITH RIB AS PER DRG        -> THK/OD/ID + rib + drawing
THK4XID639XOD705 TYPE: CONVEX                         -> label-prefixed, X-separated, no spaces
30900#Grooved metal gaskets AISI SS-316 core with 0.5 mm Graphite/PTFE covering layers
   -> glued size+class: 30" 900#  (also 24600# -> 24" 600#)
GKT 100NB KMP 4.5MM SS317L GPH B16.20                 -> shorthand: NB size, KMP, thk, mat, filler
GSKT CAMP CL600 RF 1-1/2IN GRAPHITE 316L              -> abbreviation soup, class before size
GSKT CH CVR W/RIB 1849X1881MM 03/-09                  -> channel cover, W/RIB, ID x OD pair
GASKET/GASKET/SIZE:OD-1890MM X ID-1864MM X 4MM THK./MAT:CAMPROFILE ALLOY 825 ...///STANDARD
   -> slash-delimited ERP export; ignore empty slash fields
12", 150#, 3 mm thk, SURFACE FINISH BETWEEN RA 3.2 & 6.3 UM   -> RA finish -> side-field
4.5T SOFT IRON GASKET WITH 0.5mm GRAPHITE LAYERS (M=3, Y=31 mpa)
   -> 4.5T = 4.5MM total ; M/Y are gasket factors -> side-field
1801MM OD X 1745MM ID ... WITH 6 CROSSBAR 10MM THK AS PER DWG ... POS. 9 (K-TYPE FLEXITALLIC)
   -> crossbars (pass partitions) + drawing + position + brand style letter
```
Rules: `{n}T` = total thickness in MM · a third bare number after OD/ID is the **seal width**
(verify `(OD−ID)/2`) · `CORE + FACING` in brackets means **total = core + 2 × facing** ·
`W/RIB` = with rib · `POS.`/`PART NO.` = drawing position, always carried.

---

## PART 3 — THE SEVEN OUTPUT FAMILIES + SELECTION LAW

| # | Family | Used when | Shape |
|---|---|---|---|
| **Y1** | **W3 round (dominant)** | OD/ID given in MM | `SIZE : OD {n}MM X ID {n}MM X {t}MM THK ({c}MM CORE THK) KAMMPROFILE {MAT} {LAYER} LAYER ON BOTH SIDES [+ INTEGRAL OUTER RING] [( AS PER DRAWING {ref} )]` |
| **Y2** | **W1 flange, integral ring** | size + class given | `SIZE : {n}" X {ppp}# X {t}MM THK, KAMMPROFILE {MAT} GROOVED METAL GASKET WITH {LAYER} COVERING LAYER ON BOTH SIDES, INTEGRAL OUTER RING, {standard}` |
| **Y3** | **W1 flange, IR + OR named** | customer names inner and centering rings | `SIZE: {n}" X {ppp}# X {t}MM THK,{MAT} KAMMPROFILE GASKET WITH {LAYER} LAYERS ON BOTH SIDES + {IR} INNER RING & {OR} OUTER RING,{standard}` |
| **Y4** | **Shorthand code form** | customer sent a coded short text (`GKT 100NB KMP 4.5MM SS317L GPH`) | `KAMPROFILE (RF) {mat}/{FG\|PTFE\|EPTFE}[+{mat}-OR] {t}MM[,{ring t}MM] {standard}` |
| **Y5** | **Overall-thickness form** | thickness known only as an overall figure; no size/class resolvable | `{MAT} KAMPROFILE GASKET WITH {LAYER} LAYER ON BOTH SIDE [+ {MAT} OUTER RING (LOOSE FIT)] , (OVERALL {t}MM THK)` |
| **Y6** | **MAJOR OD form (crowned / convex)** | convex or crowned profile, drawing-based | `SIZE: {n}MM MAJOR OD X {n}MM MAJOR ID X {t}MM THK ({c}MM CORE THK) KAMMPROFILE {MAT} GASKET WITH {LAYER} LAYER ON BOTH SIDES , AS PER DRAWING {ref} , PART NO.{pos}` |
| **Y7** | **Oval / racetrack form** | two axis dims + a seal width | `SIZE : {A}MM X {B}MM X WIDTH {w}MM X {t}MM THK ({c}MM CORE THK) KAMMPROFILE {MAT} {LAYER} LAYERS BOTH SIDES - AS PER DRAWING` |

**Selection law:** size + class present → Y2 (integral ring) or Y3 (rings named) ·
OD/ID in MM → Y1 · convex/crowned → Y6 · two axes + width → Y7 · coded short text → Y4 ·
thickness only → Y5 · complex OEM/brand-style spec with crossbars and a drawing that is
**not attached** → echo verbatim + `KINDLY PROVIDE DRAWINGS` (Part 10).

**Canonical form for new work: Y1 for W3, Y2/Y3 for W1.** Write `KAMMPROFILE` (two M's).

---

## PART 4 — ★ THE THICKNESS ENGINE (total ↔ core)

A kammprofile is **core + one covering layer per side**: `TOTAL = CORE + 2 × LAYER`.
The GGPL string must always carry `({core}MM CORE THK)`.

| Given | Do |
|---|---|
| Core **and** layer stated (`3.2 CORE + 0.5 FACING`) | total = 3.2 + 1.0 = **4.2MM THK (3.2MM CORE THK)** |
| Total **and** core stated | print both as given |
| **Total only** | core = **total − 1.0MM** (0.5MM layer per side, GGPL standard) |
| Core only | total = core + 1.0MM |

Observed total/core pairs (count): **5/4 (50) · 4/3 (38) · 4.5/3.3 (18) · 4.5/3.5 (10) ·
4.5/3 (9) · 4.2/3.2 (4) · 3/2 (3) · 6.5/5 (2)**.

### 4.1 ★ GGPL CORE STOCK — SUBSTITUTE, DO NOT COPY BLINDLY
GGPL builds kammprofile cores from **its own stock thicknesses**. When a customer states a
core GGPL does not stock, GGPL proceeds with the nearest stock core and its resulting total —
this is house practice, **not an error**.

**Confirmed house value:** customer `(3.5 CORE + 0.5 FACING)` → GGPL
**`4.2MM THK (3.2MM CORE THK)`** — the 3.5MM core is supplied as GGPL's 3.2MM stock core,
giving a 4.2MM total.

```
Core stock observed in GGPL output: 2 · 3 · 3.2 · 3.3 · 3.5 · 4 · 5 MM
Standard facing: 0.5MM per side  ->  standard totals: 3 · 4 · 4.2 · 4.3 · 4.5 · 5 · 6 MM
```

> ★ **Note on 3.5 (clarified 2026-07-29).** 3.5 appears both as stock above and as
> the core substituted *away from* in the confirmed house value below. Both hold,
> because they are different pathways and the engine keeps them separate:
> * a 3.5 core **derived** from a 4.5MM total is honoured (Part 4.2, 10 rows);
> * a 3.5 core the customer **states** alongside a facing is built as 3.2 → 4.2 total.

Procedure when a core is stated:
1. Core is a stock value → honour it; total = core + 2 × facing.
2. Core is **not** a stock value → substitute the nearest stock core, recompute the total,
   and emit the register line:
   `WE ARE PROCEEDING WITH GASKET THICKNESS AS {total}MM (CORE THICKNESS AS {core}MM) AS PER
   MANUFACTURING PRACTICE`
3. Never print a core GGPL cannot build, and never leave the substitution undocumented.

### 4.2 The 4.5MM ambiguity
Three cores appear against a 4.5MM total in house data — 3.5 (0.5 facing), 3.3 (0.6) and
3.0 (0.75). When total = 4.5MM and no core is stated, apply **3.5MM** and flag:
`LAYER THK NOT STATED — 0.5MM/SIDE APPLIED (CORE 3.5MM). CONFIRM IF 0.6 OR 0.75MM.`

Thin-core caution: a core below 3MM (e.g. 3MM total → 2MM core) is manufacturable but weak —
add `CONFIRM GROOVE DEPTH / SPACE LIMIT`.

---

## PART 5 — MATERIALS (core) AND LAYERS (facing)

**Cores observed:** SS316 · SS316L · SS316/SS316L · SS304 · SS304L · SS309 · SS310S ·
SS317L · SS321 · SS347 · SS904L · S32750 (super duplex) · UNS S31803 · ALLOY 825 /
INCOLOY 825 · UNS N06625 / INCONEL 625 · SOFT IRON · monel/titanium when named.
Normalise per the material master; grade suffixes (L, H, Ti) survive; `AISI SS-316` → SS316.

**Layers (facing) observed:** `GRAPHITE` (default) · `FLEXIBLE GRAPHITE` · `STANDARD PURITY
GRAPHITE` (keep the grade) · `GRAPHITE 98%` · `PTFE` · `EPTFE` · `MICA` (high temp).
House wording alternates `GRAPHITE LAYER ON BOTH SIDES` / `GRAPHITE LAYERS ON BOTH SIDES` /
`GRAPHITE COVERING LAYER ON BOTH SIDES` — pick one (`GRAPHITE LAYERS ON BOTH SIDES`).

**Filler fidelity applies:** a stated facing is copied exactly. `Graphite/PTFE as covering
layers` (either-or) → quote GRAPHITE + note `PTFE OPTION AVAILABLE — CONFIRM`.

---

## PART 6 — RING LOGIC (four states — never guess)

| Customer says | Output |
|---|---|
| Nothing about rings, W1 flange size given | `INTEGRAL OUTER RING` (GGPL default for flange KAMM, evidenced in the deviation register) |
| `integral` / one-piece / machined-in | `+ INTEGRAL OUTER RING` |
| `centering ring` / `outer ring` with a material | `+ {mat} OUTER RING` (or `{mat} OUTER RING (LOOSE FIT)`) |
| Inner **and** centering ring named | `+ {IR} INNER RING & {OR} OUTER RING` (both-rings law) |
| Full construction enumerated with no ring | **no ring** (exhaustive-list rule) |
| Exchanger/equipment gasket sitting in a groove (W3, no class) | no ring unless stated |

Ring thickness, when quoted separately in Y4, follows the total: `4.5MM,1.5 MM`.

---

## PART 7 — GEOMETRY VARIANTS

| Variant | Trigger | Handling |
|---|---|---|
| **Round** | OD/ID | Y1 |
| **Oval / racetrack** | two axis dims + width | Y7, drawing required |
| **Convex / crowned** | `CONVEX`, `CROWNED`, `TYPE: CONVEX` | Y6 with `MAJOR OD` / `MAJOR ID`; retain `CONVEX`; flag tooling check |
| **With rib** | `WITH RIB` / `W/RIB` | append `, WITH RIB`; if not stated on an exchanger item → `KINDLY CONFIRM RIB DETAILS` |
| **Crossbar / pass partition** | `CROSSBAR`, `{n} CROSSBAR 10MM THK`, `PASS PARTITION` | carry count and thickness verbatim; drawing mandatory |
| **Channel cover** | `CH CVR`, `CHANNEL COVER` | equipment gasket → W3 + drawing |
| **Obround / manway** | two axes, obround | Y7 shape wording + drawing |

Never invent a rib, crossbar count, or crown geometry — these come from the drawing or a
confirmation.

---

## PART 8 — STANDARD SLOT (KAMM-specific — note the Series difference)

| Case | Slot |
|---|---|
| W1, NPS ≤ 24 | `ASME B16.20` |
| **W1, NPS ≥ 26** | **`ASME B16.47 (SERIES B)`** — ★ house practice for KAMM (SPW and SC default to SERIES A). Confirmed by the register entry *"We are proceeding Filler material as Graphite, Integral Outer ring and Gasket as Series B"*. Quote SERIES A only if the customer states it. |
| W3 dims, no class | no standard slot; `(NON STANDARD)` or `( AS PER DRAWING {ref} )` |
| Drawing cited | `( AS PER DRAWING {ref} )` + `PART NO./POS.` when given |
| DN/PN work | `EN 1514-6` if the customer works in EN; otherwise B16.20 house style |
| `MNF STD` / vendor standard | no slot; retain the phrase |

Mark the row `NON-STD` in the tracking column whenever dims are the spec (the source set
flags 144 of 496 rows this way).

---

## PART 9 — DEVIATION REGISTER (KAMM entries, use verbatim)
```
KINDLY PROVIDE DRAWINGS
KINDLY PROVIDE WINDING MATERIAL & CLEAR SPECIFICATION
WE ARE PROCEEDING MATERIAL AS "SS316 KAMMPROFILE GASKET WITH GRAPHITE LAYER ON BOTH SIDES
AND GASKET THICKNESS AS 4MM (CORE THICKNESS AS 3MM)"
We are proceeding Filler material as "Graphite", Integral Outer ring and Gasket as "Series B"
LAYER THK NOT STATED — 0.5MM/SIDE APPLIED (CORE {c}MM). CONFIRM IF 0.6 OR 0.75MM.
WE ARE PROCEEDING WITH GASKET THICKNESS AS {t}MM (CORE THICKNESS AS {c}MM) AS PER MANUFACTURING PRACTICE
CONVEX / CROWNED PROFILE — CONFIRM CROWN GEOMETRY AGAINST DRAWING; TOOLING CHECK
KINDLY CONFIRM RIB DETAILS
```

---

## PART 10 — RETAIN · DROP · ESCALATE
**RETAIN:** `CONVEX` · `WITH RIB` · crossbar count and thickness · `INTEGRAL` / `LOOSE FIT` ·
facing grade (`STANDARD PURITY`, `98%`, `FLEXIBLE`) · drawing number + `PART NO.` / `POS.` ·
`MAJOR OD/ID` for crowned profiles · seal width when given.

**DROP to side-fields:** surface finish (`RA 3.2 & 6.3 UM`, AARH) · gasket factors
(`M=3, Y=31 MPa`) · equipment capacity (`SHELL 1.066 M3`) · exchanger tag and serials ·
OEM part numbers and brand style letters (→ deviation) · ERP empty slash fields ·
`STANDARD` / `PLANT ELEMENT` boilerplate · customer type codes not in GGPL taxonomy
(`TYPE CK`) — note them, do not print them.

**ESCALATE:**
| Situation | Output |
|---|---|
| Brand-style spec with crossbars, drawing cited but not attached | echo the customer text + `KINDLY PROVIDE DRAWINGS` |
| Core material not identifiable | `KINDLY PROVIDE WINDING MATERIAL & CLEAR SPECIFICATION` |
| Oval/obround/crowned with no drawing and no full geometry | `KINDLY PROVIDE DRAWING WITH DIMENSION` |
| Drawing cited **and dims complete** | quote + `( AS PER DRAWING )` + verify alert (never "provide drawing") |
| Drawing attached, dims unread | Rule K-2 DIM-FILL worksheet |

---

## PART 11 — DRIFT — DO NOT REPRODUCE
*(Scope set by GGPL: the Camprofile-to-spiral-wound rows, the CNAF/Alloy-825 row and the
spelling-variant list are excluded as junk rows or accepted house usage. The 3.5-core to
3.2-core case is NOT drift — it is house practice, now Part 4.1.)*

1. **`SS304 METAL JACKETED` answered with `KAMMPROFILE SOFT IRON`** — family and material
   both changed. If a drawing governs, quote from the drawing and say so; otherwise echo the
   customer's product family.
2. **Inconsistent slot spacing** (`OD 1532MM` vs `1532MM OD`, `( 3MM CORE THK )` vs
   `(3MM CORE THK)`, `NMM THKCORE`) → use one house form per Part 3.
3. **Two identical customer lines carrying different drawing part numbers** (410 / 411) —
   correct when they are genuinely different positions, an error when duplicated. Verify.

## PART 12 — WORKED EXAMPLES (all from the shared KAMM set)
```
1) IN : (3.2 CORE + 0.5 FACING) THK x 1506 ID x 1532 OD GROOVED METAL GRAPHITE
   OUT: SIZE : OD 1532MM X ID 1506MM X 4.2MM THK (3.2MM CORE THK) KAMMPROFILE SS316
        GRAPHITE LAYERS ON BOTH SIDES (NON STANDARD)
   [total = 3.2 + 2x0.5 ; core material not stated -> SS316 default + assumption]

1b) IN : (3.5 CORE + 0.5 FACING) THK x 1282 ID x 1342 OD GROOVED METAL GRAPHITE
   OUT: SIZE : OD 1342MM X ID 1282MM X 4.2MM THK (3.2MM CORE THK) KAMMPROFILE SS316
        GRAPHITE LAYERS ON BOTH SIDES (NON STANDARD)
   DEV: WE ARE PROCEEDING WITH GASKET THICKNESS AS 4.2MM (CORE THICKNESS AS 3.2MM) AS PER
        MANUFACTURING PRACTICE          [3.5MM core supplied as GGPL 3.2MM stock core]

2) IN : 1216 1184 16 SS 347 KAMM PROFILE
   OUT: SIZE : OD 1216MM X ID 1184MM X 4MM THK (3MM CORE THK) KAMMPROFILE SS347
        GRAPHITE LAYERS ON BOTH SIDES + INTEGRAL OUTER RING (NON STANDARD)
   [third number 16 = seal width, (1216-1184)/2 = 16 confirms; THK not stated -> 4/3 default]

3) IN : 30900#Grooved metal gaskets AISI SS-316 core with 0.5 mm Graphite/PTFE covering layers
   OUT: SIZE : 30" X 900# X 4.5MM THK, KAMMPROFILE SS316 GROOVED METAL GASKET WITH GRAPHITE
        COVERING LAYERS ON BOTH SIDES, INTEGRAL OUTER RING, ASME B16.47 (SERIES B)
   DEV: PTFE OPTION AVAILABLE — CONFIRM · LAYER 0.5MM/SIDE -> CORE 3.5MM

4) IN : 24GASKET RF 600#, ASME B16.20 Gasket Camprofile, SS 316/SS 316L GPH, INR SS 316/316L
        CS centering ring
   OUT: SIZE: 24" X 600# X 4.5MM THK,SS316/SS316L KAMMPROFILE GASKET WITH GRAPHITE LAYERS ON
        BOTH SIDES + SS316/SS316L INNER RING & CS OUTER RING,ASME B16.20
   [KAMM, not SPW — see Part 11.1]

5) IN : GKT 100NB KMP 4.5MM SS317L GPH B16.20
   OUT: KAMPROFILE (RF) 317L/FG+317L-OR 4.5MM,1.5 MM ASME B16.20                        [Y4]

6) IN : 4 THK X 1980 OD X 1950 ID WITH RIB AS PER DRG
   OUT: SIZE : OD 1980MM X ID 1950MM X 4MM THK (3MM CORE THK) KAMMPROFILE CONVEX GROOVED
        SS316 METAL GASKET WITH GRAPHITE LAYERS ON BOTH SIDES, WITH RIB ( AS PER DRAWING 410 )

7) IN : Kammprofile SS 904L with flexible graphite layer, 4.5mm thk  [oval, per drawing]
   OUT: SIZE : 2796MM X 753MM X WIDTH 13MM X 4.5MM THK (3.5MM CORE THK) KAMMPROFILE SS904L
        FLEXIBLE GRAPHITE LAYERS BOTH SIDES - AS PER DRAWING                            [Y7]

8) IN : 4.5T SOFT IRON GASKET WITH 0.5mm GRAPHITE LAYERS ON BOTH SIDES (KAMPROFILE)
        (M=3, Y=31 mpa) [drawing SK-8293 part 504]
   OUT: SIZE: 510MM MAJOR OD X 450MM MAJOR ID X 4.5MM THK (3.5MM CORE THK) KAMMPROFILE
        SOFT IRON GASKET WITH GRAPHITE LAYERS ON BOTH SIDES , AS PER DRAWING SK-8293 ,
        PART NO.504                                                                     [Y6]
   SIDE: M=3, Y=31 MPa (gasket factors)

9) IN : GASKET/GASKET/SIZE:OD-1890MM X ID-1864MM X 4MM THK./MAT:CAMPROFILE ALLOY 825 WITH
        GRAPHITE LAYERS///STANDARD
   OUT: SIZE : OD 1890MM X ID 1864MM X 4MM THK (3MM CORE THK) KAMMPROFILE ALLOY 825
        GRAPHITE LAYERS ON BOTH SIDES (NON STANDARD)

10) IN : 12", 150#, 3 mm thk, SURFACE FINISH BETWEEN RA 3.2 & 6.3 UM  [S32750, PTFE layers]
    OUT: SIZE : 12" X 150# X 3MM THK (2MM CORE THK) KAMMPROFILE S32750 PTFE LAYERS ON BOTH
         SIDES WITH INTEGRAL OUTER RING, ASME B16.20
    SIDE: SURFACE FINISH RA 3.2-6.3 UM · FLAG: 2MM CORE — CONFIRM GROOVE DEPTH

11) IN : GASKET, KAMMPROFILE, STYLE PN, MATL 316SS 4MM THK PLUS 0.5MM GRAPHITE LAYER ON BOTH
         SIDES, TOTAL THICKNESS 5MM, 1801MM OD X 1745MM ID, WITH 6 CROSSBAR 10MM THK AS PER
         DWG GOO-GA-25-04 POS. 9 (PART Nº: K-TYPE FLEXITALLIC)
    OUT: [echo the customer specification verbatim]
    DEV: KINDLY PROVIDE DRAWINGS   ·   NS
    [crossbar layout is drawing-governed; brand style letter -> deviation]

12) IN : GASKET,MET GRVD,316L,GPH,558x582x3mm · Type CK · layers STANDARD PURITY GRAPHITE ·
         grooved profile SS316L · thickness total 3mm · grooved ring i.d. x o.d. 558 x 582 ·
         EXCHANGER E1203 · Brand METAKAMM
    OUT: SIZE : OD 582MM X ID 558MM X 3MM THK (2MM CORE THK) KAMMPROFILE SS316L STANDARD
         PURITY GRAPHITE LAYERS ON BOTH SIDES (NON STANDARD)
    DEV: GGPL MAKE, EQUIVALENT TO METAKAMM · 2MM CORE — CONFIRM GROOVE DEPTH ·
         TYPE CK IS A CUSTOMER CODE — CONFIRM MEANING · CONFIRM NO PASS PARTITION
```

---

## PART 13 — VALIDATION (KAMM rows of the Section 7.2 checklist)
1. Classified KAMM, not SPW — `GROOVED METAL` / `PROFILE GASKET` / `CAMP` / `KMP` never route to spiral wound.
2. Output carries `({core}MM CORE THK)`; `TOTAL = CORE + 2 × LAYER` holds arithmetically.
3. Stated core checked against GGPL stock (2/3/3.2/3.3/3.5/4/5MM); a non-stock core is
   substituted to the nearest stock value **with the register line**, never copied or dropped.
3a. Total 4.5MM without a stated core ⇒ 3.5MM core **and** the layer-thickness flag.
4. Core < 3MM ⇒ groove-depth confirmation flag.
5. Ring state explicit: integral / loose / IR+OR / none — never guessed; W1 default is INTEGRAL OUTER RING.
6. Facing grade copied exactly (STANDARD PURITY / 98% / FLEXIBLE / PTFE / EPTFE).
7. W3 strings: OD before ID, OD > ID. W1 strings: size + class + standard.
8. NPS ≥ 26 ⇒ `ASME B16.47 (SERIES B)` unless the customer states Series A.
9. Convex ⇒ `MAJOR OD/ID` wording + crown confirmation; rib/crossbar carried or flagged.
10. Drawing cited ⇒ `( AS PER DRAWING {ref} )` with `PART NO./POS.`; dims missing ⇒ DIM-FILL.
11. Canonical spellings: KAMMPROFILE · GROOVED · OUTER RING · LOOSE FIT · INTEGRAL · THICKNESS.
12. Side-fields clean of RA finish, M/Y factors, capacities, tags, OEM part numbers.
13. `NON-STD` tracking flag set whenever dims are the spec.

## REGRESSION FIXTURE (Section 8)
| Fixture | Tests | Must produce |
|---|---|---|
| GGPL KAMM set (12 worked examples, 496 pairs) | Rule Y: seven-family selection, thickness engine incl. the 4.5MM ambiguity, three-bare-number and CORE+FACING grammars, glued size+class, ring-state logic, convex MAJOR OD, oval width form, crossbar echo + drawing escalation, SERIES B for ≥26", METAKAMM/Flexitallic brand deviations, Part 11 drift corrections | The 12 outputs and their deviations exactly as written; every line carries a core thickness; zero KAMM→SPW misroutes; zero `GROOOVED`/`KAMPROFILE`/`LOSSE` spellings |

Implemented in `tests/test_rule_x2_y_z.py` (Rule Y section).
