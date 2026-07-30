# RULE X-2 — MULTI-LEVEL (SPANNED) HEADERS & UNIT-BANNER INHERITANCE
### Why "DIMENSION IN MM / WIDTH / THICKNESS / LENGTH" tables lose their dimensions on paste
### GGPL Enquiry Bot · companion to Rule X (Full-Manifest Conversion), Part 2

> **The failure.** An 18-line neoprene BOQ was pasted and the dimensions did not come
> through. The table has a **two-row header**: row 1 carries `SR.NO | MATERIAL DESCRIPTION |
> DIMENSION IN MM (merged across three columns) | QTY`, and row 2 carries the sub-labels
> `WIDTH | TRHICKNESS | LENGTH`. Binding columns from row 1 alone leaves columns 4 and 5
> **unnamed**, so their values (thickness and length) are discarded — and the one column
> that did get a name, `DIMENSION IN MM`, received only the width.

---

## PART 1 — DETECT A MULTI-LEVEL HEADER

Any one of these signals means the header spans more than one row — re-read before parsing:

1. **Category label in row 1** whose value is a group name, not a field name:
   `DIMENSION` · `DIMENSIONS` · `DIMENSION IN MM` · `SIZE` · `DIM (MM)` · `MATERIAL` ·
   `CERTIFICATION` · `PRICE` · `DELIVERY` — followed by a row of field names.
2. **Row 2 holds field names** from the sub-header lexicon: `WIDTH · THICKNESS · LENGTH ·
   OD · ID · THK · CS · HEIGHT · NB · NPS · CLASS · UNIT · NOS`.
3. ★ **Count mismatch (the reliable test):** row 1 names *N* columns but the data rows
   carry *M > N* populated cells. A multi-level header is present. **Never proceed by
   dropping the surplus columns.**
4. Row 1 has blank cells directly beneath a filled cell (the merge remnant after paste),
   or row 2 has blanks under `SR.NO` / `QTY` (which span both header rows).

---

## PART 2 — COMPOSE THE EFFECTIVE HEADER

Build one header per column as `parent > child`, carrying the parent down across the span
and the child up where row 2 is blank:

```
paste:   SR.NO | MATERIAL DESCRIPTION | DIMENSION IN MM |        |        | QTY
              |                       | WIDTH | TRHICKNESS | LENGTH |

becomes: SR.NO
         MATERIAL DESCRIPTION
         DIMENSION IN MM > WIDTH
         DIMENSION IN MM > THICKNESS
         DIMENSION IN MM > LENGTH
         QTY
```

### 2.1 Unit inheritance from the banner
A parent carrying a unit applies it to every child: `DIMENSION IN MM` ⇒ WIDTH, THICKNESS
and LENGTH are all **MM**, even though the cells hold bare numbers with no unit.
Same for `DIMENSION IN INCH` · `WEIGHT (KG)` · `PRICE (USD)`.
But see 2.2 — a unit banner tells you the *unit*, not the *size world*.
Without this the bot has three unitless integers and no way to write `MM THK`.

### 2.2 ★ RAW MM IS NOT NOMINAL BORE — the guard
`DIMENSION IN MM` means these are **physical measurements in millimetres**. They are NOT
DN / NB nominal-bore designations, even when a value coincides with one. In this BOQ the
widths `100`, `400`, `630` are all real DN sizes — read as bore, item 1 becomes "NB 100"
and gets quoted as a 4" flange gasket instead of a 100 MM wide strip.

**Six tests — any single YES means raw MM:**

| # | Test | This BOQ |
|---|---|---|
| 1 | Banner is a *measurement* label (`DIMENSION IN MM`, `DIM (MM)`, `SIZE IN MM`) rather than a bore label (`NB`, `DN`, `NPS`, `A` for JIS) | `DIMENSION IN MM` → raw MM |
| 2 | Sub-headers name geometry: WIDTH · THICKNESS · LENGTH · OD · ID · HEIGHT. **A bore designation never has a THICKNESS companion inside the same dimension group** | WIDTH/THICKNESS/LENGTH → raw MM |
| 3 | **Three** dimensions present (W×T×L or OD×ID×THK). NB/DN is a single value | three columns → raw MM |
| 4 | No class / PN / rating column anywhere — so it is not a flange item at all | no class, no PN → raw MM |
| 5 | ★ **Off-series test:** if *any* value in the column falls outside the DN series (15,20,25,32,40,50,65,80,100,125,150,200,250,300,350,400,450,500,600,700,800…), the whole column is raw MM | 130, 223, 260, 318, 393, 540, 680, 707, 710, 867, 1716, 4666, 5002, 5640, 5969 → raw MM, conclusively |
| 6 | Material is a sheet/roll material quoted with a thickness (rubber, CNAF, PTFE, graphite) | NEOPRENE + 3/5/10 MM → cut item, not a flange gasket |

