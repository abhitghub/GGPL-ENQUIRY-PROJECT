"use client";

import * as React from "react";

import type { GasketItem } from "@/lib/api";
import { toNumber } from "@/lib/api";

// Excel-like pricing grid: click/drag range selection, type-to-edit, Enter/Tab/
// arrow navigation, copy/paste TSV (works with real Excel), Ctrl+D fill down,
// and a drag fill-handle on the selection corner. Editable columns are Unit
// price and Discount %; everything else is read-only context.

type ColKey = "sl" | "desc" | "ggpl" | "qty" | "uom" | "unit" | "disc" | "final" | "total";

const COLS: Array<{ key: ColKey; label: string; editable: boolean; className: string }> = [
  { key: "sl", label: "#", editable: false, className: "w-12 text-center" },
  { key: "desc", label: "Description", editable: false, className: "min-w-[280px]" },
  { key: "ggpl", label: "GGPL description", editable: false, className: "min-w-[280px]" },
  { key: "qty", label: "Qty", editable: false, className: "w-16 text-right" },
  { key: "uom", label: "UOM", editable: false, className: "w-16" },
  { key: "unit", label: "Unit price", editable: true, className: "w-28 text-right" },
  { key: "disc", label: "Discount %", editable: true, className: "w-24 text-right" },
  { key: "final", label: "Final price", editable: false, className: "w-28 text-right" },
  { key: "total", label: "Total", editable: false, className: "w-28 text-right" },
];

const EDITABLE_COLS = COLS.map((col, index) => (col.editable ? index : -1)).filter((index) => index >= 0);

type Range = { minRow: number; maxRow: number; minCol: number; maxCol: number };

function parseNumber(raw: string): number {
  const value = Number(String(raw).replace(/[^0-9.\-]/g, ""));
  return Number.isFinite(value) ? value : 0;
}

function parseClipboard(text: string): string[][] {
  const rows = text.replace(/\r/g, "").split("\n");
  while (rows.length && rows[rows.length - 1] === "") rows.pop();
  return rows.map((row) => row.split("\t"));
}

