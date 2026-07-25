# GGPL MASTER SPEC v3.1 SUPPLEMENT — BEYOND THE SIX FAMILIES
## Sheets, O-Rings, Plug, Lens, Lip Seal, Diaphragm, Corrugated, Manhole/Handhole, Envelope, Metal Clad, Solid Metal & Adjacent Products

> Extends the v3 Master Spec with chapters B7–B17. These are the products your UNIQUE REQUIREMENT sheet flagged as missing (SHEETS, PLUG GASKET, CORRUGATED, LIP SEAL, DIAPHRAGM GASKET, LENSE GASKET) plus every other out-of-family item found in your enquiry data or likely to arrive. Insert these into the classifier BEFORE the Soft Cut fallback (SC is the catch-all, so named specialty products must be caught first).

## UPDATED CLASSIFIER PRIORITY (replaces v3 STEP 1)

1. ISK → 2. RTJ → 3. **LENS GASKET** → 4. **O-RING / CORD** → 5. DJI → 6. KAMM (incl. PROFILE GASKET) → 7. SPW (incl. MC/MCR manhole spiral) → 8. **CORRUGATED METAL (CMG)** → 9. **MANHOLE / HANDHOLE / BOILER** → 10. **ENVELOPE GASKET** → 11. **METAL CLAD** → 12. **SOLID METAL FLAT** → 13. **PLUG GASKET** → 14. **LIP SEAL** → 15. **DIAPHRAGM** → 16. **EYELET GASKET** → 17. **SHEET / ROLL** → 18. SC (catch-all flat gaskets) → 19. **ADJACENT/REGRET list**

═══════════════════════════════════════════════

## B7 — SHEETS & ROLLS (raw material supply)

**Detect:** "sheet", "roll", LENGTH × WIDTH dims with no flange size, "per sq mtr", jointing sheet.
**Materials:** CNAF (grades AP-601, WR-57, etc. verbatim), rubber (EPDM/NBR/CR/SBR/silicone/viton, shore hardness kept), PTFE / expanded PTFE, graphite (plain, SS316 foil/tanged insert, wire mesh reinforced), cork, mica, ceramic paper, vermiculite.
**Fields:** length, width, thickness, material+grade, quantity (sheets vs sq.mtr), insert type for graphite.
**Templates:**
- `SIZE: {L}MM LENGTH X {W}MM WIDTH X {t}MM THK, {MATERIAL} SHEET`
- Metre form: `SIZE: {x}MTR LENGTH X {x}MTR WIDTH X {t}MM THK, {MATERIAL} SHEET`
- Graphite w/ insert: `..., GRAPHITE SHEET WITH SS316 TANGED INSERT` / `...WITH SS316 FOIL INSERT`
- Roll: `SIZE: {L}MTR LENGTH X {W}MM WIDTH X {t}MM THK, {MATERIAL} ROLL`
**Standard sheet sizes to recognize:** 1000×1000, 1500×1500, 2000×1500, 1270×1270 (CNAF market standards) — never force; quote as given.
**Escalate:** grade unclear → `KINDLY PROVIDE DATASHEET / DETAILED MATERIAL DESCRIPTION`.

## B8 — O-RINGS, CORDS & MOLDED RUBBER

**Detect:** "O-RING"/"O RING" as product, "cord", "quad ring", elastomer + ID×CS dims, AS568/BS/metric dash numbers.
**Materials:** VITON/FKM, SILICONE (fix "SILICON"), EPDM, NBR/NITRILE, HNBR, NEOPRENE, PTFE, FFKM/KALREZ-type (verbatim), PU.
**Templates:**
- `SIZE: {ID}MM ID X {CS}MM THK, {MATERIAL} O-RING`
- With OD: `SIZE: {OD}MM OD X {ID}MM ID X {CS}MM THK, {MATERIAL} O-RING`
- Qualifiers kept: `HIGH PRESSURE`, `PTFE ENCAPSULATED {core} O-RING`, shore hardness (`VITON 75 SHORE A O-RING`), standard dash no. (`AS568-236, VITON O-RING`)
- Cord: `SIZE: {CS}MM CS X {L}MTR LENGTH, {MATERIAL} O-RING CORD`
**Drop:** pressure rating bars, "TYPE: FLAT" noise. **ISO 3601** may be cited if customer does.
**Escalate:** molded custom profiles without drawing → `KINDLY PROVIDE DRAWING`.

## B9 — LENS GASKET (LENS RING) — DIN 2696

