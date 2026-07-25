# GGPL GASKET PRODUCT MASTER SPECIFICATION (v3 — FUTURE-PROOF)
## ISK | KAMM | DJI | SPW | SC | RTJ — Standard, Non-Standard & All Size Systems
### The single source of truth for the GGPL Enquiry Bot

> Sources: 35k+ GGPL historical conversion pairs, GGPL material master & ASME reference sheets, FEEDBACK corrections, verified against ASME B16.20-2017, ASME B16.21-2021, ASME B16.47, API 6A/ISO 10423, EN 1514-1/EN 1092.
> Structure: PART A = universal rules (all products). PART B = one deep chapter per product family. PART C = size-system engine. PART D = validation & escalation. PART E = extraction schema & pipeline.

═══════════════════════════════════════════════════════════════════
# PART A — UNIVERSAL RULES (apply to every product)
═══════════════════════════════════════════════════════════════════

## A1. THE THREE SIZE WORLDS (never mix them)

Every enquiry lives in exactly ONE of these worlds. Detect it first; it decides the template.

| World | Detected by | Size format in output | Standard family |
|---|---|---|---|
| **W1 — ASME inch/class** | NPS, inches, ", #, LB, CL, Class 150–2500 | `{x}" X {ppp}#` | ASME B16.21 / B16.20 / B16.47 / API 6A |
| **W2 — Metric DN/PN** | DN, NB, PN, EN/DIN/ISO standards, mm nominal bore | `{x} DN X PN{x}` or `NB {x} X PN{x}` — **NEVER an inch mark on DN/NB** | EN 1514-1, EN 1092, ISO 4633, EN 681, BS 10 |
| **W3 — Non-standard dimensional** | OD/ID/length/width in mm, drawing refs, equipment gaskets (heat exchangers, tanks, covers) | `{OD}MM OD X {ID}MM ID X {t}MM THK` (OD first, then ID) | none / (AS PER DRAWING) / (NON STANDARD) |