**A bore reading requires positive evidence**: the literal token `NB` / `DN` / `NPS` / `A`,
**or** a class/PN rating alongside the number (Rule V size-world law). Absent that evidence,
a bare metric number is a measurement — and it is written `{n}MM`, never `{n} NB`.

Corollary in the other direction: `NB 100 X PN16` is a bore designation and carries **no
inch mark and no MM suffix** — `100 NB`, not `100MM`. The two worlds never blend.

### 2.3 Bind by name, never by position
The column order in this BOQ is **WIDTH → THICKNESS → LENGTH**, not the usual
length-width-thickness. Positional assumption produces nonsense (a "223 mm thick" gasket).
Always map the value to the field named in its own sub-header.

### 2.4 Typo-tolerant header matching (fuzzy, edit distance ≤ 2)
Observed and adjacent misspellings that must still bind:
```
TRHICKNESS · THCKNESS · THIKNESS · THICKNES · THK · TH.        -> THICKNESS
LENGHT · LENTH · LG · LONG · L                                  -> LENGTH
WITDH · WIDHT · WD · W                                          -> WIDTH
QNTY · QTY. · QYT · NOS · NO'S · PCS                            -> QTY
DIAMETER · DIA · Ø                                              -> OD (or CS on O-rings)
MATERIAL DESCRIPTION · MOC · MATL · SPEC                        -> MATERIAL
```
An exact-match header lookup fails on `TRHICKNESS` and silently loses a dimension — which
is precisely what happened here.

---

## PART 3 — CONVERSION (rectangular strip / sheet-cut items)

With W, T and L bound, the product is a rectangular cut item (Rule X disposition: QUOTE):

```
SIZE: {L}MM LENGTH X {W}MM WIDTH X {T}MM THK, {MATERIAL} (NON STANDARD)
```
Order in the GGPL string stays **LENGTH × WIDTH × THK** (house form, Section 4.1 SC-7),
regardless of the order the customer's columns used.

**Two flags this genre always needs:**
- **Shore hardness not stated** for a rubber item → `KINDLY CONFIRM SHORE HARDNESS`
  (house form when given: `NEOPRENE 60 - 70 SHORE A HARDNESS`).
- **Length beyond sheet stock** — any length over ~2000 MM must come from roll material:
  `LENGTH {x}MM REQUIRES ROLL STOCK — CONFIRM ROLL WIDTH COVERS {W}MM; NO SPLICE UNLESS APPROVED`.
  (A 5969 MM × 710 MM × 10 MM strip is cuttable from roll but not from a standard sheet.)

---

## PART 4 — WORKED CONVERSION (the 18-line neoprene BOQ)

All 18 lines convert; none are dropped; QTY is bound from its own spanning column.