**Detect:** "lens gasket", "lens ring", "lenticular", spherical seat, conical flange face, high-pressure line joint.
**Facts:** metallic line-contact seal with spherical faces for conical-faced high-pressure flanges; governed by DIN 2696 (range ≈ DN10 PN63 to DN300 PN400); material must be softer than flange; drawings + full material spec normally required for anything non-DIN.
**Materials:** soft iron, LCS, SS304/316/316L/321/347, F5/F11, copper, aluminium, Monel 400, Inconel 600/625, Incoloy 800/825, titanium, Hastelloy.
**Templates:**
- DIN standard: `SIZE: DN{x} X PN{x}, LENS RING GASKET, {MATERIAL}, DIN 2696`
- Non-standard: `SIZE: {OD}MM OD X {ID}MM ID X {H}MM, LENS RING GASKET, {MATERIAL} (AS PER DRAWING)`
**Escalate:** no DN/PN and no drawing → `KINDLY PROVIDE DRAWING WITH DIMENSION`. Hardness note optional (softer than flange) — include BHN only if customer specifies.

## B10 — LIP SEAL

**Detect:** "lip seal", "PTFE lip seal", "rotary seal", "oil seal", "shaft seal", "with lip" shape notes on jacketed items.
**Two meanings — disambiguate:**
a) **PTFE/elastomer lip seals** (rotary/static, glass-lined reactor flange lip seals) → product
b) **"...WITH LIP" as a shape** on DJ/soft gaskets → stays in that family, append `WITH LIP` to shape (see DJI example: `SHAPE: ROUND WITH LIP`)
**Templates:**
- `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, {PTFE|VITON|NBR} LIP SEAL (AS PER DRAWING)`
- Reactor flange: `SIZE: DN{x}, PTFE LIP SEAL FOR GLASS LINED FLANGE (AS PER DRAWING)`
- Spring-energized: `..., PTFE SPRING ENERGISED LIP SEAL...`
**Escalate:** shaft seals with metal case (SKF-type oil seals) are usually bought-out items → check make-or-buy; default `WILL QUOTE SOON` if dims complete, `KINDLY PROVIDE DRAWING` if not.

## B11 — DIAPHRAGM GASKET / DIAPHRAGMS

**Detect:** "diaphragm", "diaphram", valve/actuator/pump diaphragm, rubber-fabric disc.
**Materials:** EPDM, NBR, VITON, SILICONE, PTFE, PTFE-faced EPDM, rubber with fabric (nylon/polyester) reinforcement.
**Templates:**
- `SIZE: {OD}MM OD X {t}MM THK, {MATERIAL} DIAPHRAGM (AS PER DRAWING)`
- Faced: `..., PTFE FACED EPDM DIAPHRAGM WITH FABRIC REINFORCEMENT (AS PER DRAWING)`
- With bolt-hole/convolution detail → drawing mandatory.
**Escalate:** convoluted/molded diaphragms are tooling items → `KINDLY PROVIDE DRAWING`; valve make/model alone (no dims) → `KINDLY PROVIDE DRAWING WITH DIMENSION`.

## B12 — CORRUGATED METAL GASKET (CMG)

**Detect:** "corrugated gasket", "corrugated metal", "CMG", "corrugated with graphite facing/layers" — NOT "corrugated type filler" inside a DJ description (that stays DJI).
**Facts:** thin corrugated metal core (0.5–0.8MM typ.) with soft facing layers (flexible graphite standard, PTFE optional); low-seating-stress alternative to DJ for heat exchangers; also plain corrugated metal (no facing) legacy style.
**Materials:** core SS304/316/316L/Monel/Inconel; facing graphite/PTFE.
**Templates:**
- W1: `SIZE: {x}" X {ppp}# X {t}MM THK, {CORE} CORRUGATED METAL GASKET WITH GRAPHITE FACING LAYERS, ASME B16.20` (house style: cite customer's standard; B16.20 covers jacketed/grooved — CMG often mfr standard, keep customer's)
- W3: `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, {CORE} CORRUGATED METAL GASKET WITH GRAPHITE FACING LAYERS[ (AS PER DRAWING)]`
- Plain (no facing): `..., {MATERIAL} CORRUGATED METAL GASKET (PLAIN)`
**Note:** "GACLI"/legacy corrugated CAF names in your master → map to CORRUGATED METAL GASKET WITH {facing}.

## B13 — MANHOLE / HANDHOLE / BOILER GASKETS (obround family)

