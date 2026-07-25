# GGPL MASTER SPEC v3.2 SUPPLEMENT — BRAND & TRADE-NAME CROSS-REFERENCE
## "Gaskets with different names": competitor styles, trade names, synonyms → GGPL descriptions

> Customers often specify a COMPETITOR BRAND or STYLE CODE instead of a generic construction ("Flexitallic CGI", "Klingersil C-4400", "Pikotek VCS", "Kroll & Ziller"). This dictionary tells the bot exactly what construction each name means and how to write the GGPL line. Verified against manufacturer interchange charts and datasheets.

═══════════════════════════════════════════════
# 0. THE BRAND-HANDLING POLICY (three buckets)

**Bucket 1 — STYLE CODES (construction in disguise).** Brand style codes like CGI, RWI, WRI just describe a construction (winding + rings). → TRANSLATE to the normal GGPL template. Do NOT keep the brand code in the description. Optionally note in deviation field: `EQUIVALENT TO {BRAND} STYLE {CODE}`.

**Bucket 2 — MATERIAL TRADE NAMES (grade in disguise).** Klingersil C-4400, Durlon 8500, Grafoil, Viton, Gylon. → TRANSLATE to generic material + keep the certification grade (BS7531 GR X/Y). Deviation note: `GGPL EQUIVALENT TO {BRAND GRADE}` — because GGPL supplies its own make, this note protects against "you quoted the wrong brand" disputes.

**Bucket 3 — PRODUCT-IDENTITY BRANDS (the brand IS the spec).** Kroll & Ziller (G-ST-P/S), unique patented constructions. → KEEP VERBATIM in the GGPL string (your house rule: "we take exact what customer says"). Applies when there is no meaningful generic name.

**Universal rule:** never silently substitute. If customer says "Pikotek VCS or equivalent" → quote GGPL STYLE-CS. If customer says "Pikotek VCS only, no equivalent" → quote + deviation `CUSTOMER SPECIFIES PIKOTEK MAKE — GGPL OFFERING EQUIVALENT STYLE-CS` and flag for sales review.

═══════════════════════════════════════════════
# 1. SPIRAL WOUND — STYLE CODE INTERCHANGE (Bucket 1)

Construction → brand codes (any of these words in an enquiry = that construction):

| Construction | Flexitallic | Garlock | Lamons | Teadit | Klinger | GRI | Leader | GGPL output |
|---|---|---|---|---|---|---|---|---|
| Winding only (no rings) | **R** | **SW** | **W** | 911 | R (Maxiflex) | D | S | `{WINDING} SPIRAL WOUND GASKET WITH {FILLER} FILLER (WINDING ONLY)` — for T&G / M-F / grooved flanges |
| Winding + OUTER ring | **CG** | **RW** | **WR** | 913 | CR | DR | SR | standard template, OR only |
| Winding + OUTER + INNER | **CGI** | **RWI** | **WRI** | 913M | CRIR | DRI | SRI | standard template, IR + OR |
| Winding + INNER ring only | RIR | RIR | WI | — | — | — | — | `...WITH {FILLER} FILLER + {IR} INNER RING` (no OR; grooves/recesses) |
| Heat-exchanger limited-width | HX-RIR | — | — | — | — | — | — | W3 dims + IR, `(AS PER DRAWING)` |
| Low seating stress | LS / LSI | Flexseal LE | WRI-LC / WRI-LE | 913M-LE | CRIR-LE | — | HDLE | standard template + `(LOW STRESS)` |
| SPW for RTJ groove | CG-RJ / CGI-RJ | — | WR-RJ / WRI-RJ | — | — | — | — | standard SPW template + note `TO SUIT RTJ GROOVE (AS PER DRAWING)` |
| Anti-buckling outer | — | EDGE / STABL-LOCK | WR-AB | — | — | — | — | standard WR construction + deviation note |

**Other SPW trade names:** Spirotallic, Spiraseal, Metaflex (Klinger METALFLEX), Flexseal (Garlock) → all = SPIRAL WOUND GASKET; parse construction from context; default CGI-equivalent (IR+OR) if unstated at class ≥600 or PTFE filler (B16.20 mandate), else CG-equivalent.

═══════════════════════════════════════════════
# 2. SHEET / SOFT-CUT MATERIAL TRADE NAMES (Bucket 2)

