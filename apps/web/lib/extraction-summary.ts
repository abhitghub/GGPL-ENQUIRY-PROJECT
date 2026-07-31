import { GasketItem } from "@/lib/api";
import { getString } from "@/components/quotes/item-validation";

/**
 * Extraction summary lines — the internal "please provide formula" list sales
 * sends out once an enquiry is processed.
 *
 * The list is a *spec* list, not an item list: size and pressure rating are the
 * dimensions that vary within one spec, so a family is keyed on everything
 * except them and the ratings collapse onto a single line:
 *
 *   SS304/GRA+SS304IR&SS304OR,150# ,300# ,600# ,900# ,1500#
 *   SS316L/GRA+SS316LIR&SS316LOR (NON STD)
 *   KAMMPROFILE SS347 POLY CARBON GRADE APX-2 OR EQUIVALENT LAYER ON BOTH SIDES ,7.35MM THK,6.35MM CORE (NON STD)
 *   NON ASBESTOS BS7531 GR X ,3MM THK ,150# ,RF
 *   RTJ ,OVAL ,SOFTIRON ,90 BHN HARDNESS
 *
 * Fillers and ring materials use the shop shorthand (GRAPHITE -> GRA) rather
 * than the long wording the rules engine stores for `ggpl_description`.
 */

export type ExtractionSummaryGroup = {
  item: string;
  /** Line items that collapsed onto this spec. */
  count: number;
  /** Total quantity across those line items — what pricing works against. */
  qty: number;
  /** 1-based line numbers feeding the spec, so a price can be traced back. */
  lines: number[];
};

type FamilyRender = (ratings: string[], thicknesses: string[]) => string;

type SummaryFamily = {
  /** Dedupe key: the spec with size, rating and thickness removed. */
  groupKey: string;
  render: FamilyRender;
  /** False when no house family could be built and the raw wording was used. */
  classified: boolean;
};

// --- shorthand ------------------------------------------------------------

/**
 * Filler shorthand. One alternation applied in a single pass, longest form
 * first, so a span is rewritten once — sequential replacements would turn
 * MICA GRAPHITE into GRAPHITE/MICA and then into GRA/MICA.
 */
const FILLER_SHORTHAND_RE = new RegExp(
  [
    "95\\s*%?\\s*PURE\\s+GRAPHITE",
    "MICA\\s+GRAPHITE",
    "GRAPHITE\\s*\\/\\s*MICA",
    "FLEXIBLE\\s+(?:INHIBITED\\s+)?GRAPHITE",
    "FLEX\\s+GRAPHITE",
    "GRAFOIL\\s+GRAPHITE",
    "VERMICULITE(?:\\s+FILLER)?(?:\\s*\\([^)]*\\))?",
    "THERMICULITE\\s*\\d*",
    "GRAFOIL",
    "GRAPHITE",
  ].join("|"),
  "g",
);

function fillerShorthand(match: string): string {
  if (/PURE/.test(match)) return "95% PURE GRA";
  if (/MICA/.test(match)) return "GRAPHITE/MICA";
  if (/FLEX/.test(match)) return "FLEX GRA";
  if (/VERMICULITE|THERMICULITE/.test(match)) return "THERMICULITE";
  return "GRA";
}

// CAF is what the customer asks for; the engine normalises it to CNAF plus a
// deviation note and a grade. The filler slot keeps the customer's word.
const CNAF_FILLER_RE = /\bCNAF\b.*$/;

/** Ring / metal shorthand: CARBON STEEL -> CS, SS 316 L -> SS316L. */
function shortMetal(value: unknown): string {
  const text = normalizeText(value);
  if (!text) return "";
  return text
    .replace(/\bCARBON\s+STEEL\b/g, "CS")
    .replace(/\bSTAINLESS\s+STEEL\b/g, "SS")
    .replace(/\bSS\s+(\d)/g, "SS$1")
    .replace(/\b(SS\d{3})\s+L\b/g, "$1L")
    .replace(/\s{2,}/g, " ")
    .trim();
}

/**
 * Shop shorthand for the winding-side filler slot only. Sheet and soft-cut MOC
 * is left as the engine wrote it — the shop spells GRAPHITE out for a cut sheet
 * and keeps the CNAF grade, which the CAF collapse below would drop.
 */
function shortFiller(value: unknown): string {
  const text = normalizeText(value);
  if (!text) return "";
  if (CNAF_FILLER_RE.test(text)) return text.replace(CNAF_FILLER_RE, "CAF").trim();
  return text.replace(FILLER_SHORTHAND_RE, fillerShorthand).replace(/\s{2,}/g, " ").trim();
}

function normalizeText(value: unknown): string {
  return getString(value).toUpperCase().replace(/\s+/g, " ").trim();
}