**Detect:** "manhole", "handhole", "boiler gasket", "obround", "elliptical", "oval" + tank/boiler context, "tube cap", "MC"/"MCR" style.
**Facts:** manhole-cover gaskets come round/obround/oval; spiral-wound MC (winding only) and MCR (with centering ring) styles exist for manhole covers, and boiler handhole/tube-cap services use square/rectangular/diamond/obround/pear shapes; graphite obround gaskets are a common alternative to spiral wound. When ordering, boiler make/model, style, and full dims matter.
**Templates:**
- Obround soft/graphite: `SIZE: {A}MM X {B}MM OBROUND X {t}MM THK, {MATERIAL} MANHOLE GASKET` (A×B = across the two axes; add `{W}MM SEAT WIDTH` if given)
- Spiral MC/MCR: `SIZE: {A}MM X {B}MM OBROUND, {WINDING} SPIRAL WOUND MANHOLE GASKET (STYLE {MC|MCR}) WITH {FILLER} FILLER[ + {OR} CENTERING RING]`
- Rubber manhole (tank): `SIZE: {A}MM X {B}MM X {t}MM THK, {MATERIAL} MANHOLE GASKET (AS PER DRAWING)`
**Escalate:** shape unclear or taper/lip seats → `KINDLY PROVIDE DRAWING`; boiler make/model only → `KINDLY PROVIDE DRAWING WITH DIMENSION`.

## B14 — ENVELOPE GASKET (PTFE ENVELOPE)

**Detect:** "envelope gasket", "PTFE envelope", "TEC gasket", "insert gasket PTFE jacketed" (soft insert in PTFE jacket — NOT metal DJ).
**Construction:** machined/slit PTFE envelope (V-slit, milled, or form-machined) with CNAF / rubber / corrugated-metal insert.
**Templates:**
- W1: `SIZE: {x}" X {ppp}# X {t}MM THK, PTFE ENVELOPE GASKET WITH {CNAF|EPDM|CORRUGATED SS316} INSERT, ASME B16.21`
- W2: `SIZE: {x} DN X PN{x} X {t}MM THK, PTFE ENVELOPE GASKET WITH {INSERT} INSERT, EN 1514-3`
- (EN 1514-3 is the PTFE-envelope gasket standard — use when customer is in DN/PN world and cites EN; else B16.21/customer std.)

## B15 — METAL CLAD / MC PLATE GASKETS

**Detect:** "metal clad", "metal cladded", partial jacket, "clad gasket" — single-side or edge-clad soft core (vs full double jacket = DJI).
**Template:** `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, {METAL} CLAD GASKET WITH {FILLER} CORE[ (AS PER DRAWING)]`
**If ambiguous with DJI:** full enclosure described → DJI; "clad one side"/"edge clad" → METAL CLAD; unknown → quote DJI + note.

## B16 — SOLID METAL FLAT RING

**Detect:** "solid metal gasket", "metal flat ring", "SS316 flat ring gasket" with no filler/facing, tongue-groove or male-female flange gaskets.
**Template:**
- `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, SOLID {MATERIAL} FLAT RING GASKET[ (AS PER DRAWING)]`
- W1 flange: `SIZE: {x}" X {ppp}# X {t}MM THK, SOLID {MATERIAL} FLAT RING GASKET` — add `{x} BHN HARDNESS` if customer specifies hardness (common for solid metal).
**Note:** tongue & groove / M-F facings change gasket OD/ID vs RF — if facing stated as T&G or M&F, dims come from customer or drawing; don't apply RF tables.

## B17 — PLUG GASKET

**Detect:** "plug gasket", "plug seal", HX shoulder-plug gasket, boiler plug, "test plug gasket".
**Reality:** small solid-metal, graphite, or soft washers/rings sealing threaded or shoulder plugs (heat-exchanger channel plugs, boiler plugs). Almost always W3 (dims) or drawing.
**Templates:**
- `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, {MATERIAL} PLUG GASKET`
- With shoulder/step profile: `..., {MATERIAL} PLUG GASKET (AS PER DRAWING)`
- Graphite plug ring: `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, GRAPHITE PLUG GASKET`
**Escalate:** thread size only (e.g. "1/2 NPT plug gasket") → `KINDLY PROVIDE DIMENSIONS / DRAWING`.

## B18 — EYELET GASKET

**Detect:** "eyelet", "eyeletted", "inner eyelet", metal-eyeleted CNAF/graphite.
**Template:** `SIZE: {OD}MM OD X {ID}MM ID X {t}MM THK, {CNAF|GRAPHITE} GASKET WITH {SS316|SS304|COPPER} INNER EYELET[ (AS PER DRAWING)]`
W1 flange form allowed: `SIZE: {x}" X {ppp}# X {t}MM THK, CNAF GASKET WITH SS316 INNER EYELET, ASME B16.21`.

