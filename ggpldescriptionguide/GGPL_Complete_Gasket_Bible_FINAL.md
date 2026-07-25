# ═══════════════════════════════════════════════════════════════════
# GGPL COMPLETE GASKET CONVERSION BIBLE — FINAL CONSOLIDATED EDITION
# Customer Description → GGPL Quote Description | ALL PRODUCTS, ALL VARIETIES
# ═══════════════════════════════════════════════════════════════════
# Built from: 35,000+ GGPL historical conversion pairs (Export + Domestic),
# GGPL Material Master, GGPL ASME reference sheet, ISK/KAMM/DJI/SPW masters,
# UNIQUE REQUIREMENT rules, FEEDBACK corrections, verified against
# ASME B16.20-2017, B16.21-2021, B16.47, API 6A/ISO 10423, DIN 2696, EN 1514.
# This is the SINGLE SOURCE OF TRUTH for the GGPL Enquiry Bot.
# ═══════════════════════════════════════════════════════════════════

# SECTION 1 — UNIVERSAL RULES (APPLY TO EVERYTHING)

## 1.1 THE THREE SIZE WORLDS — detect FIRST, before anything else

| World | Signals | Output size format | Standards family |
|---|---|---|---|
| **W1 ASME inch/class** | NPS, ", inch, #, LB, CL, Class 150–2500 | `{x}" X {ppp}#` | ASME B16.21/B16.20/B16.47/API 6A |
| **W2 Metric DN/PN** | DN, NB, PN, EN/DIN/ISO/BS10 refs | `{x} DN X PN{x}` / `NB {x} X PN{x}` — **NO inch mark ever on DN/NB** | EN 1514-1/-2/-3/-6, EN 1092, ISO 4633, EN 681, BS 10 Table D/E/F |
| **W3 Non-standard dims** | OD/ID/L/W in mm, drawing refs, equipment gaskets | `{OD}MM OD X {ID}MM ID X {t}MM THK` — OD always first, OD>ID | none / (AS PER DRAWING) / (NON STANDARD) |

- PN present ⇒ size is DN even if unlabeled (`25PN16` → DN 25). Size >3 digits + PN ⇒ W2/W3, never inches.
- NEVER convert W1↔W2. Quote in customer's world. Mixed (DN450, CLASS 150) → keep both: `450 DN X 150#`.
- mm pipe-OD in W1 context → NPS map: 21.3→1/2", 26.7→3/4", 33.4→1", 42.2→1-1/4", 48.3→1-1/2", 60.3→2", 73/76.1→2-1/2", 88.9→3", 101.6→3-1/2", 114.3→4", 141.3→5", 168.3→6", 219.1→8", 273→10", 323.9→12", 355.6→14", 406.4→16", 457→18", 508→20", 610→24".

## 1.2 PRE-PARSING (most bot failures start here)
- Leading size glued to text: `16INSULATING...`→16"; `RTJ2SOFT IRON...900#`→RTJ 2" 900#; `2CL 150`→2" 150#.
- Unicode fractions: ½→1/2", ¾→3/4", ⅜→3/8". European decimals: 1,5→1.5.
- Dim strings: `101X110X1,5` → ID 101, OD 110, THK 1.5 (smaller=ID). `OD 1430 x3x ID 1404` → OD/THK/ID. `Th=4 (3+2x0,5)` → total 4, core 3, layers 0.5×2.
- Deduplicate pasted-twice text. Table fields (`Size:- 76.1 mm Rating:- 150#`) → parse label:value pairs.
- Strip to side-fields (never into GGPL string): tag/PL/cat/item codes, "for B16.5 flanges", service notes, Lethal, oil quality, QA/QC certs, O-ring bar ratings, pipe schedules, quantities.

## 1.3 CLASSIFICATION PRIORITY (first match wins)
1 ISK → 2 RTJ → 3 LENS → 4 O-RING/CORD → 5 DJI → 6 KAMM (incl. **PROFILE GASKET**) → 7 SPW (incl. MC/MCR manhole spiral) → 8 CORRUGATED METAL (CMG) → 9 MANHOLE/HANDHOLE → 10 ENVELOPE → 11 METAL CLAD → 12 SOLID METAL FLAT → 13 PLUG → 14 LIP SEAL → 15 DIAPHRAGM → 16 EYELET → 17 SHEET/ROLL → 18 SC (catch-all flats) → 19 ADJACENT/REGRET.
Unclear ⇒ `KINDLY PROVIDE CLEAR SPEC`.

## 1.4 FIDELITY LAWS (violations = severe errors)
1. **Filler fidelity** — stated filler copied exactly (CNAF/PTFE/GRAPH 98%/VERMICULITE grade/MICA). Graphite only as silence-default.
2. **Material fidelity** — normalize name, never change alloy.
3. **Both-rings law** — IR and OR both stated ⇒ both in output.
4. **Shape fidelity** — OVAL stays OVAL; RX/BX are ring TYPES not shapes.
5. **Verbatim brands** — product-identity brands (Kroll & Ziller) copied exactly.
6. **No guessed construction** — rib, fire-safety, ring number: derived or asked, never invented.

## 1.5 OUTPUT GRAMMAR
UPPERCASE. `SIZE: ` prefix. ` X ` between size elements. Comma-separated fields. `{t}MM THK`. Coatings retained (GALVANISED/ZINC/CADMIUM PLATED/ELECTROPLATED/XYLAN/PTFE/EPOXY COATED). Drawing ref ⇒ `(AS PER DRAWING)`. NACE dropped except RX template (always) or explicit demand (append `NACE MR0175`). Canonical spellings: OCTAGONAL, INCOLOY, INCONEL, HASTELLOY, GALVANISED, SILICONE, KAMMPROFILE, ASME B16.20/B16.21/B16.47 (SERIES A).

## 1.6 STANDARDS ENGINE (size+class+product decides, not customer's flange note)
| Product | ≤24" | 26–60" | W2 | API |
|---|---|---|---|---|
| SC | ASME B16.21 | ASME B16.47 (SERIES A) | EN 1514-1 / cust. | — |
| SPW | ASME B16.20 | B16.47 (SERIES A; B if stated) | B16.20 / EN 1514-2 | **NEVER API** |
| KAMM | ASME B16.20 | B16.47 (A/B as stated) | EN 1514-6 | — |
| DJI | ASME B16.20 | B16.47 | — | — |
| RTJ | ASME B16.20 | B16.47 (SERIES-A) / R93–R105 | — | API 6A (BX), API 6B (RX) |
| ISK | to suit B16.5 | to suit B16.47 (SERIES-A) | to suit EN 1092/BS EN | to suit API 6A |
| ENVELOPE | B16.21 | B16.47 (A) | EN 1514-3 | — |
| LENS | — | — | DIN 2696 | — |
Class gaps: no CL400 NPS ½–3 (use 600); no CL900 NPS ½–2½ (use 1500); no CL2500 NPS ≥14. New/foreign standards (JIS B2404, GOST, AS 2129 Table D/E, SANS 1123): keep verbatim.