// --- rating / thickness ---------------------------------------------------

const NON_STANDARD_TOKENS = new Set([
  "NON STANDARD",
  "NON-STANDARD",
  "NONSTANDARD",
  "NON STD",
  "NON-STD",
]);

export function isNonStandard(value: unknown): boolean {
  return NON_STANDARD_TOKENS.has(normalizeText(value));
}

/** "CLASS 150" / "150 LB" / "150#" -> "150#"; "PN 16" -> "PN16". */
export function normalizeRatingLabel(value: unknown): string {
  const text = normalizeText(value);
  if (!text) return "";
  const pn = text.match(/^PN\s*(\d+(?:\.\d+)?)/);
  if (pn) return `PN${trimNumber(pn[1])}`;
  const num = text.match(/(\d+(?:\.\d+)?)/);
  if (num) return `${trimNumber(num[1])}#`;
  return text;
}

function trimNumber(value: string | number): string {
  const num = Number(value);
  if (!Number.isFinite(num)) return String(value);
  return String(Number(num.toFixed(3)));
}

function ratingSortValue(label: string): [number, number] {
  const pn = label.match(/^PN(\d+(?:\.\d+)?)/);
  if (pn) return [1, Number(pn[1])];
  const num = label.match(/^(\d+(?:\.\d+)?)#/);
  if (num) return [0, Number(num[1])];
  return [2, 0];
}

function sortRatings(labels: Iterable<string>): string[] {
  return [...labels].sort((left, right) => {
    const [leftGroup, leftNum] = ratingSortValue(left);
    const [rightGroup, rightNum] = ratingSortValue(right);
    if (leftGroup !== rightGroup) return leftGroup - rightGroup;
    if (leftNum !== rightNum) return leftNum - rightNum;
    return left.localeCompare(right);
  });
}

/** ",150# ,300# ,600#" — empty when the family has no rating at all. */
function ratingsPart(ratings: string[]): string {
  return ratings.length ? `,${ratings.join(" ,")}` : "";
}

/** "3MM THK" for one, "3MM ,1.5MM THK" when a spec is quoted in two thicknesses. */
function thicknessPart(thicknesses: string[]): string {
  if (!thicknesses.length) return "";
  return `${thicknesses.map((thk) => `${thk}MM`).join(" ,")} THK`;
}

function sortThicknesses(values: Iterable<string>): string[] {
  return [...values].sort((left, right) => Number(left) - Number(right));
}

// --- suffixes -------------------------------------------------------------

/**
 * Trailing parentheticals: the B16.47 series, the non-standard marker and any
 * special note (OXYGEN, NACE ...). These belong to the spec, so they split
 * families rather than collapsing into one.
 */
function familySuffix(item: GasketItem): string {
  const parts: string[] = [];
  const special = normalizeText(item.special);
  if (special) parts.push(special);
  const standard = normalizeText(item.standard);
  if (isNonStandard(standard)) {
    parts.push("NON STD");
  } else {
    const series = standard.match(/SERIES[\s-]*([AB])\b/);
    if (series) parts.push(`SERIES ${series[1]}`);
  }
  return parts.map((part) => ` (${part})`).join("");
}

// --- family builders ------------------------------------------------------

function spiralWoundFamily(item: GasketItem): SummaryFamily | null {
  const winding = shortMetal(item.sw_winding_material);
  const filler = shortFiller(item.sw_filler);
  if (!winding && !filler) return null;

  const head = [winding, filler].filter(Boolean).join("/");
  const inner = shortMetal(item.sw_inner_ring);
  const outer = shortMetal(item.sw_outer_ring);
  let rings: string;
  if (inner && outer) rings = `+${inner}IR&${outer}OR`;
  else if (inner) rings = `+${inner}IR&WITHOUT OUTERRING`;
  else if (outer) rings = `+${outer}OR`;
  else rings = "+WITHOUT INNERRING & WITHOUT OUTERRING";

  const suffix = familySuffix(item);
  const base = `${head}${rings}`;
  return {
    groupKey: `SPW|${base}|${suffix}`,
    render: (ratings) => `${base}${ratingsPart(ratings)}${suffix}`,
    classified: true,
  };
}

function kammFamily(item: GasketItem): SummaryFamily | null {
  const core = shortMetal(item.kamm_core_material) || shortMetal(item.moc);
  const covering = normalizeText(item.kamm_surface_material || item.kamm_covering_layer);
  if (!core && !covering) return null;

  // The covering wording stays long here — the shop writes "GRAPHITE LAYER ON
  // BOTH SIDES" for a Kammprofile, not "GRA".
  const layer = [core, covering].filter(Boolean).join(" ");
  let head = `KAMMPROFILE ${layer} LAYER ON BOTH SIDES`;
  const outer = shortMetal(item.sw_outer_ring);
  const integral = item.kamm_integral_outer_ring;
  const isIntegral = integral === true || normalizeText(integral) === "INTEGRAL";
  if (outer) head += ` WITH ${outer} OUTER RING`;
  else if (isIntegral) head += " WITH INTEGRAL OUTER RING";

  // Total-and-core thickness is the Kammprofile's identity, not a size that
  // varies inside one spec, so it stays in the key.
  const thk = numberText(item.thickness_mm);
  const coreThk = numberText(item.kamm_core_thk);
  let thkPart = thk ? ` ,${thk}MM THK` : "";
  if (coreThk) thkPart += `${thkPart ? "," : " ,"}${coreThk}MM CORE`;

  const suffix = familySuffix(item);
  return {
    groupKey: `KAMM|${head}|${thkPart}|${suffix}`,
    render: (ratings) => `${head}${ratingsPart(ratings)}${thkPart}${suffix}`,
    classified: true,
  };
}

function djiFamily(item: GasketItem): SummaryFamily | null {
  const jacket = shortMetal(item.moc);
  if (!jacket) return null;
  const filler = shortFiller(item.dji_filler);
  const head = filler && filler !== "GRA" ? `DJ/${jacket}+${filler}` : `DJ/${jacket}`;
  const suffix = familySuffix(item);
  return {
    groupKey: `DJI|${head}|${suffix}`,
    render: (ratings, thicknesses) => {
      const thk = thicknessPart(thicknesses);
      return `${head}${ratingsPart(ratings)}${thk ? ` ,${thk}` : ""}${suffix}`;
    },
    classified: true,
  };
}

function rtjFamily(item: GasketItem): SummaryFamily | null {
  const moc = shortMetal(item.moc);
  if (!moc) return null;
  const groove = normalizeText(item.rtj_groove_type) || "OCT";
  const hardnessSpec = normalizeText(item.rtj_hardness_spec);
  const bhn = numberText(item.rtj_hardness_bhn);
  const hardness = hardnessSpec || (bhn ? `${bhn} BHN HARDNESS` : "");
  const parts = ["RTJ", groove, moc];
  if (hardness) parts.push(hardness);
  if (normalizeText(item.standard).includes("API 6A")) parts.push("API-6A TYPE");
  // Ring number and rating are the size dimension for an RTJ — left out.
  const base = parts.join(" ,");
  const suffix = familySuffix(item);
  return {
    groupKey: `RTJ|${base}|${suffix}`,
    render: () => `${base}${suffix}`,
    classified: true,
  };
}

function iskFamily(item: GasketItem): SummaryFamily | null {
  const parts = [
    normalizeText(item.isk_style) || "ISK",
    normalizeText(item.isk_type),
    shortFiller(item.isk_gasket_material),
  ].filter(Boolean);
  if (parts.length < 2) return null;
  const base = parts.join(" ,");
  const suffix = familySuffix(item);
  return {
    groupKey: `ISK|${base}|${suffix}`,
    render: (ratings, thicknesses) => {
      const thk = thicknessPart(thicknesses);
      return `${base}${thk ? ` ,${thk}` : ""}${ratingsPart(ratings)}${suffix}`;
    },
    classified: true,
  };
}

const CONSTRUCTION_WORD: Record<string, string> = {
  SHEET_GASKET: "SHEET GASKET",
  CORRUGATED: "CORRUGATED GASKET",
  PLUG_GASKET: "PLUG GASKET",
  METAL_CLAD: "METAL CLAD GASKET",
  SOLID_METAL: "SOLID METAL GASKET",
  CMG: "CORRUGATED METAL GASKET",
  ENVELOPE: "ENVELOPE GASKET",
};

/** SOFT_CUT and the other MOC-plus-thickness families. */
function sheetFamily(item: GasketItem, gasketType: string): SummaryFamily | null {
  const moc = normalizeText(item.moc);
  if (!moc) return null;
  const construction = CONSTRUCTION_WORD[gasketType];
  const head = construction ? `${moc} ${construction}` : moc;
  const face = normalizeText(item.face_type);
  const suffix = familySuffix(item);
  return {
    groupKey: `${gasketType}|${head}|${face}|${suffix}`,
    render: (ratings, thicknesses) => {
      const thk = thicknessPart(thicknesses);
      return [head, thk, ratingsPart(ratings).replace(/^,/, ""), face]
        .filter(Boolean)
        .join(" ,") + suffix;
    },
    classified: true,
  };
}

/**
 * Rows with no house family — one-off products such as
 * "SIZE : 0.1 THK x 1736 LG x 45 W , DUPLEX S31803 LAMIFLEX SEALING STRIP" or a
 * graphite sheet cut to size. The wording as processed *is* the spec, so it is
 * echoed rather than dropped from the list.
 */
function rawFamily(item: GasketItem): SummaryFamily | null {
  const text = normalizeText(item.ggpl_description) || normalizeText(item.raw_description);
  if (!text) return null;
  return {
    groupKey: `RAW|${text}`,
    render: () => text,
    classified: false,
  };
}

function numberText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "";
  const num = Number(value);
  if (!Number.isFinite(num) || num === 0) return "";
  return trimNumber(num);
}