export function PricingGrid({
  items,
  unitPrices,
  lineDiscounts,
  canEdit,
  onApply,
}: {
  items: GasketItem[];
  unitPrices: number[];
  lineDiscounts: number[];
  canEdit: boolean;
  onApply: (next: { unit_prices: number[]; line_discounts_pct: number[] }) => void;
}) {
  const [active, setActive] = React.useState<{ row: number; col: number } | null>(null);
  const [anchor, setAnchor] = React.useState<{ row: number; col: number } | null>(null);
  const [focus, setFocus] = React.useState<{ row: number; col: number } | null>(null);
  const [selecting, setSelecting] = React.useState(false);
  const [editing, setEditing] = React.useState<{ row: number; col: number; value: string } | null>(null);
  const [fillSource, setFillSource] = React.useState<Range | null>(null);
  const [fillRow, setFillRow] = React.useState<number | null>(null);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const editRef = React.useRef<HTMLInputElement>(null);

  const range: Range | null = anchor && focus
    ? {
        minRow: Math.min(anchor.row, focus.row),
        maxRow: Math.max(anchor.row, focus.row),
        minCol: Math.min(anchor.col, focus.col),
        maxCol: Math.max(anchor.col, focus.col),
      }
    : null;

  const fillRange: Range | null = fillSource && fillRow !== null && fillRow > fillSource.maxRow
    ? { ...fillSource, maxRow: fillRow }
    : null;

  function cellValue(row: number, col: number): string {
    const item = items[row];
    if (!item) return "";
    const unit = toNumber(unitPrices[row] ?? 0);
    const disc = Math.max(toNumber(lineDiscounts[row] ?? 0), 0);
    const finalPrice = unit * (1 - disc / 100);
    const qty = item.status === "regret" ? 0 : toNumber(item.quantity);
    switch (COLS[col].key) {
      case "sl": return String(row + 1);
      case "desc": return item.status === "regret" ? "REGRET - CANNOT PRODUCE" : String(item.raw_description || item.ggpl_description || "");
      case "ggpl": return item.status === "regret" ? "" : String(item.ggpl_description || "");
      case "qty": return String(item.quantity ?? "");
      case "uom": return String(item.uom || "NOS");
      case "unit": return String(unitPrices[row] ?? 0);
      case "disc": return String(lineDiscounts[row] ?? 0);
      case "final": return finalPrice.toFixed(2);
      case "total": return (finalPrice * qty).toFixed(2);
    }
  }

  // Apply a batch of edits to the two arrays in ONE parent update.
  function applyEdits(edits: Array<{ row: number; col: number; value: string }>) {
    if (!canEdit || !edits.length) return;
    const nextUnits = [...unitPrices];
    const nextDiscs = [...lineDiscounts];
    let changed = false;
    for (const edit of edits) {
      if (edit.row < 0 || edit.row >= items.length) continue;
      const key = COLS[edit.col]?.key;
      if (key === "unit") { nextUnits[edit.row] = parseNumber(edit.value); changed = true; }
      if (key === "disc") { nextDiscs[edit.row] = parseNumber(edit.value); changed = true; }
    }
    if (changed) onApply({ unit_prices: nextUnits, line_discounts_pct: nextDiscs });
  }

  function select(row: number, col: number, extend: boolean) {
    setActive({ row, col });
    setFocus({ row, col });
    if (!extend) setAnchor({ row, col });
    setEditing(null);
  }

  function startEdit(row: number, col: number, initial?: string) {
    if (!canEdit || !COLS[col].editable) return;
    setEditing({ row, col, value: initial ?? cellValue(row, col) });
  }

  function commitEdit(move: "down" | "right" | "stay" = "stay") {
    if (!editing) return;
    applyEdits([editing]);
    const { row, col } = editing;
    setEditing(null);
    if (move === "down" && row + 1 < items.length) select(row + 1, col, false);
    else if (move === "right") {
      const nextEditable = EDITABLE_COLS.find((c) => c > col) ?? EDITABLE_COLS[0];
      const nextRow = nextEditable <= col ? Math.min(row + 1, items.length - 1) : row;
      select(nextRow, nextEditable, false);
    }
  }

  React.useEffect(() => {
    if (editing) editRef.current?.focus();
  }, [editing]);

  React.useEffect(() => {
    if (!selecting && !fillSource) return undefined;
    const up = () => {
      setSelecting(false);
      if (fillSource && fillRange) {
        // Tile the source block's values downward (Excel copy-fill).
        const srcRows = fillSource.maxRow - fillSource.minRow + 1;
        const edits: Array<{ row: number; col: number; value: string }> = [];
        for (let row = fillSource.maxRow + 1; row <= fillRange.maxRow; row += 1) {
          for (let col = fillSource.minCol; col <= fillSource.maxCol; col += 1) {
            if (!COLS[col]?.editable) continue;
            const srcRow = fillSource.minRow + ((row - fillSource.minRow) % srcRows);
            edits.push({ row, col, value: cellValue(srcRow, col) });
          }
        }
        applyEdits(edits);
        setAnchor({ row: fillSource.minRow, col: fillSource.minCol });
        setFocus({ row: fillRange.maxRow, col: fillSource.maxCol });
      }
      setFillSource(null);
      setFillRow(null);
    };
    window.addEventListener("mouseup", up);
    return () => window.removeEventListener("mouseup", up);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selecting, fillSource, fillRange]);

  function onKeyDown(event: React.KeyboardEvent) {
    if (editing) {
      if (event.key === "Enter") { event.preventDefault(); commitEdit("down"); }
      else if (event.key === "Tab") { event.preventDefault(); commitEdit("right"); }
      else if (event.key === "Escape") { event.preventDefault(); setEditing(null); }
      return;
    }
    if (!active) return;
    const move = (dRow: number, dCol: number, extend: boolean) => {
      event.preventDefault();
      const row = Math.max(0, Math.min(items.length - 1, (extend && focus ? focus.row : active.row) + dRow));
      const col = Math.max(0, Math.min(COLS.length - 1, (extend && focus ? focus.col : active.col) + dCol));
      if (extend) setFocus({ row, col });
      else select(row, col, false);
      containerRef.current?.querySelector(`[data-cell="${row}-${col}"]`)?.scrollIntoView({ block: "nearest", inline: "nearest" });
    };
    if (event.key === "ArrowDown") move(1, 0, event.shiftKey);
    else if (event.key === "ArrowUp") move(-1, 0, event.shiftKey);
    else if (event.key === "ArrowLeft") move(0, -1, event.shiftKey);
    else if (event.key === "ArrowRight") move(0, 1, event.shiftKey);
    else if (event.key === "Enter") { event.preventDefault(); startEdit(active.row, active.col); }
    else if (event.key === "F2") { event.preventDefault(); startEdit(active.row, active.col); }
    else if (event.key === "Tab") move(0, 1, false);
    else if ((event.key === "Delete" || event.key === "Backspace") && canEdit) {
      event.preventDefault();
      const target = range ?? { minRow: active.row, maxRow: active.row, minCol: active.col, maxCol: active.col };
      const edits: Array<{ row: number; col: number; value: string }> = [];
      for (let row = target.minRow; row <= target.maxRow; row += 1)
        for (let col = target.minCol; col <= target.maxCol; col += 1)
          if (COLS[col].editable) edits.push({ row, col, value: "0" });
      applyEdits(edits);
    } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "d" && canEdit) {
      event.preventDefault();
      if (!range || range.maxRow <= range.minRow) return;
      const edits: Array<{ row: number; col: number; value: string }> = [];
      for (let row = range.minRow + 1; row <= range.maxRow; row += 1)
        for (let col = range.minCol; col <= range.maxCol; col += 1)
          if (COLS[col].editable) edits.push({ row, col, value: cellValue(range.minRow, col) });
      applyEdits(edits);
    } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "a") {
      event.preventDefault();
      setAnchor({ row: 0, col: 0 });
      setFocus({ row: items.length - 1, col: COLS.length - 1 });
    } else if (!event.ctrlKey && !event.metaKey && !event.altKey && event.key.length === 1) {
      if (COLS[active.col].editable && canEdit) { event.preventDefault(); startEdit(active.row, active.col, event.key); }
    }
  }

  function onCopy(event: React.ClipboardEvent) {
    if (editing) return;
    const target = range ?? (active ? { minRow: active.row, maxRow: active.row, minCol: active.col, maxCol: active.col } : null);
    if (!target) return;
    const rows: string[] = [];
    for (let row = target.minRow; row <= target.maxRow; row += 1) {
      const values: string[] = [];
      for (let col = target.minCol; col <= target.maxCol; col += 1) values.push(cellValue(row, col));
      rows.push(values.join("\t"));
    }
    event.clipboardData.setData("text/plain", rows.join("\n"));
    event.preventDefault();
  }

  function onPaste(event: React.ClipboardEvent) {
    if (!canEdit || editing) return;
    const parsed = parseClipboard(event.clipboardData.getData("text/plain"));
    if (!parsed.length || !active) return;
    event.preventDefault();
    const start = range ?? { minRow: active.row, maxRow: active.row, minCol: active.col, maxCol: active.col };
    const edits: Array<{ row: number; col: number; value: string }> = [];
    const singleValue = parsed.length === 1 && parsed[0].length === 1;
    if (singleValue && range && (range.maxRow > range.minRow || range.maxCol > range.minCol)) {
      // One value over a selection fills the whole selection (Excel behaviour).
      for (let row = range.minRow; row <= range.maxRow; row += 1)
        for (let col = range.minCol; col <= range.maxCol; col += 1)
          if (COLS[col].editable) edits.push({ row, col, value: parsed[0][0] });
    } else {
      parsed.forEach((rowValues, rowOffset) => {
        rowValues.forEach((value, colOffset) => {
          const row = start.minRow + rowOffset;
          const col = start.minCol + colOffset;
          if (COLS[col]?.editable) edits.push({ row, col, value });
        });
      });
    }
    applyEdits(edits);
  }

  const inRange = (row: number, col: number, r: Range | null) =>
    Boolean(r && row >= r.minRow && row <= r.maxRow && col >= r.minCol && col <= r.maxCol);

  return (
    <div
      ref={containerRef}
      tabIndex={0}
      onKeyDown={onKeyDown}
      onCopy={onCopy}
      onPaste={onPaste}
      className="max-h-[620px] select-none overflow-auto rounded-md border outline-none focus:ring-1 focus:ring-ring"
    >
      <table className="w-full border-collapse text-sm">
        <thead className="sticky top-0 z-10 bg-muted/80 backdrop-blur">
          <tr>
            {COLS.map((col) => (
              <th key={col.key} className={`border-b border-r px-2 py-1.5 text-left text-xs font-medium text-muted-foreground last:border-r-0 ${col.className}`}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item, row) => (
            <tr key={row} className="hover:bg-muted/30">
              {COLS.map((col, colIndex) => {
                const selected = inRange(row, colIndex, range);
                const isActive = active?.row === row && active.col === colIndex;
                const isFillPreview = inRange(row, colIndex, fillRange) && !inRange(row, colIndex, fillSource);
                const isEditing = editing?.row === row && editing.col === colIndex;
                const isFillCorner = canEdit && !editing && ((range && row === range.maxRow && colIndex === range.maxCol) || (!range && isActive));
                return (
                  <td
                    key={col.key}
                    data-cell={`${row}-${colIndex}`}
                    className={`relative border-b border-r px-2 py-1 align-middle last:border-r-0 ${col.className} ${col.editable && canEdit ? "cursor-cell" : "cursor-default"} ${
                      selected ? "bg-emerald-50 ring-1 ring-inset ring-emerald-400/60 dark:bg-emerald-950/20" : ""
                    } ${isActive ? "ring-2 ring-inset ring-emerald-600" : ""} ${isFillPreview ? "ring-1 ring-inset ring-emerald-500/70" : ""} ${
                      col.key === "desc" || col.key === "ggpl" ? "max-w-[420px] truncate text-xs" : ""
                    }`}
                    title={col.key === "desc" || col.key === "ggpl" ? cellValue(row, colIndex) : undefined}
                    onMouseDown={(event) => {
                      if ((event.target as HTMLElement).closest("input")) return;
                      event.preventDefault();
                      containerRef.current?.focus();
                      select(row, colIndex, event.shiftKey);
                      setSelecting(true);
                    }}
                    onMouseEnter={() => {
                      if (fillSource) { setFillRow(row); return; }
                      if (selecting) setFocus({ row, col: colIndex });
                    }}
                    onDoubleClick={() => startEdit(row, colIndex)}
                  >
                    {isEditing ? (
                      <input
                        ref={editRef}
                        value={editing.value}
                        onChange={(event) => setEditing((current) => (current ? { ...current, value: event.target.value } : current))}
                        onBlur={() => commitEdit("stay")}
                        className="w-full bg-transparent text-right outline-none"
                      />
                    ) : (
                      cellValue(row, colIndex)
                    )}
                    {isFillCorner && (
                      <span
                        title="Drag to fill down"
                        className="absolute bottom-0 right-0 z-20 h-2 w-2 translate-x-1/2 translate-y-1/2 cursor-crosshair rounded-[1px] border border-white bg-emerald-600 shadow-sm"
                        onMouseDown={(event) => {
                          event.stopPropagation();
                          event.preventDefault();
                          setFillSource(range ?? { minRow: row, maxRow: row, minCol: colIndex, maxCol: colIndex });
                          setFillRow(null);
                        }}
                      />
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
          {!items.length && (
            <tr><td colSpan={COLS.length} className="px-3 py-6 text-center text-sm text-muted-foreground">No items to price.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