| Brand grade | Generic construction | GGPL material string |
|---|---|---|
| **Klingersil C-4400** | aramid fibre + NBR binder, BS7531 **Grade Y** | `CNAF (ARAMID FIBRE WITH NBR BINDER) BS7531 GR Y` |
| **Klingersil C-4430** | glass+synthetic fibre + NBR, BS7531 **Grade X** | `CNAF (GLASS/SYNTHETIC FIBRE WITH NBR BINDER) BS7531 GR X` |
| Klingersil C-4500 | carbon fibre + NBR (high temp) | `CNAF (CARBON FIBRE WITH NBR BINDER)` |
| Klingersil C-8200 | PTFE bonded aramid (acid service) | `PTFE BONDED CNAF` |
| **Durlon 8500** | aramid/inorganic + NBR (≈ Teadit NA-1090, Thermoseal C-4430 class) | `CNAF` + deviation `EQUIVALENT TO DURLON 8500` |
| Durlon 8300 / 8600 | general service CNAF (8600 = white food grade) | `CNAF` / `CNAF (FOOD GRADE, WHITE)` |
| Durlon 9000 | PTFE with inorganic filler | `FILLED PTFE` |
| **Gylon 3500** (fawn) | PTFE with silica filler | `FILLED PTFE (SILICA FILLED, FAWN)` |
| Gylon 3504 (blue) | PTFE with aluminosilicate/glass microspheres | `FILLED PTFE (GLASS MICROSPHERE, BLUE)` |
| Gylon 3510 (off-white) | PTFE with barium sulphate | `FILLED PTFE (BARIUM SULPHATE, OFF-WHITE)` |
| Garlock Blue-Gard 3000 | aramid + NBR CNAF | `CNAF` |
| Garlock IFG / Graph-Lock | inorganic fibre / graphite laminate | `CNAF (INORGANIC FIBRE)` / `GRAPHITE SHEET WITH SS INSERT` |
| Teadit NA-1002/1076/1090 | CNAF grades | `CNAF` + grade in deviation |
| **Grafoil** (GrafTech GT/GHR/GHE) | flexible graphite sheet | `FLEXIBLE GRAPHITE SHEET` (+ insert if grade says) |
| **Sigraflex** (SGL) | flexible graphite (foil/laminate, SS insert grades) | `FLEXIBLE GRAPHITE SHEET [WITH SS316 FOIL INSERT]` |
| Thermiculite 715 | vermiculite sheet (Flexitallic) | `VERMICULITE SHEET (THERMICULITE 715)` |
| **Thermiculite 835/845/855** | vermiculite SPW/kamm facing fillers | `VERMICULITE FILLER (THERMICULITE {grade})` |
| Novus (Flexitallic) SF2401, Sigma 500/511 | CNAF / PTFE sheet lines | map: Novus→CNAF, Sigma→FILLED PTFE |
| Gore GR / Gore Universal Pipe Gasket | expanded PTFE (ePTFE) | `EXPANDED PTFE (ePTFE)` |
| Tealon TF1570/1580/1590 | filled PTFE (Teadit/DuPont system) | `FILLED PTFE` + colour/grade note |
| Millboard / IT sheet (legacy) | old asbestos-era terms | `KINDLY PROVIDE CLEAR SPEC` + offer CNAF |
| **CAF** (Compressed Asbestos Fibre) | asbestos — banned/legacy | quote `CNAF` + deviation `CAF REQUESTED — GGPL OFFERS NON-ASBESTOS (CNAF) EQUIVALENT` |

═══════════════════════════════════════════════
# 3. RUBBER / POLYMER TRADE NAMES (Bucket 2 — auto-translate)

| Trade name | Polymer | GGPL string |
|---|---|---|
| **Viton** (DuPont/Chemours) | FKM fluoroelastomer | `VITON (FKM)` — Viton is industry-accepted, keep |
| Teflon | PTFE | `PTFE` |
| Buna-N / Perbunan | NBR nitrile | `NITRILE (NBR)` |
| Neoprene | CR chloroprene | `NEOPRENE (CR)` |
| Hypalon | CSM | `CSM (HYPALON)` |
| Kalrez / Chemraz / Perlast | FFKM perfluoroelastomer | `FFKM` + brand in deviation (premium — flag price) |
| Aflas | FEPM/TFE-P | `AFLAS (FEPM)` |
| Santoprene | TPV | `TPV (SANTOPRENE)` |
| EPDM Nordel | EPDM | `EPDM` |
| Silicon(e) / VMQ | silicone | `SILICONE` |
| Natural rubber / NR / gum rubber | NR | `NATURAL RUBBER` |

═══════════════════════════════════════════════
# 4. ISK / ISOLATION BRAND NAMES → GGPL STYLE (Bucket 1)