# ═══════════════════════════════════════════════════════════════════
# SECTION 2 — SC (SOFT CUT) — ALL VARIETIES

**Keywords:** CNAF, non-asbestos, compressed fibre, flat ring, full face, IBC, rubber gasket, elastomer, shore, PTFE flat, graphite sheet gasket.

## Varieties & templates
| # | Variety | Template |
|---|---|---|
| SC-1 | Flat ring RF (std) | `SIZE: {x}" X {ppp}# X {t}MM THK,{MATERIAL},RF,ASME B16.21` |
| SC-2 | Full face | `...,{MATERIAL},FF,ASME B16.21` (FF flanges; CL150 typical) |
| SC-3 | IBC form | as SC-1; write `RF` (or `IBC` if customer insists) |
| SC-4 | Large ≥26" | `...,ASME B16.47 (SERIES A)` |
| SC-5 | DN/PN | `SIZE: {x} DN X PN{x} X {t}MM THK,{MATERIAL},{RF|FF},{EN 1514-1|cust std}` — NB form: `SIZE: NB {x} X PN{x}...` |
| SC-6 | Non-std ring | `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, {MATERIAL} GASKET (NON STANDARD)` |
| SC-7 | Rectangular | `SIZE: {L}MM LENGTH X {W}MM WIDTH X {t}MM THK, {MATERIAL} GASKET (NON STANDARD)` |
| SC-8 | Obround/manway | `SIZE: {A}MM X {B}MM OBROUND X {t}MM THK, {MATERIAL} (AS PER DRAWING)` |
| SC-9 | Rubber + steel insert | `{EPDM|NBR...} WITH {MS|SS304|SS316} INSERT` — insert metal unstated ⇒ verify note |
| SC-10 | Graphite + insert | `FLEXIBLE GRAPHITE REINFORCED W/SS316 SHEET INSERT` (foil/tanged as stated) |
| SC-11 | Grade-spec verbatim | `NONASBESTOS BS7531 GR X` / `GR Y` etc. kept exactly |
| SC-12 | Branded verbatim | `KROLLER & ZILLER (G-S-T-P/S) WITH SPACER ,FF ,ASME B16.21` |
| SC-13 | Shore-graded rubber | `EPDM 50 - 60 SHORE A HARDNESS` |
| SC-14 | PTFE / ePTFE flat | material = `PTFE` / `EXPANDED PTFE (ePTFE)` / `FILLED PTFE ({filler type})` |
| SC-15 | Cork/oil paper/cloth-insert | material verbatim: `CORK`, `OIL PAPER`, `RUBBER WITH CLOTH INSERT` |

**Materials:** CNAF (+binder detail if given: ARAMID FIBRE WITH NBR BINDER), COMPRESSED NON ASBESTOS SYNTHETIC FIBER, EPDM, NEOPRENE(CR), NITRILE(NBR), HNBR, SBR, BUTYL, SILICONE, VITON(FKM), CSM, NATURAL RUBBER, TPV, PTFE family, GRAPHITE family, MICA, VERMICULITE SHEET.
**Defaults:** THK 3MM; facing RF (ring) / FF (full face); std per 1.6. Honor 1.5/1.6/2/3.2MM.
**Trap:** "PROFILE GASKET" even with rubber facing = KAMM, never SC.

# ═══════════════════════════════════════════════════════════════════
# SECTION 3 — SPW (SPIRAL WOUND) — ALL VARIETIES

**Keywords:** spiral wound/wounded, SPW, SWG, winding, centering/inner/outer ring, CGI/RW/WRI-type codes.

