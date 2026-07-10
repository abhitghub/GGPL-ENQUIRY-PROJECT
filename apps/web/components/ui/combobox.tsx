"use client";

import { Check, ChevronsUpDown, Plus } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

export type ComboboxOption = { value: string; label: string; hint?: string };

export function Combobox({
  value,
  onChange,
  options,
  placeholder = "Select",
  searchPlaceholder = "Search…",
  emptyText = "No matches",
  disabled = false,
  className,
  onCreate,
  createLabel = "Add new",
  allowCustom = false,
}: {
  value: string;
  onChange: (value: string) => void;
  options: ComboboxOption[];
  placeholder?: string;
  searchPlaceholder?: string;
  emptyText?: string;
  disabled?: boolean;
  className?: string;
  onCreate?: (query: string) => void;
  createLabel?: string;
  allowCustom?: boolean;
}) {
  const [open, setOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [highlight, setHighlight] = React.useState(0);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const selected = options.find((option) => option.value === value);

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = q ? options.filter((option) => option.label.toLowerCase().includes(q)) : options;
    return list.slice(0, 100);
  }, [query, options]);

  React.useEffect(() => {
    if (!open) return;
    setHighlight(0);
    const timer = setTimeout(() => inputRef.current?.focus(), 0);
    function onDocMouseDown(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocMouseDown);
    return () => {
      clearTimeout(timer);
      document.removeEventListener("mousedown", onDocMouseDown);
    };
  }, [open]);

  function commit(next: string) {
    onChange(next);
    setOpen(false);
    setQuery("");
  }

  function create() {
    if (!onCreate) return;
    onCreate(query.trim());
    setOpen(false);
    setQuery("");
  }

  return (
    <div className={cn("relative", className)} ref={containerRef}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
        className="flex h-9 w-full items-center justify-between gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <span className={cn("truncate", !selected && !value && "text-muted-foreground")}>{selected?.label || value || placeholder}</span>
        <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md">
          <div className="border-b p-1">
            <input
              ref={inputRef}
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setHighlight(0);
              }}
              placeholder={searchPlaceholder}
              className="w-full rounded-sm bg-transparent px-2 py-1.5 text-sm outline-none placeholder:text-muted-foreground"
              onKeyDown={(event) => {
                if (event.key === "ArrowDown") {
                  event.preventDefault();
                  setHighlight((current) => Math.min(current + 1, filtered.length - 1));
                } else if (event.key === "ArrowUp") {
                  event.preventDefault();
                  setHighlight((current) => Math.max(current - 1, 0));
                } else if (event.key === "Enter") {
                  event.preventDefault();
                  if (filtered[highlight]) commit(filtered[highlight].value);
                  else if (allowCustom && query.trim()) commit(query.trim());
                } else if (event.key === "Escape") {
                  event.preventDefault();
                  setOpen(false);
                }
              }}
            />
          </div>
          <div className="max-h-60 overflow-auto p-1">
            {filtered.length === 0 && !onCreate && !(allowCustom && query.trim()) ? (
              <div className="px-2 py-1.5 text-sm text-muted-foreground">{emptyText}</div>
            ) : (
              filtered.map((option, index) => (
                <button
                  key={option.value}
                  type="button"
                  onMouseDown={(event) => {
                    event.preventDefault();
                    commit(option.value);
                  }}
                  onMouseEnter={() => setHighlight(index)}
                  className={cn(
                    "flex w-full items-center justify-between gap-2 rounded-sm px-2 py-1.5 text-left text-sm",
                    index === highlight ? "bg-muted" : "hover:bg-muted",
                  )}
                >
                  <span className="min-w-0 flex-1 truncate">
                    {option.label}
                    {option.hint ? <span className="ml-2 text-xs text-muted-foreground">{option.hint}</span> : null}
                  </span>
                  {option.value === value ? <Check className="h-4 w-4 shrink-0" /> : null}
                </button>
              ))
            )}
            {allowCustom && query.trim() && !filtered.some((option) => option.label.toLowerCase() === query.trim().toLowerCase()) ? (
              <button
                type="button"
                onMouseDown={(event) => {
                  event.preventDefault();
                  commit(query.trim());
                }}
                className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm hover:bg-muted"
              >
                <span className="truncate">Use “{query.trim()}”</span>
              </button>
            ) : null}
            {onCreate ? (
              <button
                type="button"
                onMouseDown={(event) => {
                  event.preventDefault();
                  create();
                }}
                className="mt-1 flex w-full items-center gap-2 rounded-sm border-t px-2 py-1.5 text-left text-sm font-medium text-primary hover:bg-muted"
              >
                <Plus className="h-4 w-4 shrink-0" />
                <span className="truncate">{query.trim() ? `Add “${query.trim()}”` : createLabel}</span>
              </button>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