═══════════════════════════════════════════════

## B19 — ADJACENT PRODUCTS DECISION LIST (quote / verify / REGRET)

| Item in enquiry | Action |
|---|---|
| Gland packing / braided packing (graphite, PTFE, aramid) | CONFIGURABLE — quote if GGPL stocks (`SIZE: {x}MM SQ X {L}MTR, {MATERIAL} BRAIDED GLAND PACKING`), else `REGRET` |
| Graphite tape / joint sealant | same as packing — configurable |
| Spectacle blind / spade & spacer / paddle blank | piping component, not gasket → `REGRET` (or forward to trading team) |
| Stud bolts / nuts / washers alone | `REGRET` unless part of ISK set |
| Expansion joint / bellows | `REGRET` |
| Camlock / hose seals | quote as O-RING/soft washer if dims given, else `REGRET` |
| Valve seat / seals (PTFE seats) | `WILL QUOTE SOON` if drawing, else `KINDLY PROVIDE DRAWING` |
| Insulation (thermal) material, cloth, rope | `REGRET` unless GGPL trades it |
| Heat exchanger FULL gasket set ("gasket set for AEL exchanger") | decompose into KAMM/DJI/SC line items per drawing → `KINDLY PROVIDE DRAWING` if none |
| "IDK"/illegible/garbage rows | `KINDLY PROVIDE CLEAR SPEC` |

*(Set each CONFIGURABLE row once with sales team; the bot then applies it consistently.)*

## VALIDATION ADDITIONS (extend v3 Part D2)

11. LENS ⇒ DIN 2696 (or drawing) in standard slot; DN/PN or dims present.
12. O-RING ⇒ no flange class in output; ID before THK; OD (if any) first.
13. OBROUND ⇒ two axis dims present.
14. ENVELOPE ⇒ insert material stated.
15. CMG vs DJI: "corrugated type ... filler" inside DJ text ⇒ DJI, standalone "corrugated gasket" ⇒ CMG.
16. LIP: "with lip" as shape ⇒ parent family + WITH LIP; "lip seal" as noun ⇒ B10.
17. Any B7–B18 product without dims AND without ASME/EN size-class ⇒ escalation, never a guessed size.

## FEW-SHOT ADDITIONS

```
IN : GASKET, JACKETED; TYPE: RF, STYLE: ROUND, JACKET MATERIAL: TEFLON, FILLER MATERIAL: RUBBER, SIZE: ID 54 X OD 153 X THK 3.0 MM, SHAPE: ROUND WITH LIP
OUT: SIZE: 153MM OD X 54MM ID X 3MM THK, RUBBER FILLED PTFE DOUBLE JACKETED GASKET, ROUND WITH LIP, RF   [DJI + lip shape]

IN : PTFE envelope gasket with CNAF insert, DN80 PN16, 3mm
OUT: SIZE: 80 DN X PN16 X 3MM THK, PTFE ENVELOPE GASKET WITH CNAF INSERT, EN 1514-3

IN : Lens ring DN50 PN250 material 1.4571
OUT: SIZE: DN50 X PN250, LENS RING GASKET, SS316TI, DIN 2696

IN : Boiler manhole gasket 300 x 400 obround, graphite, 6mm thick
OUT: SIZE: 400MM X 300MM OBROUND X 6MM THK, GRAPHITE MANHOLE GASKET

IN : corrugated gasket SS316 with graphite layers, 8" 150#
OUT: SIZE: 8" X 150# X 3MM THK, SS316 CORRUGATED METAL GASKET WITH GRAPHITE FACING LAYERS

IN : Plug gasket for exchanger channel plug, OD 42 ID 33 x 2mm soft iron
OUT: SIZE: 42MM OD X 33MM ID X 2MM THK, SOFT IRON PLUG GASKET

IN : EPDM diaphragm for actuator, OD 220, fabric reinforced — drawing attached
OUT: SIZE: 220MM OD, EPDM DIAPHRAGM WITH FABRIC REINFORCEMENT (AS PER DRAWING)

IN : Spectacle blind 6" 300# SS316
OUT: REGRET

IN : Gland packing graphite 12mm x 8 mtr
OUT: [configurable] SIZE: 12MM SQ X 8MTR, GRAPHITE BRAIDED GLAND PACKING  — or REGRET per policy
```