| Brand product | Construction | GGPL style |
|---|---|---|
| **Pikotek VCS** (GPT) | G10/G11 laminate on SS core + PTFE spring-energized seal | **STYLE-CS** |
| **Pikotek VCFS** | VCS + secondary seal, fire-tested (API 6FB) | **STYLE-FCS ... (FIRE SAFE)** |
| Pikotek PGE | low-pressure GRE retainer kit | **STYLE-N** |
| **PGS Commander / Commander Extreme** | same class as VCS (PTFE spring-energized, metal core) | **STYLE-CS** |
| GPT LineBacker (G-10/G-11, O-ring or spring-energized) | GRE retainer + seal groove kit | STYLE-N (seal type per enquiry) |
| Flexitallic ISOFLEX-LT / ISOPRO-IP | GRE ring + soft seal element | STYLE-N |
| Flexitallic ISOPRO-NFP | phenolic core + nitrile facings | TYPE "E"/plain kit, NEOPRENE/NITRILE FACED PHENOLIC |
| Flexitallic I-Flex Fire-Safe | fire-safe isolation | STYLE-FCS (FIRE SAFE) |
| Lamons IsoGuard / DefendR | GRE isolation kits | map per construction described |
| Advance/Cathodic "FIK" phrases | generic kit | plain kit template |
| VCXT (high temp) | high-temp isolation set | `WILL QUOTE SOON` (novel construction — sales review) |

Rule: brand alone without construction → map per table; brand + construction details → construction wins.

═══════════════════════════════════════════════
# 5. KAMM / DJ / RTJ / CMG BRAND NAMES

| Brand | Product | GGPL |
|---|---|---|
| Flexitallic **FLEXPRO** | kammprofile | KAMMPROFILE template |
| Lamons **Kammpro** | kammprofile | KAMMPROFILE |
| Klinger Maxiprofile | kammprofile | KAMMPROFILE |
| Leader-KAM, Teadit Camprofile (942/941) | kammprofile | KAMMPROFILE |
| Garlock GRAPHONIC | corrugated metal + graphite | CORRUGATED METAL GASKET WITH GRAPHITE FACING LAYERS |
| Lamons CorruKamm / Corrugated | CMG | CMG template |
| Teadit 923/927 | metal jacketed | DJI template |
| "Camprofile", "Grooved gasket", "Serrated gasket", "PROFILE GASKET" | generic synonyms | KAMMPROFILE |
| Black-Max (boiler obround graphite) | manhole/handhole graphite | B13 obround template |
| Style MC / MCR | spiral manhole (winding only / + centering ring) | B13 spiral manhole template |

═══════════════════════════════════════════════
# 6. PRODUCT-IDENTITY BRANDS — KEEP VERBATIM (Bucket 3)

| Brand as spec | GGPL handling |
|---|---|
| **KROLL & ZILLER (G-ST-P/S) WITH SPACER** | verbatim in description (house rule) — `SIZE: {x}" X {ppp}# X {t}MM THK ,KROLLER & ZILLER (G-S-T-P/S) WITH SPACER ,FF ,ASME B16.21` |
| Victaulic coupling gaskets (style 77 etc.) | verbatim + `(AS PER DRAWING)` or REGRET per policy |
| Camlock seals, Storz seals | verbatim + dims |
| Any patented construction with no generic (e.g. "Evolution encapsulated isolating gasket") | verbatim or `WILL QUOTE SOON` |

═══════════════════════════════════════════════
# 7. GENERIC SYNONYMS DICTIONARY (same gasket, different words)

| Customer words | GGPL family/term |
|---|---|
| SWG, spiral, spirally wound, spiral metallic, CGI-type, V-winding | SPW |
| camprofile, kamprofile, grooved metal, serrated metal, PROFILE GASKET, comb profile | KAMM |
| metal jacketed, MJ, jacketed, clad gasket (full), DJ, double shell | DJI |
| ring gasket, RJ, ring joint, API ring, oct ring | RTJ |
| isolation kit, insulation kit, dielectric kit, FIK, flange kit, IJK, insulating set | ISK |
| CNAF, NA sheet, non-asb, synthetic fibre gasket, jointing gasket, fibre gasket | SC (CNAF) |
| it/jointing sheet, packing sheet | SHEET |
| centering ring = guide ring = outer ring; anti-buckling ring = inner ring | ring naming |
| filler = filter (common typo) = soft layer = facing | FILLER |
| PTFE = Teflon = virgin PTFE; ePTFE = expanded PTFE = Gore-type | PTFE |
| flexible graphite = exfoliated = expanded graphite = Grafoil = Sigraflex | GRAPHITE |
| thermiculite = vermiculite = mica-based high temp filler (distinct from MICA sheet) | VERMICULITE |
| SS = CRES = stainless; MS = mild steel = CS; GI = galvanised iron | metals |
| lb = # = class = CL = rating = ANSI class = pound rating | class |
| gland ring, follower ring (context: packing) | B19 adjacent |