```
 1  100 W x  3 T x  223 L  x60  -> SIZE:  223MM LENGTH X 100MM WIDTH X  3MM THK, NEOPRENE RUBBER (NON STANDARD)
 2  100 W x  3 T x  318 L  x24  -> SIZE:  318MM LENGTH X 100MM WIDTH X  3MM THK, NEOPRENE RUBBER (NON STANDARD)
 3  100 W x  5 T x  393 L   x8  -> SIZE:  393MM LENGTH X 100MM WIDTH X  5MM THK, NEOPRENE RUBBER (NON STANDARD)
 4  130 W x  5 T x  707 L   x4  -> SIZE:  707MM LENGTH X 130MM WIDTH X  5MM THK, NEOPRENE RUBBER (NON STANDARD)
 5  260 W x  5 T x  867 L  x14  -> SIZE:  867MM LENGTH X 260MM WIDTH X  5MM THK, NEOPRENE RUBBER (NON STANDARD)
 6  400 W x 10 T x 1716 L  x54  -> SIZE: 1716MM LENGTH X 400MM WIDTH X 10MM THK, NEOPRENE RUBBER (NON STANDARD)
 7  540 W x 10 T x 4666 L  x13  -> SIZE: 4666MM LENGTH X 540MM WIDTH X 10MM THK, NEOPRENE RUBBER (NON STANDARD) *
 8  630 W x 10 T x 4666 L  x19  -> SIZE: 4666MM LENGTH X 630MM WIDTH X 10MM THK, NEOPRENE RUBBER (NON STANDARD) *
 9  540 W x 10 T x 5002 L  x29  -> SIZE: 5002MM LENGTH X 540MM WIDTH X 10MM THK, NEOPRENE RUBBER (NON STANDARD) *
10  630 W x 10 T x 5002 L  x13  -> SIZE: 5002MM LENGTH X 630MM WIDTH X 10MM THK, NEOPRENE RUBBER (NON STANDARD) *
11  680 W x 10 T x 5002 L   x4  -> SIZE: 5002MM LENGTH X 680MM WIDTH X 10MM THK, NEOPRENE RUBBER (NON STANDARD) *
12  540 W x 10 T x 5640 L   x2  -> SIZE: 5640MM LENGTH X 540MM WIDTH X 10MM THK, NEOPRENE RUBBER (NON STANDARD) *
13  630 W x 10 T x 5640 L   x3  -> SIZE: 5640MM LENGTH X 630MM WIDTH X 10MM THK, NEOPRENE RUBBER (NON STANDARD) *
14  680 W x 10 T x 5640 L   x4  -> SIZE: 5640MM LENGTH X 680MM WIDTH X 10MM THK, NEOPRENE RUBBER (NON STANDARD) *
15  540 W x 10 T x 5969 L  x26  -> SIZE: 5969MM LENGTH X 540MM WIDTH X 10MM THK, NEOPRENE RUBBER (NON STANDARD) *
16  630 W x 10 T x 5969 L  x20  -> SIZE: 5969MM LENGTH X 630MM WIDTH X 10MM THK, NEOPRENE RUBBER (NON STANDARD) *
17  680 W x 10 T x 5969 L   x3  -> SIZE: 5969MM LENGTH X 680MM WIDTH X 10MM THK, NEOPRENE RUBBER (NON STANDARD) *
18  710 W x 10 T x 5969 L   x5  -> SIZE: 5969MM LENGTH X 710MM WIDTH X 10MM THK, NEOPRENE RUBBER (NON STANDARD) *

* ROLL-STOCK ITEMS (length > 2000MM)
FLAGS: SHORE HARDNESS NOT STATED — KINDLY CONFIRM (typ. NEOPRENE 60-70 SHORE A) ·
       ITEMS 7-18 REQUIRE ROLL MATERIAL — CONFIRM ROLL WIDTH >= STRIP WIDTH, NO SPLICE
       UNLESS APPROVED · REVISED FINAL BOQ — SUPERSEDES EARLIER OFFER (quote reference)
CHECK: 18 lines parsed · 18 QUOTE · 0 deferred · 0 out of scope · total qty 305
       [corrected 2026-07-29: the 18 quantities above sum to 305, not 315 —
        60+24+8+4+14+54+13+19+29+13+4+2+3+4+26+20+3+5. The line listing is the
        authority; the earlier summary figure was off by 10.]
```

---

## PART 5 — FAILURE MODES THIS RULE PREVENTS
1. Dimensions dropped because sub-header columns were unnamed in row 1 (this failure).
2. `MM` never applied because the unit lived only in the merged banner.
3. W × T × L read positionally as L × W × T — a plausible-looking, completely wrong gasket.
3a. Raw millimetre widths (100 / 400 / 630) misread as nominal bore NB 100 / NB 400 / NB 630,
    turning cut strips into flange gaskets.
4. `TRHICKNESS` (and its cousins) failing an exact header match and losing a column.
5. QTY misread when its column spans both header rows and row 2 is blank beneath it.
6. Long strips quoted as sheet-cut when they need roll stock.

## VALIDATION ADDITIONS (Section 7.2)
- **38.** Header rows reconciled against data-row column count; a mismatch forces a
  multi-level re-read, never a column drop.
- **39.** Every dimension bound by sub-header name, with the unit inherited from its parent
  banner; positional binding never used.
- **39a.** Raw-MM vs nominal-bore resolved by the six tests in 2.2 before any size is written.
  A bare metric number without an NB/DN/NPS token or a class/PN rating is a measurement:
  written `{n}MM`, never `{n} NB`. Off-series values in a column settle the whole column.
- **40.** Header matching is fuzzy (edit distance ≤ 2) against the canonical lexicon.
- **41.** Rubber cut items carry a shore-hardness confirmation; lengths > 2000 MM carry a
  roll-stock flag.

## REGRESSION FIXTURE (Section 8)
| Fixture | Tests | Must produce |
|---|---|---|
| Neoprene revised-final BOQ (18 lines, 2-row header) | X-2: spanned-header detection via count mismatch, parent>child composition, MM inheritance, W×T×L name binding, `TRHICKNESS` fuzzy match, QTY spanning column, roll-stock and shore-hardness flags | 18 lines out, all QUOTE, dims in LENGTH × WIDTH × THK order, 12 roll-stock flags, total qty 305 |

Implemented in `tests/test_rule_x2_y_z.py` (Rule X-2 section).