export function summaryFamily(item: GasketItem): SummaryFamily | null {
  if (item.status === "regret") return null;
  const gasketType = normalizeText(item.gasket_type) || "SOFT_CUT";
  let family: SummaryFamily | null = null;
  if (gasketType === "SPIRAL_WOUND") family = spiralWoundFamily(item);
  else if (gasketType === "KAMM") family = kammFamily(item);
  else if (gasketType === "DJI") family = djiFamily(item);
  else if (gasketType === "RTJ") family = rtjFamily(item);
  else if (gasketType === "ISK" || gasketType === "ISK_RTJ") family = iskFamily(item);
  else family = sheetFamily(item, gasketType);
  return family ?? rawFamily(item);
}

/** True when the row only made the list through its raw wording. */
export function isUnclassifiedSummaryItem(item: GasketItem): boolean {
  const family = summaryFamily(item);
  return family !== null && !family.classified;
}

/**
 * The summary rows plus, for every line item, the row it collapsed onto
 * (null when the row was skipped — a regret line, or one with no wording at
 * all). Pricing needs both halves: the spec list carries the formula, and the
 * per-line index puts that formula next to the line on the pricing sheet.
 */
export type ExtractionSummaryIndex = {
  groups: ExtractionSummaryGroup[];
  /** groupIndexByLine[i] — index into `groups` for items[i]. */
  groupIndexByLine: Array<number | null>;
};