## Construction facts (B16.20-2017)
Sealing element 4.45MM uncompressed → quote **4.5MM THK**; compressed ≈3.2MM ("3.2 compressed" still = 4.5 gasket). Rings 2.97–3.33MM. Alt thk honored: 3.2MM, 6.4MM (1/4").
**INNER RING MANDATORY:** CL900 NPS≥24; CL1500 NPS≥12; CL2500 NPS≥4; **ALL PTFE-filled**; graphite where buckling risk. Customer omits in these cases ⇒ ADD IR (winding material) + note.

## Varieties & templates
| # | Variety | Trigger | Template |
|---|---|---|---|
| SPW-1 | Standard IR+OR (CGI/RWI/WRI-type) | default ≥600#, PTFE, or both rings stated | `SIZE: {x}" X {ppp}# X {t}MM THK,{WINDING} SPIRAL WOUND GASKET WITH {FILLER} FILLER + {IR} INNER RING & {OR} OUTER RING,ASME B16.20` |
| SPW-2 | OR only (CG/RW/WR-type) | "no inner ring" / CG/RW/WR codes | `...WITH {FILLER} FILLER + {OR} OUTER RING,ASME B16.20` |
| SPW-3 | Winding only (R/SW/W-type) | T&G, M-F, grooved flanges | `...{WINDING} SPIRAL WOUND GASKET WITH {FILLER} FILLER (WINDING ONLY)` |
| SPW-4 | IR only (RIR-type) | grooves/recesses | `...WITH {FILLER} FILLER + {IR} INNER RING` |
| SPW-5 | Large ≥26" | | `...,ASME B16.47 (SERIES A)` (SERIES B if stated) |
| SPW-6 | DN/PN | | `SIZE: {x} DN X {PN{x}|{ppp}#} X {t}MM THK, ...` |
| SPW-7 | Low stress | LS/LSI/LE/WRI-LC codes or "low seating stress" | SPW-1 + `(LOW STRESS)` |
| SPW-8 | For RTJ groove | CG-RJ/WRI-RJ / "spiral for ring groove" | SPW-1/2 + `TO SUIT RTJ GROOVE (AS PER DRAWING)` |
| SPW-9 | HX / non-standard | dims/limited width/pass context | `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, {WINDING} SPIRAL WOUND GASKET WITH {FILLER} FILLER[ + rings] (NON STANDARD / AS PER DRAWING)` |
| SPW-10 | Manhole spiral MC/MCR | manhole/boiler + spiral | `SIZE: {A}MM X {B}MM {OBROUND|OVAL|ROUND}, {WINDING} SPIRAL WOUND MANHOLE GASKET (STYLE {MC|MCR}) WITH {FILLER} FILLER[ + {OR} CENTERING RING]` |
| SPW-11 | NACE-demanded | explicit NACE cert requirement | insert `NACE MR0175,` before standard |

**Windings:** SS316/316L/304/304L/321/347/317L/310, DUPLEX (S31803/S32205), SUPER DUPLEX (S32750/S32760), MONEL 400, INCONEL 625 (UNS N06625 kept if written), INCOLOY 825, HASTELLOY C276, TITANIUM, 6MO, ALLOY 20.
**Fillers:** GRAPHITE (default) / FLEXIBLE / INHIBITED / GRAPH 98%, PTFE, CNAF, VERMICULITE (THERMICULITE 715/835/845/855 grade kept), MICA-GRAPHITE, CERAMIC.
**Rings:** OR default CS; SS304 for <-45°C; "SS centering" → stated SS or winding. IR default = winding. Shorthand `I & O RING-SS304` ⇒ both SS304.
**HARD RULES:** never API standard; never swap stated filler; both rings when both stated.

# ═══════════════════════════════════════════════════════════════════
# SECTION 4 — RTJ — ALL VARIETIES

**Keywords:** ring joint, RTJ, octagonal/oval, R-/RX-/BX-, API 6A/6B/6BX, wellhead.

## Ring taxonomy
| Type | Profile | Flanges | Pressure | Standard slot |
|---|---|---|---|---|
| R OVAL | oval (fits old round-bottom + flat grooves) | B16.5/B16.47-A/API 6B | ≤2500# / ≤5000 psi | ASME B16.20 (API 6A if 6B flange) |
| R OCTAGONAL | octagonal (preferred) | flat-bottom grooves | same | same |
| RX | pressure-energized, same groove as R (joint interchangeable, section not) | API 6B | 2000–5000 psi | NACE MR-01-75 / ISO 15156, API 6B |
| BX | pressure-energized, 6BX ONLY, not interchangeable | API 6BX | 5000–20000 psi | API 6A — **NEVER B16.20** |

## Templates
- RTJ-1 std: `SIZE: R-{xx},RTJ,{OCTAGONAL|OVAL},{MATERIAL}[ {COATING}],{x} BHN HARDNESS,ASME B16.20`
- RTJ-2 API 6B by ring: `SIZE: R-{xx},RTJ,{shape},{MATERIAL},{x} BHN HARDNESS,API 6A`
- RTJ-3 RX: `SIZE: RX-{xx}, RTJ, OCTAGONAL, {MATERIAL}, {x} BHN HARDNESS, NACE MR-01-75 / ISO 15156, API 6B`
- RTJ-4 BX: `SIZE: BX-{xx},RTJ,OCTAGONAL,{MATERIAL}[ {COATING}],{x} BHN HARDNESS,API 6A`
- RTJ-5 large: `SIZE: {x}" X {x}00#, RTJ, OCTAGONAL, {MATERIAL}, {x} BHN HARDNESS, ASME B16.47 (SERIES-A)` (or R93–R105)
- RTJ-6 custom/drawing: `SIZE: {OD}MM OD X {PCD/ID}MM X {H}MM HIGH, RTJ {shape}, {MATERIAL}, {x} BHN HARDNESS (AS PER DRAWING)`

## Ring number lookup (ASME B16.20, B16.5 flanges)
| NPS | 150# | 300–600# | 900# | 1500# | 2500# |
|---|---|---|---|---|---|
| 1/2 | — | R11 | R12 | R12 | R13 |
| 3/4 | — | R13 | R14 | R14 | R16 |
| 1 | R15 | R16 | R16 | R16 | R18 |
| 1-1/4 | R17 | R18 | R18 | R18 | R21 |
| 1-1/2 | R19 | R20 | R20 | R20 | R23 |
| 2 | R22 | R23 | R24 | R24 | R26 |
| 2-1/2 | R25 | R26 | R27 | R27 | R28 |
| 3 | R29 | R31 | R31 | R35 | R32 |
| 3-1/2 | R33 | R34 | R34 | — | — |
| 4 | R36 | R37 | R37 | R39 | R38 |
| 5 | R40 | R41 | R41 | R44 | R42 |
| 6 | R43 | R45 | R45 | R46 | R47 |
| 8 | R48 | R49 | R49 | R50 | R51 |
| 10 | R52 | R53 | R53 | R54 | R55 |
| 12 | R56 | R57 | R57 | R58 | R60 |
| 14 | R59 | R61 | R62 | R63 | — |
| 16 | R64 | R65 | R66 | R67 | — |
| 18 | R68 | R69 | R70 | R71 | — |
| 20 | R72 | R73 | R74 | R75 | — |
| 22 | — | — | — | — | — |
| 24 | R76 | R77 | R78 | R79 | — |

B16.47 large: 26"=R93/R100, 28"=R94/R101, 30"=R95/R102, 32"=R96/R103, 34"=R97/R104, 36"=R98/R105 (300–600#/900#).
API: BX150≈1-13/16", BX151≈2-1/16", BX152≈2-9/16", BX153≈3-1/16", BX154≈4-1/16", BX155≈5-1/8", BX156≈7-1/16", BX157≈9", BX158≈11", BX159≈13-5/8" (10000/15000 psi). RX20≈1.5", RX23≈2", RX24≈2-9/16", RX25≈3-1/8", RX26≈4-1/16", RX27≈5-1/8", RX31≈7-1/16", RX35≈9", RX39≈11", RX41≈13-5/8" (2000–5000 psi). API 6B 2000 psi ≈ CL600 dims; 3000 ≈ 900; 5000 ≈ 1500.
"—" or unresolvable ⇒ `KINDLY PROVIDE RING NO`. ISO 27509/compact flange ⇒ `AS PER ASME STANDARD RING NUMBER IS NOT AVAILABLE SO KINDLY PROVIDE DIMENSIONS`.

## Hardness (BHN by material) — ALWAYS include `{x} BHN HARDNESS`
SOFT IRON (any plating) 90 | CS/LCS 120 | 5CR-0.5MO(F5)/2-1/4CR-1MO(F22) 130 | HASTELLOY C276 140 | SS304/316/321/347/310/INCOLOY 800H 160 | SS316L 130 soft / 160 std | SS410/F9(9CR-1MO) 170 | INCOLOY 800/SS904L 180 | INCOLOY 825 195 | INCONEL 625 210 | S32205 230 | S31803 235 | S32750/S32760 240.
**Conversions:** 83 HRBW MAX=160 BHN; 68 HRBW MAX=120 BHN; 22 HRC (duplex family)→material std BHN; customer-stated BHN used as-is.

# ═══════════════════════════════════════════════════════════════════
# SECTION 5 — KAMM (KAMMPROFILE) — ALL VARIETIES

**Keywords:** kammprofile, camprofile, kamm, grooved metal, serrated, **PROFILE GASKET (always KAMM)**, FLEXPRO/Kammpro/Maxiprofile brands, pass bar, rib.
**Construction:** serrated solid core (3–4MM) + facing layers 0.5MM/side (graphite default, PTFE opt.); total = core + 2×layer; default std-flange total 4.5MM.

| # | Variety | Template |
|---|---|---|
| K-1 | Std flange w/ rings | `SIZE: {x}" X {ppp}# X {t}MM THK,{CORE} KAMMPROFILE GASKET WITH {GRAPHITE|PTFE} FILLER + {IR} INNER RING & {OR} OUTER RING,ASME B16.20` (≥26"→B16.47 A/B) |
| K-2 | Loose centering ring only | `...FILLER + {OR} OUTER RING,...` |
| K-3 | HX non-standard | `SIZE: {OD}MM OD X {ID}MM ID X {tot}MM THK ({core}MM CORE THK), {CORE} KAMMPROFILE GASKET WITH {GRAPHITE|PTFE} LAYERS ON BOTH SIDES[ (AS PER DRAWING)]` |
| K-4 | Integral outer ring | K-3 + ` + INTEGRAL {mat} OUTER RING` |
| K-5 | With rib / pass bars | K-3/K-4 + `, WITH RIB` / `, WITHOUT RIB` / `WITH {n} PASS BAR / PARTITION RIB (AS PER DRAWING)` — unstated ⇒ note `KINDLY CONFIRM RIB DETAILS` |
| K-6 | Shaped (oval/rect/obround) | K-3 with shape word + drawing mandatory |
| K-7 | Rubber/FKM-faced profile | facing verbatim: `FLUOROCARBON RUBBER (FKM) KAMMPROFILE GASKET WITH METAL CORE` |
| K-8 | DN/PN | K-1 in DN X PN form, EN 1514-6 if demanded |

Thickness math: "3.0 core + 0.5 both sides" ⇒ `4MM THK (3MM CORE THK)`.

# ═══════════════════════════════════════════════════════════════════
# SECTION 6 — DJI (DOUBLE JACKETED / METAL JACKETED) — ALL VARIETIES

**Keywords:** double jacket(ed), metal jacketed, jacketed, copper/Teflon jacket, DJ, configuration M.
**Jackets:** SOFT IRON, CS/LCS, SS304/304L/316/316L, COPPER, BRASS, MONEL, INCONEL, TITANIUM, PTFE. **Fillers:** GRAPHITE (default metal jackets), CNAF/NON ASBESTOS, MINERAL FIBER, MICA, CERAMIC, RUBBER (PTFE jackets).
Foreign vocab: FER TENDRE=SOFT IRON, FE ARMCO=ARMCO IRON, ASBSTOS FREE=ASBESTOS FREE, REVETU=jacketed.

| # | Variety | Template |
|---|---|---|
| DJ-1 | Non-std OD/ID (primary) | `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, DOUBLE JACKETED, {JACKET} WITH {FILLER} FILLER[, WITH RIB|, WITHOUT RIB][ (AS PER DRAWING)]` |
| DJ-2 | Copper style | `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, DOUBLE JACKET GASKET WITH COPPER + GRAPHITE FILLED` |
| DJ-3 | Corrugated-type | `..., {JACKET} DOUBLE JACKETED GASKET WITH CORRUGATED TYPE {FILLER} FILLER` |
| DJ-4 | Std flange | `SIZE: {x}" X {ppp}#, DOUBLE JACKETED GASKET, {JACKET} WITH {FILLER} FILLER, ASME B16.20` |
| DJ-5 | With lip / shaped | DJ-1 + `, ROUND WITH LIP` / shape + drawing |
| DJ-6 | Pass-partition / diamond | drawing mandatory: `...WITH PASS PARTITION (AS PER DRAWING)` |
Rib unstated ⇒ quote + `KINDLY CONFIRM RIB DETAILS` (never guess). Typ. THK 3MM (HX), 1.5MM (small copper).

# ═══════════════════════════════════════════════════════════════════
# SECTION 7 — ISK (INSULATING GASKET KITS) — ALL VARIETIES

**Keywords:** insulating/insulation/isolation kit, GSKT INSULATION, FIK, dielectric, VCS/VCFS/PGE/PGS/Pikotek/LineBacker, G10/G11 + sleeves + washers.
**TYPE:** E = full face FF | F = raised face RF (OD inside bolt circle) | D = RTJ groove.
**Kit contents:** 1 gasket + sleeves (G10/G11/GRE/MYLAR/phenolic/Nomex, wall ≈0.8MM) + insulating washers (G10/G11 3MM) + metallic washers (ZINC PLATED CS 3MM / XYLAN CS / SS / PTFE COATED CS / HARDENED DIELECTRIC COATED 316).
**Cores:** SS316, SS316/316L, UNS S32760, INCOLOY 825, INCONEL 625. **Seals:** PTFE spring-energized, VITON/EPDM O-ring, MICA secondary.
**Fire-safe logic:** MICA/secondary seal or fire-tested ⇒ `(FIRE SAFE)`; PTFE-only/phenolic/no core ⇒ `(NON FIRE SAFE)`. ALWAYS print one.

| # | Style/Variety | Template |
|---|---|---|
| I-1 | Simple (customer construction) | `SIZE: {x}" X {ppp}#, INSULATING GASKET, {retainer}, W/{core} CORE, {sleeve} SLEEVES AND WASHER` |
| I-2 | GRE G-10 Type-F kit | `SIZE: {x}" X {ppp}#,INSULATING GASKET KIT,GRE G-10 WITH SS316/SS316L CORE,SLEEVES: GRE/MYLAR, SEAL RING,PTFE SSPRES ENRG SPIRAL RING,RF,(NON FIRE SAFE)` |
| I-3 | STYLE-CS (≈Pikotek VCS/PGS Commander) | `SIZE: {x}" X {ppp}#, INSULATING GASKET KIT, STYLE-CS, (SET: G10 GASKET WITH {CORE} CORE 3MM THK WITH PTFE SPRING ENERGISED SEAL, G10 SLEEVES, G10 INSULATING WASHER 3MM THK, METALLIC WASHER ZINC PLATED CS WASHER 3MM THK), RF, {std}` |
| I-4 | STYLE-FCS fire safe (≈VCFS) | `..., STYLE-FCS (SET: G10/G11 GASKET WITH {CORE} CORE {t}MM THK, PTFE PRIMARY SEAL, MICA SECONDARY SEAL, GRE G10/G11 WASHER & SLEEVES, HARDENED DIELECTRIC COATED 316 METALLIC WASHER 3MM THK), RF, ASME B16.5 (FIRE SAFE)` |
| I-5 | TYPE "E" full face phenolic | `{x}" X {ppp}#,FLANGE INSULATION GASKET KIT TYPE "E" FULL FACE,NEOPRENE FACED PHENOLIC GASKET, G11 SLEEVE, G11 WASHERS & PTFE COATED CS WASHER,ASME B16.5 (NON FIRE SAFE)` |
| I-6 | STYLE-N (≈PGE/LineBacker) | `SIZE: {x}" X {ppp}#, INSULATING GASKET KIT (STYLE-N) GRE G10 CORE 4MM THK, PRIMARY SEAL PTFE, SLEEVE GRE G10, INSULATING WASHER G10, METALLIC WASHER ZINC PLATED CS WASHER 3MM THK, RF (NON-FIRE SAFE)` |
| I-7 | DN water kit (EN 681/1514) | `SIZE: {x} DN X PN{x}#, INSULATING GASKET KIT, G10 WITH EPDM "O" RING, G10 WASHER, MS WASHER, G10 SLEEVES, WITHOUT STEEL CORE, FF, (NON-FIRE SAFE)` |
| I-8 | Large B16.47 | I-3/I-4 with `ASME B16.47 (SERIES-A)` |
| I-9 | Novel construction | `WILL QUOTE SOON` |
Pressure future-proofing: kits exist to ANSI 2500#/API 15000 — never REGRET on pressure alone.

# ═══════════════════════════════════════════════════════════════════
# SECTION 8 — SPECIALTY & OUT-OF-FAMILY PRODUCTS

| # | Product | Detect | Template |
|---|---|---|---|
| S-1 | **SHEET** | sheet/roll, L×W no flange | `SIZE: {L}MM LENGTH X {W}MM WIDTH X {t}MM THK, {MATERIAL} SHEET` (MTR form ok; insert variants: `GRAPHITE SHEET WITH SS316 TANGED/FOIL INSERT`; roll: `...{MATERIAL} ROLL`) |
| S-2 | **O-RING** | O-RING as product | `SIZE: [{OD}MM OD X ]{ID}MM ID X {CS}MM THK, [HIGH PRESSURE ]{MATERIAL} O-RING` — cord: `SIZE: {CS}MM CS X {L}MTR LENGTH, {MATERIAL} O-RING CORD`; dash no. kept; drop bar rating, "TYPE: FLAT" |
| S-3 | **LENS** | lens ring/lenticular | `SIZE: DN{x} X PN{x}, LENS RING GASKET, {MATERIAL}, DIN 2696` — non-std: dims + (AS PER DRAWING) |
| S-4 | **LIP SEAL** | lip seal as noun | `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, {PTFE|VITON|NBR} [SPRING ENERGISED ]LIP SEAL (AS PER DRAWING)` — "WITH LIP" as shape stays in parent family |
| S-5 | **DIAPHRAGM** | diaphragm/diaphram | `SIZE: {OD}MM OD X {t}MM THK, {MATERIAL} DIAPHRAGM[ WITH FABRIC REINFORCEMENT] (AS PER DRAWING)` |
| S-6 | **CMG** | corrugated gasket standalone | `SIZE: {x}" X {ppp}# X {t}MM THK, {CORE} CORRUGATED METAL GASKET WITH GRAPHITE FACING LAYERS[, {std}]` / W3 dims form; plain: `(PLAIN)`. "corrugated type filler" inside DJ text ⇒ stays DJI |
| S-7 | **MANHOLE/HANDHOLE** | manhole, handhole, boiler, obround | soft/graphite: `SIZE: {A}MM X {B}MM OBROUND X {t}MM THK, {MATERIAL} MANHOLE GASKET`; spiral: SPW-10; shapes round/obround/oval/pear/diamond → drawing if odd |
| S-8 | **ENVELOPE** | PTFE envelope | `SIZE: {x}" X {ppp}# X {t}MM THK, PTFE ENVELOPE GASKET WITH {CNAF|EPDM|CORRUGATED SS316} INSERT, ASME B16.21` (W2: EN 1514-3) |
| S-9 | **METAL CLAD** | edge/one-side clad | `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, {METAL} CLAD GASKET WITH {FILLER} CORE[ (AS PER DRAWING)]` — full enclosure ⇒ DJI |
| S-10 | **SOLID METAL FLAT** | solid metal ring, T&G, M-F | `SIZE: {dims or x" X ppp#} X {t}MM THK, SOLID {MATERIAL} FLAT RING GASKET[, {x} BHN HARDNESS]` — T&G/M-F dims from customer/drawing |
| S-11 | **PLUG GASKET** | plug gasket/seal | `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, {MATERIAL} PLUG GASKET[ (AS PER DRAWING)]` — thread-size only ⇒ ask dims |
| S-12 | **EYELET** | eyelet(ted) | `SIZE: {dims or flange size} X {t}MM THK, {CNAF|GRAPHITE} GASKET WITH {SS316|COPPER} INNER EYELET[, ASME B16.21]` |
| S-13 | **CORRUGATED (soft, legacy)** | corrugated CAF/Gacli names | map to S-6 with facing |

## Adjacent products (quote/REGRET policy — set once with sales)
Gland packing & graphite tape → CONFIGURABLE (`SIZE: {x}MM SQ X {L}MTR, {MATERIAL} BRAIDED GLAND PACKING`) or REGRET | Spectacle blind/spade/spacer → REGRET | Stud bolts/nuts alone → REGRET (unless ISK set) | Expansion joint/bellows → REGRET | PTFE valve seats → drawing → WILL QUOTE SOON | HX full gasket SET → decompose per drawing / KINDLY PROVIDE DRAWING | Thermal insulation/cloth/rope → REGRET.

# ═══════════════════════════════════════════════════════════════════
# SECTION 9 — MASTER LOOKUP TABLES

## 9.1 Material aliases (normalize; never change alloy)
SS316←316/AISI 316/Type 316/UNS S31600/Tp316 | SS316L←316L/F316L | SS304←304/Tp304 | SS304L | SS310/310S | SS316H | SS317/317L | SS321/321H | SS347/347H | SS410/410S | SOFT IRON←SI/S.I./Iron/SFT IRON/FER TENDRE | ARMCO IRON←FE ARMCO | LCS←LTCS/G10100 | CS←carbon steel/MS(context) | INCONEL 625←INC625/Alloy 625/UNS N06625/INCOLY 625 | INCOLOY 800/800H | INCOLOY 825←Alloy 825/UNS N08825/INCOLY 825 | MONEL 400 | HASTELLOY C276←UNS N10276 | ALLOY 20 | 6MO←UNS S31254 | TITANIUM GR.2/GR.12 | UNS S31803/S32205 DUPLEX | UNS S32750/S32760 SUPER DUPLEX | BRASS/BRONZE/ALUMINIUM/CU-NI 70/30 | 5CR-0.5MO←F5/A182-F5 | 9CR-1MO←F9 | 2-1/4CR-1MO←F22 | SS316TI←1.4571.
Fix always: INCOLY→INCOLOY, SILICON→SILICONE, OCATGONAL→OCTAGONAL, SOFTIRON→SOFT IRON, ASME 16.20→ASME B16.20.

## 9.2 Filler aliases
GRAPHITE FILLER←graphite/FG/GPH/grafoil/graphoil/"graphite filled" | FLEXIBLE GRAPHITE FILLER (if "flexible" written) | FLEXIBLE INHIBITED GRAPHITE FILLER | GRAPH 98% FILLER (verbatim) | PTFE FILLER←teflon/virgin/ePTFE | CNAF FILLER | VERMICULITE FILLER←thermiculite (grade kept: THERMICULITE 715/835/845/855) | MICA / MICA-GRAPHITE | CERAMIC | MINERAL FIBER | ASBESTOS FREE.

## 9.3 Thickness conversions
1/64"=0.4 | 1/32"=0.8 | 1/16"=1.6 | 3/32"=2.4 | 1/8"=3.2 | 5/32"=4.0 | 3/16"=4.8 | 0.175"=4.5 | 1/4"=6.4 MM.

## 9.4 DN↔NPS (parse aid ONLY — never convert output)
DN15=1/2" | 20=3/4" | 25=1" | 32=1-1/4" | 40=1-1/2" | 50=2" | 65=2-1/2" | 80=3" | 100=4" | 125=5" | 150=6" | 200=8" | 250=10" | 300=12" | 350=14" | 400=16" | 450=18" | 500=20" | 600=24".

## 9.5 Brand dictionary (3 buckets)
**B1 style codes → translate:** SPW interchange (Section 3 table): R/SW/W/911=winding only; CG/RW/WR/913/CR=+OR; CGI/RWI/WRI/913M/CRIR/DRI=+IR+OR; RIR=IR only; LS/LSI/LE/WRI-LC=low stress; CG-RJ/WRI-RJ=RTJ-groove SPW. KAMM: FLEXPRO/Kammpro/Maxiprofile/Leader-KAM/Camprofile=KAMMPROFILE. CMG: GRAPHONIC. Manhole: MC/MCR, Black-Max=graphite obround.
**B2 material trade names → generic (+grade kept, brand to deviation):** Klingersil C-4400=CNAF ARAMID/NBR BS7531 GR Y | C-4430=CNAF GLASS-SYNTH/NBR BS7531 GR X | C-4500=carbon fibre CNAF | C-8200=PTFE-bonded CNAF | Durlon 8300/8500/8600=CNAF (8600 white food) | Durlon 9000=FILLED PTFE | Gylon 3500/3504/3510=FILLED PTFE (silica fawn / glass-microsphere blue / barium-sulphate off-white) | Blue-Gard 3000=CNAF | Graph-Lock=graphite laminate w/ insert | Teadit NA-xxxx=CNAF | Grafoil/Sigraflex=FLEXIBLE GRAPHITE | Gore GR=ePTFE | Tealon=FILLED PTFE | Viton=FKM(keep VITON) | Teflon=PTFE | Buna-N=NBR | Neoprene=CR | Hypalon=CSM | Kalrez/Chemraz=FFKM(flag premium) | Aflas=FEPM | **CAF=asbestos → quote CNAF + deviation note**.
**ISK brands:** Pikotek VCS→STYLE-CS | VCFS→STYLE-FCS (FIRE SAFE) | PGE/LineBacker→STYLE-N | PGS Commander→STYLE-CS | ISOPRO-NFP→TYPE E phenolic | VCXT/novel→WILL QUOTE SOON.
**B3 verbatim:** KROLL & ZILLER (G-ST-P/S) WITH SPACER; Victaulic-style coupling seals; patented no-generic items.
Unknown brand ⇒ construction words in text, else `KINDLY PROVIDE DATASHEET / DETAILED MATERIAL DESCRIPTION` + log for dictionary.

## 9.6 Synonyms
SWG/spiral=SPW | camprofile/grooved/serrated/PROFILE GASKET=KAMM | MJ/jacketed/DJ=DJI | RJ/ring joint=RTJ | FIK/dielectric/isolation kit=ISK | jointing/fibre gasket=CNAF SC | centering=guide=outer ring | filler=facing=soft layer | lb=#=CL=class=rating | SS=CRES | MS=mild steel | GI=galvanised iron.

# ═══════════════════════════════════════════════════════════════════
# SECTION 10 — ESCALATIONS (exact strings)
`WILL QUOTE SOON` | `KINDLY PROVIDE RING NO` | `AS PER ASME STANDARD RING NUMBER IS NOT AVAILABLE SO KINDLY PROVIDE DIMENSIONS` | `KINDLY PROVIDE DRAWING` | `KINDLY PROVIDE DRAWING WITH DIMENSION` | `KINDLY PROVIDE CLEAR SPEC` | `KINDLY PROVIDE DATASHEET / DETAILED MATERIAL DESCRIPTION` | `KINDLY CONFIRM RIB DETAILS` (note beside quote) | `REGRET`.

# SECTION 11 — VALIDATION CHECKLIST (deterministic, run after assembly)
1 `SIZE:` prefix or escalation. 2 W1 inches carry `"`; W2 DN/NB carry NONE. 3 THK present (SC/SPW/KAMM/DJI/CMG/sheet/O-ring). 4 Filler = customer's exactly. 5 Both rings when both stated. 6 RTJ complete: ring no+RTJ+shape+material(+coating)+BHN+correct std (BX⇒API 6A, RX⇒API 6B+NACE, R+ASME⇒B16.20). 7 SPW std ≠ API; PTFE⇒IR; IR-mandate classes. 8 ≥26"⇒B16.47. 9 PROFILE GASKET⇒KAMM. 10 OD>ID all W3. 11 KAMM W3 has `({core}MM CORE THK)`. 12 ISK ends (FIRE SAFE)/(NON FIRE SAFE). 13 Drawing ref⇒(AS PER DRAWING). 14 Class exists for size (gaps rule). 15 LENS⇒DIN 2696 or drawing. 16 OBROUND⇒two axes. 17 ENVELOPE⇒insert stated. 18 Brand translated⇒deviation note present. 19 Spellings canonical. 20 No customer noise leaked.

# SECTION 12 — GOLD FEW-SHOT SET (condensed, one per pattern)
```
SC std        : NPS 2, CNAF Flat Ring, Cl.150, ASME B16.21 → SIZE: 2" X 150# X 3MM THK,CNAF,RF,ASME B16.21
SC FF rubber  : NPS 12 full face elastomer shore A 50-60 Cl150 → SIZE: 12" X 150# X 3MM THK,EPDM 50 - 60 SHORE A HARDNESS,FF,ASME B16.21
SC grade      : 3" 150# 2MM NONASBESTOS BS7531 GR X → SIZE: 3" X 150# X 2MM THK,NONASBESTOS BS7531 GR X,RF,ASME B16.21
SC W2         : NB100 PN6 EPDM FF EN1514-1 3mm → SIZE: NB 100 X PN6 X 3MM THK,EPDM,FF,EN 1514-1
SC brand      : Klingersil C-4400 2" 150# 1.5mm → SIZE: 2" X 150# X 1.5MM THK,CNAF (ARAMID FIBRE WITH NBR BINDER) BS7531 GR Y,RF,ASME B16.21 [DEV: EQUIVALENT TO KLINGERSIL C-4400]
SC verbatim   : Kroll & Ziller (G-ST-P/S) w/ spacer 8" Cl150 → SIZE: 8" X 150# X 4.5MM THK ,KROLLER & ZILLER (G-S-T-P/S) WITH SPACER ,FF ,ASME B16.21
SPW std       : NPS 4 SPW SS316 flexgraphite SS316 IR&OR Cl150 NACE Lethal → SIZE: 4" X 150# X 4.5MM THK,SS316 SPIRAL WOUND GASKET WITH FLEXIBLE GRAPHITE FILLER + SS316 INNER RING & SS316 OUTER RING,ASME B16.20
SPW default OR: 1/2" 150# SPW SS316+graphite → SIZE: 1/2" X 150# X 4.5MM THK,SS316 SPIRAL WOUND GASKET WITH GRAPHITE FILLER + SS316 INNER RING & CS OUTER RING,ASME B16.20
SPW CNAF      : SPW OR-SS316 IR-SS316 CNAF filler 12" 150# 0.175" → SIZE: 12" X 150# X 4.5MM THK,SS316 SPIRAL WOUND GASKET WITH CNAF FILLER + SS316 INNER RING & SS316 OUTER RING,ASME B16.20
SPW large     : NPS 30 SPW SS316 FG Cl150 → ...,ASME B16.47 (SERIES A)
SPW DN        : 20DN ASME 150 SS304 graphite 4.5 → SIZE: 20 DN X 150# X 4.5MM THK, SS304 SPIRAL WOUND GASKET WITH GRAPHITE FILLER + SS304 INNER RING & SS304 OUTER RING, ASME B16.20
SPW brand     : 4" 300# Flexitallic CGI SS316/graphite → SIZE: 4" X 300# X 4.5MM THK,SS316 SPIRAL WOUND GASKET WITH GRAPHITE FILLER + SS316 INNER RING & CS OUTER RING,ASME B16.20 [DEV: EQUIVALENT TO FLEXITALLIC CGI]
RTJ std       : NPS 2 Cl600 Soft Iron Oct RJ Galvanised → SIZE: R-23,RTJ,OCTAGONAL,SOFT IRON GALVANISED,90 BHN HARDNESS,ASME B16.20
RTJ oval      : NPS 8 OVAL RJ Cl900 SI Electroplated Zinc → SIZE: R-49,RTJ,OVAL,SOFT IRON ELECTROPLATED ZINC,90 BHN HARDNESS,ASME B16.20
RTJ glued     : RTJ2SOFT IRON (90 BHN MAX) ELECTROPLATED 900# → SIZE: R-24,RTJ,OCTAGONAL,SOFT IRON ELECTROPLATED,90 BHN HARDNESS,ASME B16.20
RTJ HRC       : RTJ0.75 UNS S32205 22HRC 1500# → SIZE: R-14,RTJ,OCTAGONAL,UNS S32205,230 BHN HARDNESS,ASME B16.20
RTJ BX        : BX-162 CADMIUM PLATED SOFT IRON 90BH API 6BX → SIZE: BX-162,RTJ,OCTAGONAL,SOFT IRON CADMIUM PLATED,90 BHN HARDNESS,API 6A
RTJ BX by size: 1 13/16 S32750 22HRC API 10000 TYPE BX → SIZE: BX-150,RTJ,OCTAGONAL,UNS S32750,240 BHN HARDNESS,API 6A
RTJ miss      : NPS 30 Cl1500 Incoloy 825 RJ → KINDLY PROVIDE RING NO
RTJ ISO27509  : 22" 1500lb ISO 27509 seal ring → AS PER ASME STANDARD RING NUMBER IS NOT AVAILABLE SO KINDLY PROVIDE DIMENSIONS
KAMM profile  : NPS 18 PROFILE GASKET Cl150 FF FKM w/ metal core → SIZE: 18" X 150# X 4.5MM THK,FLUOROCARBON RUBBER (FKM) KAMMPROFILE GASKET WITH METAL CORE,FF,ASME B16.21
KAMM std      : 24" 600# camprofile SS316/316L GPH, INR SS316/316L, CS centering → SIZE: 24" X 600# X 4.5MM THK,SS316/SS316L KAMMPROFILE GASKET WITH GRAPHITE FILLER + SS316/SS316L INNER RING & CS OUTER RING,ASME B16.20
KAMM HX       : CAMPROFILE core SS316L 3.0MM + 0.5 graphite both sides OD560 ID536 → SIZE: 560MM OD X 536MM ID X 4MM THK (3MM CORE THK), SS316L KAMMPROFILE GASKET WITH GRAPHITE LAYERS ON BOTH SIDES
DJI drawing   : DJ CONFIG M OD1430 x3x ID1404 DRAWING 6273 SOFT IRON+GRAPHITE → SIZE: 1430MM OD X 1404MM ID X 3MM THK, DOUBLE JACKETED, SOFT IRON WITH GRAPHITE FILLER (AS PER DRAWING)
DJI copper    : copper jacket 101X110X1,5 → SIZE: 110MM OD X 101MM ID X 1.5MM THK, DOUBLE JACKET GASKET WITH COPPER + GRAPHITE FILLED
DJI corr      : DJ 367OD 341ID 3.2 304L/FG corrugated type → SIZE: 367MM OD X 341MM ID X 3.2MM THK, SS304L DOUBLE JACKETED GASKET WITH CORRUGATED TYPE GRAPHITE FILLER
DJI teflon    : Tank gasket Teflon jacketed non-asb filler 3mm OD580 ID513 → SIZE: 580MM OD X 513MM ID X 3MM THK, DOUBLE JACKETED, PTFE WITH NON ASBESTOS FILLER — KINDLY CONFIRM RIB DETAILS
ISK GRE       : ½INSULATING GASKET KIT 600# TYPE-F GRE G-10 SS316/316L core GRE/MYLAR sleeves PTFE SS spring → SIZE: 1/2" X 600#,INSULATING GASKET KIT,GRE G-10 WITH SS316/SS316L CORE,SLEEVES: GRE/MYLAR, SEAL RING,PTFE SSPRES ENRG SPIRAL RING,RF,(NON FIRE SAFE)
ISK CS        : 2" 600# PGS COMMANDER EXTREME RF Type F S32760 core → SIZE: 2" X 600#, INSULATING GASKET KIT, STYLE-CS, (SET: G10 GASKET WITH UNS S32760 CORE 3MM THK WITH PTFE SPRING ENERGISED SEAL, G10 SLEEVES, G10 INSULATING WASHER 3MM THK, METALLIC WASHER ZINC PLATED CS WASHER 3MM THK), RF, ASME B16.20
ISK FCS       : ISK STYLE-FCS 2" 600# PTFE primary MICA secondary → ...STYLE-FCS (SET: ...), RF, ASME B16.5 (FIRE SAFE)
ISK E         : FIK 24" 150 LBS NEMA GR-11 sleeve neoprene-phenolic FF → 24" X 150#,FLANGE INSULATION GASKET KIT TYPE "E" FULL FACE,NEOPRENE FACED PHENOLIC GASKET, G11 SLEEVE, G11 WASHERS & PTFE COATED CS WASHER,ASME B16.5 (NON FIRE SAFE)
ISK DN        : Insulation kit EPDM EN681&1514 25 PN16 → SIZE: 25 DN X PN16#, INSULATING GASKET KIT, G10 WITH EPDM "O" RING, G10 WASHER, MS WASHER, G10 SLEEVES, WITHOUT STEEL CORE, FF, (NON-FIRE SAFE)
ISK brand     : 6" 600# Pikotek VCFS RF → STYLE-FCS ... (FIRE SAFE) [DEV: EQUIVALENT TO PIKOTEK VCFS]
O-RING        : O-RING VITON ID 14 X THK 3 250BAR → SIZE: 14MM ID X 3MM THK, VITON O-RING
O-RING OD     : SILICON ID62 OD70 THK3 → SIZE: 70MM OD X 62MM ID X 3MM THK, SILICONE O-RING
SHEET         : Teflon sheet 1000x1000x3 → SIZE: 1000MM LENGTH X 1000MM WIDTH X 3MM THK, TEFLON SHEET
LENS          : Lens ring DN50 PN250 1.4571 → SIZE: DN50 X PN250, LENS RING GASKET, SS316TI, DIN 2696
MANHOLE       : boiler manhole 300x400 obround graphite 6mm → SIZE: 400MM X 300MM OBROUND X 6MM THK, GRAPHITE MANHOLE GASKET
CMG           : corrugated SS316 graphite layers 8" 150# → SIZE: 8" X 150# X 3MM THK, SS316 CORRUGATED METAL GASKET WITH GRAPHITE FACING LAYERS
ENVELOPE      : PTFE envelope CNAF insert DN80 PN16 3mm → SIZE: 80 DN X PN16 X 3MM THK, PTFE ENVELOPE GASKET WITH CNAF INSERT, EN 1514-3
PLUG          : plug gasket OD42 ID33 2mm soft iron → SIZE: 42MM OD X 33MM ID X 2MM THK, SOFT IRON PLUG GASKET
DIAPHRAGM     : EPDM diaphragm OD220 fabric reinf, drawing → SIZE: 220MM OD, EPDM DIAPHRAGM WITH FABRIC REINFORCEMENT (AS PER DRAWING)
CAF trap      : CAF gasket 3mm 4" 150# → SIZE: 4" X 150# X 3MM THK,CNAF,RF,ASME B16.21 [DEV: CAF REQUESTED — NON-ASBESTOS EQUIVALENT OFFERED]
mm→NPS        : BUTYL RUBBER FF Size 76.1mm 150# → SIZE: 2.5" X 150# X 3MM THK,BUTYL RUBBER,FF,ASME B16.21
REGRET        : Spectacle blind 6" 300# → REGRET
Complex ISK   : novel construction, insufficient detail → WILL QUOTE SOON
```

# SECTION 13 — PIPELINE & MAINTENANCE
LLM (GPT-4o mini, temp 0, JSON mode): pre-parse → classify → extract JSON only. Deterministic Python: size-world → family rules → lookups (rings/hardness/IR-mandate/standards/brands) → template assembly → Section 11 checks. Verify call → mismatch/low-confidence → human queue. FEEDBACK sheet = permanent regression suite; every human correction becomes a test. Brand dictionary & material master stored as editable tables loaded at runtime. New family = new section with: keywords, varieties, W1/W2/W3 templates, mandatory fields, validation rows.
# ═══════════════════════ END OF DOCUMENT ═══════════════════════
