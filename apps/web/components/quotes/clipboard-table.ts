export type ClipboardTableSource = "html" | "tsv";

export type ClipboardTableDetection = {
  source: ClipboardTableSource;
  rows: string[][];
  headers: string[];
  bodyRows: string[][];
  hasHeader: boolean;
};

export type StructuredItemFields = {
  customer_sl_no: string;
  customer_item_code: string;
  raw_description: string;
  quantity: string;
  uom: string;
};

type StructuredItemField = keyof StructuredItemFields;

const POSITIONAL_FIELDS: StructuredItemField[] = [
  "customer_sl_no",
  "customer_item_code",
  "raw_description",
  "quantity",
  "uom",
];

function normalizeHeader(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function fieldForHeader(value: string): StructuredItemField | undefined {
  const header = normalizeHeader(value);
  if (!header) return undefined;
  if (/^(sl|sr|serial|line|item) ?(no|number)?$/.test(header) || header === "customer sl no") return "customer_sl_no";
  if (header.includes("item code") || header === "code" || header === "part no" || header === "part number") return "customer_item_code";
  if (header.includes("description") || header === "details" || header === "item") return "raw_description";
  if (header === "qty" || header === "quantity" || header.includes("required qty")) return "quantity";
  if (header === "uom" || header === "unit" || header === "units" || header.includes("unit of measure")) return "uom";
  return undefined;
}

function cleanRows(rows: string[][]) {
  return rows
    .map((row) => row.map((cell) => cell.trim()))
    .filter((row) => row.some(Boolean));
}

export function parseTsvTable(text: string): string[][] {
  return cleanRows(
    text
      .replace(/\r\n/g, "\n")
      .replace(/\r/g, "\n")
      .split("\n")
      .map((row) => row.split("\t")),
  );
}

function parseHtmlTable(html: string): string[][] {
  if (!html || typeof DOMParser === "undefined") return [];
  const document = new DOMParser().parseFromString(html, "text/html");
  const table = document.querySelector("table");
  if (!table) return [];
  return cleanRows(
    Array.from(table.querySelectorAll("tr")).map((row) =>
      Array.from(row.querySelectorAll("th,td")).map((cell) => cell.textContent ?? ""),
    ),
  );
}

export function detectClipboardTable(html: string, text: string): ClipboardTableDetection | null {
  const htmlRows = parseHtmlTable(html);
  const rows = htmlRows.length ? htmlRows : text.includes("\t") ? parseTsvTable(text) : [];
  if (!rows.length || Math.max(...rows.map((row) => row.length)) < 2) return null;
  const headerMatches = rows[0].filter((cell) => fieldForHeader(cell)).length;
  const hasHeader = headerMatches >= 2;
  return {
    source: htmlRows.length ? "html" : "tsv",
    rows,
    headers: hasHeader ? rows[0] : POSITIONAL_FIELDS.map((field) => field.replaceAll("_", " ")),
    bodyRows: hasHeader ? rows.slice(1) : rows,
    hasHeader,
  };
}

export function structuredRowsToItemFields(detection: ClipboardTableDetection): StructuredItemFields[] {
  const fields = detection.hasHeader
    ? detection.headers.map(fieldForHeader)
    : POSITIONAL_FIELDS;
  return detection.bodyRows
    .map((row) => {
      const item: StructuredItemFields = {
        customer_sl_no: "",
        customer_item_code: "",
        raw_description: "",
        quantity: "",
        uom: "",
      };
      row.forEach((value, index) => {
        const field = fields[index];
        if (field) item[field] = value.trim();
      });
      return item;
    })
    .filter((row) => Object.values(row).some(Boolean));
}

export function rowsToTsv(rows: string[][]) {
  return rows.map((row) => row.join("\t")).join("\n");
}