export function buildExtractionSummaryIndex(items: GasketItem[]): ExtractionSummaryIndex {
  type Bucket = {
    render: FamilyRender;
    lines: number[];
    qty: number;
    ratings: Set<string>;
    thicknesses: Set<string>;
    order: number;
  };
  const buckets = new Map<string, Bucket>();
  const bucketKeyByLine: Array<string | null> = [];

  items.forEach((item, index) => {
    const family = summaryFamily(item);
    if (!family) {
      bucketKeyByLine.push(null);
      return;
    }
    let bucket = buckets.get(family.groupKey);
    if (!bucket) {
      bucket = {
        render: family.render,
        lines: [],
        qty: 0,
        ratings: new Set<string>(),
        thicknesses: new Set<string>(),
        order: buckets.size,
      };
      buckets.set(family.groupKey, bucket);
    }
    bucketKeyByLine.push(family.groupKey);
    bucket.lines.push(index + 1);
    const quantity = Number(item.quantity);
    if (Number.isFinite(quantity)) bucket.qty += quantity;
    const rating = normalizeRatingLabel(item.rating);
    if (rating) bucket.ratings.add(rating);
    const thickness = numberText(item.thickness_mm);
    if (thickness) bucket.thicknesses.add(thickness);
  });

  const ordered = [...buckets.entries()]
    .map(([groupKey, bucket]) => ({
      groupKey,
      row: {
        item: bucket.render(sortRatings(bucket.ratings), sortThicknesses(bucket.thicknesses)),
        count: bucket.lines.length,
        qty: Number(bucket.qty.toFixed(3)),
        lines: bucket.lines,
      },
      order: bucket.order,
    }))
    .filter((entry) => entry.row.item.trim().length > 0)
    .sort((left, right) => (right.row.count - left.row.count) || (left.order - right.order));

  const positionByKey = new Map(ordered.map((entry, position) => [entry.groupKey, position]));
  return {
    groups: ordered.map((entry) => entry.row),
    groupIndexByLine: bucketKeyByLine.map((key) => (key === null ? null : positionByKey.get(key) ?? null)),
  };
}

/**
 * Collapse processed rows into formula-request lines. Rows are ordered by how
 * many items feed the line, as before.
 */
export function buildExtractionSummary(items: GasketItem[]): ExtractionSummaryGroup[] {
  return buildExtractionSummaryIndex(items).groups;
}

/**
 * Fingerprint of the line items a summary was built from. Shared by the
 * extraction summary and the pricing formulas so both can tell when the specs
 * moved underneath them. Mirrors `extraction_summary()` on the API side.
 */
export function extractionSummaryItemSignature(items: GasketItem[]): string {
  return JSON.stringify(items.map((item) =>
    Object.keys(item)
      .sort()
      .map((key) => [key, item[key]]),
  ));
}