Rules:
- If PN appears, the size is DN — even unlabeled (`25PN16` → DN 25).
- Any size number >3 digits with PN → W2 or W3, never inches.
- Never convert between W1 and W2. Quote in the customer's world.
- Mixed signals (DN size + # class, e.g. "DN450, CLASS 150") → keep exactly as customer: `450 DN X 150#`.
- W3 always writes OD before ID, regardless of customer order. Smaller number = ID, larger = OD.
- mm pipe-OD given for a flange gasket (W1 context) → map to NPS: 21.3→1/2", 26.7→3/4", 33.4→1", 42.2→1-1/4", 48.3→1-1/2", 60.3→2", 73→2-1/2" (also 76.1 EU), 88.9→3", 101.6→3-1/2", 114.3→4", 141.3→5", 168.3→6", 219.1→8", 273→10", 323.9→12", 355.6→14", 406.4→16", 457→18", 508→20", 610→24".

## A2. FLANGE-STANDARD → GASKET-STANDARD ENGINE (future-proof core)

The gasket standard is decided by (size, class, product), not by what the customer's flange note says:

| Product | ≤24" (B16.5 flanges) | 26"–60" (B16.47 flanges) | DN/PN | API wellhead |
|---|---|---|---|---|
| SC (soft cut) | ASME B16.21 | ASME B16.47 (SERIES A) — Series B if stated | EN 1514-1 / customer std | — |
| SPW | ASME B16.20 | ASME B16.47 (SERIES A) — Series B if stated | ASME B16.20 (house style) or EN 1514-2 if demanded | **NEVER API** |
| KAMM | ASME B16.20 | ASME B16.47 (SERIES A/B as stated) | EN 1514-6 if demanded | — |
| DJI | ASME B16.20 | ASME B16.47 | — | — |
| RTJ | ASME B16.20 (R rings) | ASME B16.47 (SERIES-A) / R93–R105 | — | API 6A (BX), API 6B (R/RX oilfield) |
| ISK | to suit ASME B16.5 | to suit ASME B16.47 (SERIES-A) | to suit EN 1092 / BS EN | to suit API 6A |

- ASME B16.47 Series A NPS 12–24 shares raised-face dims with B16.5 — if customer explicitly says "B16.47 Series A" at ≤24", honor it.
- Class-400 note: no class 400 flanges NPS 1/2–3 (use 600 gasket); no class 900 NPS 1/2–2-1/2 (use 1500); no class 2500 NPS ≥14.
- Future new standards (EN 12560, JIS B2404, GOST, AS 2129 Table D/E, SANS 1123): keep the customer's standard verbatim in the standard slot; classify by product family as usual. Never force-fit ASME.

## A3. OUTPUT GRAMMAR (all products)

- UPPERCASE. Prefix `SIZE: ` (no space before colon, one after).
- Separator inside the size block: ` X ` (spaces around X).
- Field separator: comma. Consistent spacing.
- Thickness always as `{t}MM THK` (decimal point, not comma).
- Never leak: flange references ("for B16.5 flanges"), tag/PL/cat/item numbers, service notes, "Lethal", "oil quality", QA/QC certs, pressure ratings of O-rings, pipe schedules. These go in structured side-fields (customer_item_code, notes), never in the GGPL string.
- NACE: dropped by default; retained for RTJ RX template (always), and appended as `NACE MR0175` before the standard when the customer explicitly demands NACE material certification.
- Coating always retained (RTJ + metallic washers): GALVANISED, ZINC PLATED, CADMIUM PLATED, ELECTROPLATED, XYLAN COATED, PTFE COATED, EPOXY COATED.
- Drawing number present → append `(AS PER DRAWING)`.
- Canonical spellings: OCTAGONAL, INCOLOY, INCONEL, HASTELLOY, GALVANISED, SILICONE, KAMMPROFILE, ASME B16.20 / B16.21 / B16.47 (SERIES A).

## A4. FIDELITY LAWS (violations = severe errors)

1. **Filler fidelity** — stated filler is copied exactly (CNAF, PTFE, GRAPH 98%, VERMICULITE/THERMICULITE grade, MICA, CERAMIC). Graphite is only the silence-default.
2. **Material fidelity** — normalize the name, never change the alloy. UNS codes may be kept as UNS or mapped to trade name; never map to a different grade.
3. **Both-rings law** — SPW/KAMM: if IR and OR are both stated, both appear in output.
4. **Shape fidelity** — RTJ OVAL stays OVAL. RX/BX are ring TYPES, never shapes.
5. **Unique/branded items** (Kroll & Ziller, proprietary seals) — reproduce customer wording verbatim.
6. **No guessed construction** — rib (DJI/KAMM), fire-safety (ISK), ring number: derived from rules or asked, never invented.

═══════════════════════════════════════════════════════════════════
# PART B — PRODUCT FAMILY CHAPTERS
═══════════════════════════════════════════════════════════════════

## B1 — SC (SOFT CUT / NON-METALLIC FLAT GASKETS) — ASME B16.21

**What it is:** flat gaskets cut from sheet — CNAF, rubber (EPDM/NBR/CR/FKM/silicone/butyl/SBR/HNBR), PTFE, expanded PTFE, graphite (with/without metal insert), cork, oil paper, specialty branded (Kroll & Ziller).

**Keywords:** CNAF, non-asbestos, compressed fiber, flat ring, full face, rubber gasket, elastomer, shore hardness, PTFE flat, graphite sheet, IBC.

**Forms (know all three — future-proof):**
- **Flat Ring / IBC** (inside bolt circle) — sits within bolts, for RF flanges → facing = **RF** (write RF; "IBC" if customer uses it)
- **Full Face (FF)** — covers whole flange incl. bolt holes, for FF flanges → **FF**
- B16.21-2021 covers B16.5 flanges AND B16.47 Series A large flanges; Class 150 has flat-ring + full-face tables; classes 300/600/900 flat ring only. Rubber full-face on high class is unusual → sanity-check.

**Facing default:** ring type → RF; "full face"/FF flange/soft rubber utility service → FF.
**Thickness default:** 3MM; honor stated 1.5/1.6/2/3.2MM. Shore hardness retained: `EPDM 50 - 60 SHORE A HARDNESS`.

**Templates:**
- W1: `SIZE: {x}" X {ppp}# X {t}MM THK,{MATERIAL},{RF|FF},ASME B16.21`
- W1 large: `SIZE: {x}" X {ppp}# X {t}MM THK,{MATERIAL},{RF|FF},ASME B16.47 (SERIES A)` — B16.21 covers Series A dims; house style cites B16.47 for ≥26"
- W2: `SIZE: {x} DN X PN{x} X {t}MM THK,{MATERIAL},{RF|FF},{EN 1514-1|customer std}` / `SIZE: NB {x} X PN{x} X {t}MM THK,...`
- W3 ring: `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, {MATERIAL} GASKET (NON STANDARD)`
- W3 rectangular: `SIZE: {L}MM LENGTH X {W}MM WIDTH X {t}MM THK, {MATERIAL} GASKET (NON STANDARD)` — manway/handhole obround: `{L}MM X {W}MM OBROUND, {MATERIAL} (AS PER DRAWING)`
- Sheet: `SIZE: {L}MM LENGTH X {W}MM WIDTH X {t}MM THK, {MATERIAL} SHEET` (per-metre: `{x}MTR`)

**Special SC sub-types:** steel-insert rubber (`EPDM WITH SS304 INSERT` — verify insert metal), graphite reinforced (`FLEXIBLE GRAPHITE REINFORCED W/SS316 SHEET INSERT`), grade-spec materials verbatim (`NONASBESTOS BS7531 GR X`), branded verbatim (`KROLLER & ZILLER (G-S-T-P/S) WITH SPACER`).

---

## B2 — SPW (SPIRAL WOUND) — ASME B16.20

**What it is:** V-profile metal strip wound with soft filler; centering (outer) ring, optional inner ring.

**Keywords:** spiral wound, SPW, SWG, winding, CGI, centering ring, inner/outer ring, "spiral wounded".

**Construction facts (verified against B16.20-2017):**
- Sealing element uncompressed thickness 4.45MM → GGPL quotes **4.5MM THK** standard; compressed ≈3.2MM (customer "3.2mm compressed" still = 4.5MM gasket)
- Inner/outer ring thickness 2.97–3.33MM (≈3MM/3.2MM — don't quote separately unless asked)
- Other thicknesses exist: 3.2MM (small/low-profile), 6.4MM (1/4", large equipment) — honor if stated
- **Inner ring MANDATORY per B16.20:** Class 900 NPS ≥24; Class 1500 NPS ≥12; Class 2500 NPS ≥4; **ALL PTFE-filled gaskets**; all flexible-graphite where buckling risk. → If customer omits IR in these cases, ADD IR (winding material) and note the addition.
- Outer/centering ring default: **CS** (coated carbon steel); SS304 for < -45°C service; customer's "SS centering ring" → winding material or stated SS grade.

**Materials:** winding SS316/316L/304/321/347/duplex/super duplex/Monel/Inconel 625/Incoloy 825/Hastelloy C276/titanium/6Mo/UNS codes. Filler: graphite (default), flexible/inhibited graphite, PTFE, CNAF, vermiculite (Thermiculite 715/835), mica-graphite (high temp), ceramic (legacy).

**Templates:**
- W1: `SIZE: {x}" X {ppp}# X {t}MM THK,{WINDING} SPIRAL WOUND GASKET WITH {FILLER} FILLER + {IR} INNER RING & {OR} OUTER RING,ASME B16.20`
- No IR variant (only when genuinely without IR and not mandated): `...WITH {FILLER} FILLER + {OR} OUTER RING,ASME B16.20`
- W1 ≥26": `...,ASME B16.47 (SERIES A)` (SERIES B if stated; Series B has no class 900 in some sizes — trust customer)
- W2: `SIZE: {x} DN X {PN{x}|{ppp}#} X {t}MM THK, {WINDING} SPIRAL WOUND GASKET WITH {FILLER} FILLER + {IR} INNER RING & {OR} OUTER RING, ASME B16.20`
- W3 (equipment SPW): `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, {WINDING} SPIRAL WOUND GASKET WITH {FILLER} FILLER[ + {IR} INNER RING & {OR} OUTER RING] (NON STANDARD / AS PER DRAWING)`
- Suffix options: `(LOW STRESS)` low-seating-stress spec; heat-exchanger SPW with pass bars → W3 + drawing.

**Hard rules:** never API standard; never swap stated filler; both rings when both stated; IR-mandate check.

---

## B3 — RTJ (RING TYPE JOINT) — ASME B16.20 + API 6A

**What it is:** solid metal rings (oval/octagonal/RX/BX) seating in flange grooves; highest pressure gasket family.

**Keywords:** ring joint, RTJ, ring type, octagonal, oval, R-/RX-/BX-, API 6A/6B/6BX, wellhead, Christmas tree.

**The four ring types (future-proof taxonomy):**
| Type | Profile | Flanges | Pressure | Standard slot |
|---|---|---|---|---|
| R OVAL | oval | B16.5, B16.47-A, API 6B, old round-bottom grooves | ≤5000 psi / ≤2500# | ASME B16.20 (or API 6A if 6B flange) |
| R OCTAGONAL | octagonal (preferred, better seal) | flat-bottom grooves, same as above | same | same |
| RX | pressure-energized asymmetric; fits same groove as R (interchangeable joint, NOT same cross-section) | API 6B | 2000–5000 psi | NACE MR-01-75 / ISO 15156, API 6B |
| BX | pressure-energized square-with-bevel; 6BX flanges ONLY; not interchangeable with R/RX | API 6BX | 5000–20000 psi | API 6A |

- R rings: R11–R105. RX: RX20–RX91 (RX82–91 have pressure passage holes — blind-flange sizes). BX: BX150–BX169.
- Hardness law: ring 15–20 HB softer than flange groove — GGPL quotes per material table (PART 7 of v2: SOFT IRON 90, CS/LCS 120, F5 130, C276 140, SS3xx 160, SS410/F9 170, INCOLOY 800 180, INCOLOY 825 195, INCONEL 625 210, S32205 230, S31803 235, S32750 240).
- HRBW/HRC inputs: 83 HRBW=160 BHN, 68 HRBW=120 BHN, 22 HRC→material standard BHN.
- API-vs-ASME dimension equivalence (useful for parsing): API 6B 2000 psi ≈ Class 600 dims; 3000 ≈ 900; 5000 ≈ 1500.

**Ring number resolution order:**
1. Customer states ring no. → use it.
2. NPS+class → v2 PART 6A table (R11–R79, incl. 1-1/4"–5" intermediates; note 900# shifts).
3. 26–36" B16.47 → R93–R98 (300–600#) / R100–R105 (900#).
4. API PSI+size → RX/BX table (v2 PART 6C).
5. Unresolvable → `KINDLY PROVIDE RING NO`. ISO 27509/compact flange → dimensions escalation.

**Templates:**
- `SIZE: R-{xx},RTJ,{OCTAGONAL|OVAL},{MATERIAL}[ {COATING}],{x} BHN HARDNESS,ASME B16.20`
- API 6B R/RX: `SIZE: R-{xx},RTJ,{shape},{MATERIAL},{x} BHN HARDNESS,API 6A` / `SIZE: RX-{xx}, RTJ, OCTAGONAL, {MATERIAL}, {x} BHN HARDNESS, NACE MR-01-75 / ISO 15156, API 6B`
- BX: `SIZE: BX-{xx},RTJ,OCTAGONAL,{MATERIAL}[ {COATING}],{x} BHN HARDNESS,API 6A` — never ASME B16.20
- Large: `SIZE: {x}" X {x}00#, RTJ, OCTAGONAL, {MATERIAL}, {x} BHN HARDNESS, ASME B16.47 (SERIES-A)`
- W3 custom ring (drawing): `SIZE: {OD}MM OD X {ID or PCD}MM X {H}MM HIGH, RTJ {shape}, {MATERIAL}, {x} BHN HARDNESS (AS PER DRAWING)`

---

## B4 — KAMM (KAMMPROFILE / CAMPROFILE / GROOVED METAL) — ASME B16.20

**What it is:** solid concentrically-serrated metal core with soft facing layers (graphite/PTFE) both sides; the heat-exchanger workhorse; per B16.20 "grooved metal gaskets with covering layers" = grooved core + centering ring.

**Keywords:** kammprofile, camprofile, cam/kamm, grooved metal, serrated, **PROFILE GASKET** (⚠ always KAMM), covering/facing layers, pass bar, rib.

**Construction:**
- Core: SS316/316L/304/321/Monel/Inconel/duplex/titanium; core thk typ. 3–4MM
- Facing: flexible graphite (default) or PTFE, typ. 0.5MM per side; total = core + 2×layer
- Standard flange type: with loose or integral **centering/outer ring** (CS default, or core material)
- Heat-exchanger type: no outer ring, or integral ring, optional **RIB / pass bars** (single/double/multi-pass partition bars), oval/rectangular/obround shapes possible — drawings required for non-standard shapes

**Templates:**
- W1 standard: `SIZE: {x}" X {ppp}# X {t}MM THK,{CORE} KAMMPROFILE GASKET WITH {GRAPHITE|PTFE} FILLER + {IR} INNER RING & {OR} OUTER RING,ASME B16.20` (≥26" → B16.47 SERIES A/B as stated)
- W3 (HX, the common case): `SIZE: {OD}MM OD X {ID}MM ID X {total}MM THK ({core}MM CORE THK), {CORE MAT} KAMMPROFILE GASKET WITH {GRAPHITE|PTFE} LAYERS ON BOTH SIDES[ + INTEGRAL {mat} OUTER RING][, WITH RIB|, WITHOUT RIB][ (AS PER DRAWING)]`
- Pass-bar/multi-pass: append `WITH {n} PASS BAR / PARTITION RIB (AS PER DRAWING)`
- Thickness math: "3.0MM core + 0.5MM graphite both sides" → `4MM THK (3MM CORE THK)`. Default standard-flange total 4.5MM.

**Hard rules:** PROFILE GASKET = KAMM; rib asked not guessed; capture core AND layers; FKM/rubber facings on profile gaskets stay KAMM.

---

## B5 — DJI (DOUBLE JACKETED / METAL JACKETED) — ASME B16.20

**What it is:** soft filler fully enclosed in a formed metal jacket (top+bottom, overlapped); classic heat-exchanger, boiler, tank & cover gasket; mostly made to equipment dims.

**Keywords:** double jacket(ed), metal jacketed, jacketed gasket, copper/PTFE/Teflon jacket, DJ, configuration M, corrugated DJ.

**Construction:**
- Jacket: SOFT IRON, CS/LCS, SS304/304L/316/316L, copper, brass, Monel, Inconel, titanium, PTFE (soft jacket)
- Filler: graphite (default), non-asbestos/CNAF, mineral fiber, mica, ceramic
- Thickness: typ. 3MM (HX), 1.5MM (small copper), customer-driven
- Variants: plain DJ, **corrugated DJ** (`CORRUGATED TYPE {filler} FILLER`), DJ with RIB / pass bars, shaped (obround, rectangular, diamond pass-partition) → always drawing
- French/foreign vocab: FER TENDRE=SOFT IRON, FE ARMCO=ARMCO IRON, ASBSTOS FREE=ASBESTOS FREE, REVETU=jacketed

**Templates:**
- W3 (primary): `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, DOUBLE JACKETED, {JACKET} WITH {FILLER} FILLER[, WITH RIB|, WITHOUT RIB][ (AS PER DRAWING)]`
- Copper style: `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, DOUBLE JACKET GASKET WITH COPPER + GRAPHITE FILLED`
- Corrugated: `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, {JACKET} DOUBLE JACKETED GASKET WITH CORRUGATED TYPE {FILLER} FILLER`
- W1 (flange DJ, rare): `SIZE: {x}" X {ppp}#, DOUBLE JACKETED GASKET, {JACKET} WITH {FILLER} FILLER, ASME B16.20`
- Rib unknown → quote + `KINDLY CONFIRM RIB DETAILS`.

---

## B6 — ISK (INSULATING / ISOLATION GASKET KITS)

**What it is:** electrical flange isolation set = 1 gasket + bolt sleeves + insulating washers + metallic washers; fights galvanic corrosion & provides cathodic protection isolation.

**Keywords:** insulating/insulation/isolation kit, GSKT INSULATION, flange isolation, VCS/VCFS/PGE/PGS/Pikotek/LineBacker/Evolution, G10/G11 with sleeves & washers.

**TYPE (gasket footprint) — industry-wide taxonomy:**
| Type | Fit | Facing |
|---|---|---|
| **E** | full face, OD = flange OD, bolt holes | FF |
| **F** | raised face only, OD inside bolt circle, aligned by sleeves | RF |
| **D** | fits RTJ ring groove | RTJ |

**STYLE (construction) — GGPL naming:**
| Style | Construction | Fire status |
|---|---|---|
| Plain / phenolic kit | G10/G11/phenolic (or neoprene/nitrile-faced phenolic) gasket, no core | NON FIRE SAFE |
| **N** | GRE retainer + primary seal (PTFE), no/basic core | NON FIRE SAFE |
| **CS** (≈ VCS/Pikotek/PGS Commander) | G10/G11 laminate bonded to metal core + PTFE spring-energized seal (or O-ring) | NON FIRE SAFE unless secondary |
| **FCS** (≈ VCFS) | CS + PTFE primary + MICA/E-ring secondary seal, hardened dielectric washers | **FIRE SAFE** (API 6FB) |
| DN water kit | G10 + EPDM O-ring, no steel core, MS washers | NON FIRE SAFE |

**Fire-safe logic:** MICA/secondary seal OR fire-tested construction → (FIRE SAFE); PTFE-only / phenolic / no core → (NON FIRE SAFE). ALWAYS print one.

**Kit set contents (SET: ...):** gasket w/ core & seal, sleeves (G10/G11/GRE/MYLAR/phenolic/Nomex; std wall ≈0.8MM), insulating washers (G10/G11 3MM), metallic washers (ZINC PLATED CS 3MM / XYLAN COATED CS / SS / PTFE COATED CS / hardened dielectric coated 316).
**Cores:** SS316, SS316/316L, UNS S32760, INCOLOY 825, Inconel 625. **Seals:** PTFE spring-energized, Viton/EPDM O-ring, MICA secondary.

**Templates:** (as v2 3.11–3.13 — simple, GRE G-10 kit, STYLE-CS SET, STYLE-FCS FIRE SAFE, TYPE "E" FULL FACE, STYLE-N, DN water kit). Pressure range future-proofing: kits exist up to ANSI 2500# and API 10000–15000 psi — never REGRET an ISK on pressure alone.
- Escalate complex novel constructions → `WILL QUOTE SOON`.

═══════════════════════════════════════════════════════════════════
# PART C — SIZE-SYSTEM ENGINE (quick reference)
═══════════════════════════════════════════════════════════════════

- NPS list: 1/2, 3/4, 1, 1-1/4, 1-1/2, 2, 2-1/2, 3, 3-1/2, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 24 (B16.5); 26–60 even sizes (B16.47).
- Class list: 150, 300, 400*, 600, 900*, 1500, 2500* (*gaps per A2 note). PN list: 2.5, 6, 10, 16, 25, 40, 63, 100.
- DN↔NPS reference (NEVER auto-convert; parse only): DN15=1/2", DN20=3/4", DN25=1", DN32=1-1/4", DN40=1-1/2", DN50=2", DN65=2-1/2", DN80=3", DN100=4", DN125=5", DN150=6", DN200=8", DN250=10", DN300=12", DN350=14", DN400=16", DN450=18", DN500=20", DN600=24".
- API 6B: 2000/3000/5000 PSI (R/RX). API 6BX: 5000/10000/15000/20000 PSI (BX). API sizes: 1-13/16, 2-1/16, 2-9/16, 3-1/16, 4-1/16, 5-1/8, 7-1/16, 9, 11, 13-5/8, 16-3/4, 18-3/4, 21-1/4".
- Unicode/format cleanup: ½→1/2, ¾→3/4, ⅜→3/8, 1.1/2→1-1/2, comma decimals→points, strip NPS/IN/inch to `"`.
- Thickness conversions: 1/32"=0.8, 1/16"=1.6, 3/32"=2.4, 1/8"=3.2, 5/32"=4.0, 3/16"=4.8, 0.175"=4.5, 1/4"=6.4 MM.

═══════════════════════════════════════════════════════════════════
# PART D — VALIDATION MATRIX & ESCALATIONS
═══════════════════════════════════════════════════════════════════

## D1. Per-product mandatory fields
| Product | Must have | Auto-derivable | Ask if missing |
|---|---|---|---|
| SC | size, class/PN, thk, material, facing, std | thk(3), facing(RF), std | material |
| SPW | size, class, thk, winding, filler, OR, std | thk(4.5), filler(graphite), OR(CS), IR(mandate rule), std | winding |
| RTJ | ring no, shape, material, BHN, std | ring no(lookup), shape(OCT), BHN(table), std(type rule) | material; ring no if lookup fails |
| KAMM | dims/size, total+core thk, core mat, layers, std/drawing | thk(4.5 std flange), layers(graphite) | dims (HX), rib |
| DJI | OD, ID, thk, jacket, filler | filler(graphite for metal jackets) | rib, drawing |
| ISK | size, class, style/construction, fire status, facing | fire status(logic), facing(type) | construction if novel |

## D2. Cross-checks (deterministic layer)
1. BX ⇒ standard = API 6A. RX ⇒ API 6B + NACE line. R + ASME class ⇒ B16.20.
2. SPW ⇒ standard ≠ API. PTFE filler ⇒ inner ring present. Class/size ⇒ IR mandate.
3. Size ≥26" ⇒ B16.47 in standard slot (SC/SPW/KAMM/RTJ).
4. DN/NB ⇒ no `"` anywhere in size block.
5. OD > ID in every W3 string.
6. KAMM W3 ⇒ has `({core}MM CORE THK)`.
7. ISK ⇒ ends with (FIRE SAFE) or (NON FIRE SAFE)/(NON-FIRE SAFE).
8. RTJ ⇒ has `{x} BHN HARDNESS`.
9. Class exists for size (A2 gaps) — else flag.
10. Drawing ref in input ⇒ `(AS PER DRAWING)` in output.

## D3. Escalation phrases (exact strings)
`WILL QUOTE SOON` | `KINDLY PROVIDE RING NO` | `AS PER ASME STANDARD RING NUMBER IS NOT AVAILABLE SO KINDLY PROVIDE DIMENSIONS` | `KINDLY PROVIDE DRAWING` | `KINDLY PROVIDE DRAWING WITH DIMENSION` | `KINDLY PROVIDE CLEAR SPEC` | `KINDLY PROVIDE DATASHEET / DETAILED MATERIAL DESCRIPTION` | `KINDLY CONFIRM RIB DETAILS` (note, alongside quote) | `REGRET`

═══════════════════════════════════════════════════════════════════
# PART E — EXTRACTION SCHEMA & PIPELINE (unchanged architecture)
═══════════════════════════════════════════════════════════════════

JSON schema per v2 STEP 2 (+ `size_world: "W1|W2|W3"`, `form: "RING|FF|SHEET|OBROUND|RECT"`, `pass_bars: null|int`).

Pipeline: pre-parse (v2 STEP 0) → LLM classify+extract JSON → deterministic engine: size-world detect → product chapter rules → lookups (rings/hardness/IR-mandate/standards) → template assembly → D2 cross-checks → verify pass → output or human queue. FEEDBACK sheet = permanent regression suite.

## Future-proofing checklist (when new cases arrive)
- New material → add alias row to Material Master; hardness row if RTJ-capable.
- New standard (EN 12560, JIS, GOST, AS, SANS) → add to A2 matrix; keep customer std verbatim meanwhile.
- New product family (lens, lip seal, diaphragm, plug, corrugated metal, O-ring already templated in v2 3.17) → new chapter with: keywords, construction, W1/W2/W3 templates, mandatory fields, cross-checks.
- New ISK brand name → map to nearest STYLE (N/CS/FCS) via construction described, not brand.
- Every human correction → FEEDBACK row → regression test.
