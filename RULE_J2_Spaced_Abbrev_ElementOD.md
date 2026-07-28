# RULE J-2 — SPACED ABBREVIATIONS & THE ELEMENT-vs-OVERALL OD/ID CHECK
### GGPL Enquiry Bot · Hostile Input Handling · Refinement to Rules J (compact notation) and SPW-9 (equipment SPW)

> Derived from a real heat-exchanger RFQ: 12 rows of "SS304 S P W D WITH SS INNER AND
> OUTER RING", OD/ID in mm up to 2.1 metres, no class, no drawing. Everything resolved
> through existing rules except two gaps: the SPACED-OUT abbreviation "S P W D", and a
> 26mm manufacturing ambiguity — are the stated OD/ID the sealing element or the
> overall gasket over the rings?

---

## PART 1 — SPACE-TOLERANT ABBREVIATION MATCHING (extends Rule J-c)

### DETECT
Product/component abbreviations broken by spaces or periods — a common artifact of
manual typing, OCR, and PDF text extraction:

| Written | Means |
|---|---|
| `S P W D` / `S.P.W.D` / `S P W` / `SP WD` | SPIRAL WOUND (SPWD/SPW) |
| `S W G` / `S.W.G` | SPIRAL WOUND GASKET |
| `R T J` / `R.T.J` | RTJ |
| `C N A F` / `C.N.A.F` | CNAF |
| `I R` / `O R` / `C R` (standalone pairs) | INNER / OUTER / CENTERING RING (Rule J-a roles) |
| `D J` / `M C R` | DOUBLE JACKETED / manhole spiral style |
| `F F` / `R F` (in facing position) | FF / RF |

### DO
- Normalize by collapsing single spaces/periods **between single letters** before the
  abbreviation lexicon runs: `S P W D` → `SPWD` → SPIRAL WOUND.
- Guard: collapse ONLY letter-by-letter runs (2–5 single letters). Never collapse
  across real words — `SS INNER` stays two tokens; `4 MM` stays a dimension.
- After normalization, all existing Rule J mappings apply unchanged.

---

## PART 2 — ELEMENT-vs-OVERALL OD/ID CONFIRMATION (extends SPW-9 / W3)

### DETECT
A ringed spiral wound gasket (inner and/or outer ring stated) quoted by **bare OD/ID
dimensions with NO drawing reference** — typical of heat-exchanger and equipment SPW
RFQs (W3 world: mm dims, no flange class).

### THE AMBIGUITY (why this is a mandatory flag, not pedantry)
For a ringed SPW, "OD" and "ID" can mean two different parts:

```
        |<------------- OVERALL OD (over outer ring) ------------->|
        |    |<-------- SEALING ELEMENT OD ------------->|         |
   [OUTER RING][ WINDING / SEALING ELEMENT ][INNER RING]
        |    |<-- ELEMENT ID -->|                        |
        |<-- OVERALL ID (inner ring bore) -->|
```

- Ring radial widths are typically 10–15mm each side → the two readings differ by
  **20–30mm on both OD and ID**.
- On a 2-metre exchanger gasket that is the difference between a gasket that fits
  and one that is scrap. There is no safe default — the reading changes the
  manufactured part, so fidelity law 6 (no guessed construction) applies.

### DO
1. Quote the line normally (SPW-9 / W3 template) using the dims **as stated**.
2. Attach ONE mandatory confirmation flag per enquiry (not per row):

```
FLAG: KINDLY CONFIRM — STATED OD/ID ARE SEALING ELEMENT DIMS OR OVERALL DIMS
(OVER INNER/OUTER RINGS)? CRITICAL AT THESE DIAMETERS — CHANGES MANUFACTURING DIMS.
```

3. Release gate: like DIM PENDING (Rule K-2), the quote may issue but the ORDER
   must not proceed to manufacturing while this flag is unresolved.
4. Exception — flag NOT needed when: a drawing is referenced (drawing governs,
   Rule K), or the text itself disambiguates ("winding OD", "overall OD",
   "gasket OD over centering ring").

### SUPPORTING COHERENCE CHECK (advisory, not blocking)
Compute radial width = (OD − ID) / 2 per row and sanity-check against thickness:
- 4.5MM THK on ~13MM width, 6.35MM (1/4") THK on ~19MM width at metre-plus
  diameters = coherent HX practice → pass silently.
- Width under ~8MM at large diameter, or THK > width, or width wildly inconsistent
  within an otherwise identical family → add a verify note (possible typo in OD/ID).

---

## WORKED EXAMPLE (condensed from the source RFQ)

```
IN : GASKET | SS304 S P W D WITH SS INNER AND OUTER RING | 4.5 | 2126 | 2100 | 2
     (12 rows total: SS304 x8, SS316 x4; THK 4.5/6.35; duplicate-dim rows split by qty)

OUT (pattern):
SIZE: 2126MM OD X 2100MM ID X 4.5MM THK, SS304 SPIRAL WOUND GASKET WITH GRAPHITE
FILLER + SS304 INNER RING & SS304 OUTER RING (NON STANDARD)     [QTY 2]

DEV : FILLER NOT STATED — GRAPHITE APPLIED (GGPL STD) · RINGS "SS" = WINDING GRADE
FLAG: KINDLY CONFIRM — OD/ID = SEALING ELEMENT OR OVERALL (OVER RINGS)?
CHECK: 12 lines · qty 14 · SS304 x8 / SS316 x4 · quote-sheet mode (PRICE column),
       "at the earliest" -> URGENT commercial flag
```

Notes applied from existing rules: duplicate-dim rows quoted separately (Rule H);
bare "SS" rings = winding grade (Rule B winding-inference sibling); no drawing
mentioned → no Rule K alert, no (AS PER DRAWING).

---

## FAILURE MODES THIS RULE PREVENTS

1. "S P W D" unrecognized → 12 rows misclassified or escalated as unclear spec.
2. A 2.1-metre gasket manufactured 26mm wrong because element-vs-overall was assumed.
3. Duplicate-dimension rows merged, breaking the customer's tag/exchanger split.
4. Letter-collapse over-firing and mangling real words or dimensions (the guard).

---

## VALIDATION ADDITIONS (extend Section 7.2 checklist)

- **27.** Letter-by-letter abbreviation runs normalized before lexicon matching;
  collapse applied only to 2–5 single-letter sequences.
- **28.** Ringed SPW quoted by bare OD/ID without a drawing ⇒ element-vs-overall
  confirmation flag present; order release blocked until resolved.

## REGRESSION FIXTURE (add to Section 8)

| Fixture | Tests | Must produce |
|---|---|---|
| 12-row "S P W D" HX table | J-2: spaced-abbreviation collapse, W3 no-class SPW, rings = winding grade, duplicate rows unmerged, element-vs-overall flag, width/THK coherence, urgent quote-sheet flags | 12 (NON STANDARD) SPW lines with graphite default logged; ONE element-vs-overall flag; check line "12 lines · qty 14" |