═══════════════════════════════════════════════
# 8. OUTPUT & DEVIATION LANGUAGE

- GGPL string: generic construction only (Buckets 1–2), verbatim brand (Bucket 3).
- Deviation column (your quote sheet has one — use it): `GGPL MAKE, EQUIVALENT TO {BRAND} {STYLE/GRADE}` whenever a brand was translated.
- If customer marks brand as MANDATORY / "no equivalent": still produce the GGPL equivalent line + deviation `CUSTOMER SPECIFIES {BRAND} MAKE — OFFERED GGPL EQUIVALENT, SUBJECT TO CUSTOMER APPROVAL` + flag human review.
- CAF/asbestos requests: always CNAF + deviation note (legal/safety).
- Unknown brand name (not in dictionary): do NOT guess construction. Search enquiry text for construction words; if none → `KINDLY PROVIDE DATASHEET / DETAILED MATERIAL DESCRIPTION`. Log the brand for dictionary update.

═══════════════════════════════════════════════
# 9. FEW-SHOT EXAMPLES

```
IN : 4" 300# Flexitallic CGI SS316/graphite gasket ASME B16.20
OUT: SIZE: 4" X 300# X 4.5MM THK,SS316 SPIRAL WOUND GASKET WITH GRAPHITE FILLER + SS316 INNER RING & CS OUTER RING,ASME B16.20
DEV: EQUIVALENT TO FLEXITALLIC STYLE CGI

IN : Gasket spiral wound Lamons WR, 6", CL150, SS304 windings graphite filled
OUT: SIZE: 6" X 150# X 4.5MM THK,SS304 SPIRAL WOUND GASKET WITH GRAPHITE FILLER + CS OUTER RING,ASME B16.20
DEV: EQUIVALENT TO LAMONS STYLE WR (NO INNER RING)

IN : Klingersil C-4400 gasket 2" 150# 1.5mm
OUT: SIZE: 2" X 150# X 1.5MM THK,CNAF (ARAMID FIBRE WITH NBR BINDER) BS7531 GR Y,RF,ASME B16.21
DEV: GGPL MAKE, EQUIVALENT TO KLINGERSIL C-4400

IN : Gasket sheet Grafoil GHR 1000x1000x1.5mm with SS insert
OUT: SIZE: 1000MM LENGTH X 1000MM WIDTH X 1.5MM THK, FLEXIBLE GRAPHITE SHEET WITH SS316 FOIL INSERT
DEV: EQUIVALENT TO GRAFOIL GHR

IN : 6" 600# Pikotek VCFS insulation gasket kit RF
OUT: SIZE: 6" X 600#, INSULATING GASKET KIT, STYLE-FCS (SET: G10/G11 GASKET WITH SS316 CORE, PTFE PRIMARY SEAL, MICA SECONDARY SEAL, GRE G10/G11 WASHER & SLEEVES, HARDENED DIELECTRIC COATED 316 METALLIC WASHER 3MM THK), RF, ASME B16.5 (FIRE SAFE)
DEV: EQUIVALENT TO PIKOTEK VCFS (FIRE SAFE)

IN : CAF gasket 3mm 4" 150#
OUT: SIZE: 4" X 150# X 3MM THK,CNAF,RF,ASME B16.21
DEV: CAF (ASBESTOS) REQUESTED — GGPL OFFERS NON-ASBESTOS (CNAF) EQUIVALENT

IN : NPS 8, Gasket, Kroll & Ziller (G-ST-P/S) with spacer, Cl 150
OUT: SIZE: 8" X 150# X 4.5MM THK ,KROLLER & ZILLER (G-S-T-P/S) WITH SPACER ,FF ,ASME B16.21   [Bucket 3 verbatim]

IN : Gasket Garlock 3000 Blue-Gard, DN100 PN16, 2mm, full face
OUT: SIZE: 100 DN X PN16 X 2MM THK,CNAF,FF,EN 1514-1
DEV: EQUIVALENT TO GARLOCK BLUE-GARD 3000

IN : Kalrez O-ring ID 25 x 3mm
OUT: SIZE: 25MM ID X 3MM THK, FFKM O-RING
DEV: EQUIVALENT TO KALREZ — PREMIUM FFKM, CONFIRM GRADE & PRICE
```

═══════════════════════════════════════════════
# 10. MAINTENANCE RULE
Every new brand encountered → one row added here (brand, construction, GGPL mapping, bucket). The dictionary is data, not code — store as an editable table (Excel/DB) the bot loads at runtime, so sales can extend it without touching the prompt.
