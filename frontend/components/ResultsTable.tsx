"use client";

import { useMemo, useState, type ReactNode } from "react";
import type { Row } from "@/lib/api";
import { currency, prettyLine, rowToTsv } from "@/lib/format";
import { copyText } from "@/lib/clipboard";
import { CopyButton } from "./CopyButton";

type SortKey = "line" | "description" | "unit" | "bare" | "op";
type SortDir = "asc" | "desc";

const num = (v: number | null | undefined) => v ?? 0;

// How many rows we show before the "show more" button appears, and how many
// each click reveals after that. A keyword search can return up to 200 lines;
// 50 keeps the first screen scannable, then the user pulls them in 100-row steps.
const COLLAPSED_LIMIT = 50;
const STEP = 100;

// Wrap every occurrence of a filter word in a highlight <mark>, so the keywords
// the user typed light up in each description. Splitting on ONE capturing group
// lands the matched pieces at odd indices — no regex lastIndex juggling.
function highlight(text: string, terms: string[]): ReactNode {
  const escaped = terms
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .filter(Boolean);
  if (escaped.length === 0) return text;
  const re = new RegExp(`(${escaped.join("|")})`, "gi");
  return text.split(re).map((part, i) =>
    i % 2 === 1 ? (
      <mark
        key={i}
        className="rounded-[2px] bg-amber-200 px-0.5 text-slate-900 dark:bg-amber-400/30 dark:text-amber-50"
      >
        {part}
      </mark>
    ) : (
      part
    )
  );
}

// The full grid of line-items under the chosen section. Filterable by text and
// sortable by any column. Click any value cell (code, unit, totals) to copy it;
// each row also has a copy button for the whole line.
export function ResultsTable({
  rows,
  highlightLine,
}: {
  rows: Row[];
  highlightLine?: string | null;
}) {
  const [copied, setCopied] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  // Two filter modalities: "words" matches each typed word anywhere (AND);
  // "phrase" is the old behavior — the whole string as one contiguous substring.
  const [mode, setMode] = useState<"words" | "phrase">("words");
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir } | null>(null);
  // How many rows are currently revealed; grows by STEP per "show more" click.
  const [visibleCount, setVisibleCount] = useState(COLLAPSED_LIMIT);

  const hl = (highlightLine || "").replace(/\D/g, "");

  const q = filter.trim().toLowerCase();
  // The filter words (for "words" mode). Same tokenization drives both the
  // filtering and the highlighting, so what filtered is what lights up.
  const terms = useMemo(() => q.split(/\s+/).filter(Boolean), [q]);
  // What to highlight: each word in "words" mode, the whole phrase in "phrase".
  const marks = mode === "phrase" ? (q ? [q] : []) : terms;

  const view = useMemo(() => {
    let out = rows ?? [];
    if (q) {
      const qDigits = q.replace(/\D/g, "");
      out = out.filter((r) => {
        const desc = r.description.toLowerCase();
        const lineDigits = r.line_number.replace(/\D/g, "");
        // "phrase": the exact string must appear contiguously (or its digits in
        // the line number). "words": every word must appear somewhere (AND), so
        // "cost addi" keeps "Cost adjustment… additional…".
        if (mode === "phrase") {
          return desc.includes(q) || (!!qDigits && lineDigits.includes(qDigits));
        }
        return terms.every((t) => {
          const tDigits = t.replace(/\D/g, "");
          return desc.includes(t) || (!!tDigits && lineDigits.includes(tDigits));
        });
      });
    }
    if (sort) {
      const dir = sort.dir === "asc" ? 1 : -1;
      out = [...out].sort((a, b) => {
        let cmp = 0;
        switch (sort.key) {
          case "line":
            cmp = a.line_number.localeCompare(b.line_number);
            break;
          case "description":
            cmp = a.description.localeCompare(b.description);
            break;
          case "unit":
            cmp = (a.unit || "").localeCompare(b.unit || "");
            break;
          case "bare":
            cmp = num(a.bare_total) - num(b.bare_total);
            break;
          case "op":
            cmp = num(a.total_op) - num(b.total_op);
            break;
        }
        return cmp * dir;
      });
    }
    return out;
  }, [rows, q, terms, mode, sort]);

  // Reveal the first `visibleCount` rows and pull the rest in STEP-sized steps.
  // The cap runs AFTER filter/sort, so "show more" reveals the rest of the
  // *current* view, not the raw list.
  const shown = view.slice(0, visibleCount);
  const hiddenCount = view.length - shown.length;
  const nextStep = Math.min(STEP, hiddenCount);
  const canExpand = hiddenCount > 0;
  const canCollapse = visibleCount > COLLAPSED_LIMIT && view.length > COLLAPSED_LIMIT;

  if (!rows?.length) {
    return (
      <p className="rounded-lg border border-slate-200 bg-white px-4 py-6 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
        No line items were found for this section.
      </p>
    );
  }

  async function copyCell(key: string, value: string) {
    if (await copyText(value)) {
      setCopied(key);
      setTimeout(() => setCopied((c) => (c === key ? null : c)), 1000);
    }
  }

  function toggleSort(key: SortKey) {
    setSort((s) =>
      s?.key === key
        ? s.dir === "asc"
          ? { key, dir: "desc" }
          : null // third click clears the sort
        : { key, dir: "asc" }
    );
  }

  // A sortable column header.
  function SortHeader({
    label,
    sortKey,
    align = "left",
  }: {
    label: string;
    sortKey: SortKey;
    align?: "left" | "right";
  }) {
    const active = sort?.key === sortKey;
    return (
      <th
        className={`px-4 py-2.5 font-medium ${
          align === "right" ? "text-right" : "text-left"
        }`}
      >
        <button
          type="button"
          onClick={() => toggleSort(sortKey)}
          className={`inline-flex items-center gap-1 transition hover:text-slate-700 dark:hover:text-slate-200 ${
            align === "right" ? "flex-row-reverse" : ""
          } ${active ? "text-slate-900 dark:text-slate-100" : ""}`}
        >
          {label}
          <span className="text-[10px] leading-none">
            {active ? (sort!.dir === "asc" ? "▲" : "▼") : "↕"}
          </span>
        </button>
      </th>
    );
  }

  // A clickable value cell. `copyValue` lands on the clipboard.
  function Cell({
    cellKey,
    copyValue,
    className = "",
    children,
  }: {
    cellKey: string;
    copyValue: string;
    className?: string;
    children: React.ReactNode;
  }) {
    const isCopied = copied === cellKey;
    return (
      <td
        onClick={() => copyCell(cellKey, copyValue)}
        title="Click to copy"
        className={`relative cursor-pointer select-none px-4 py-2 transition-colors hover:bg-indigo-50/60 dark:hover:bg-indigo-500/10 ${className}`}
      >
        {children}
        {isCopied && (
          <span className="animate-copied pointer-events-none absolute right-1 top-1 rounded bg-emerald-600 px-1.5 py-0.5 text-[10px] font-medium text-white shadow">
            Copied
          </span>
        )}
      </td>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-slate-50 px-4 py-2 dark:border-slate-700 dark:bg-slate-800/60">
        <span className="text-xs text-slate-500 dark:text-slate-400">
          {view.length === rows.length
            ? `${rows.length} line ${rows.length === 1 ? "item" : "items"}`
            : `${view.length} of ${rows.length}`}
          <span className="ml-2 hidden sm:inline">· click a value to copy</span>
        </span>
        <div className="flex items-center gap-2">
          {/* Toggle the two filter modalities. "Words" is the new per-word match
              (default); "Phrase" is the old contiguous-substring match. */}
          <div
            role="group"
            aria-label="Filter mode"
            className="flex rounded-lg border border-slate-300 p-0.5 text-[11px] dark:border-slate-600"
          >
            {(["words", "phrase"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                aria-pressed={mode === m}
                title={
                  m === "words"
                    ? "Match each word anywhere (e.g. “cost addi” → “Cost adjustment… additional…”)"
                    : "Match the exact phrase as typed, contiguously"
                }
                className={`rounded-md px-2 py-0.5 font-medium transition ${
                  mode === m
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                }`}
              >
                {m === "words" ? "Words" : "Phrase"}
              </button>
            ))}
          </div>
          <div className="relative">
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter…"
              className="w-44 rounded-lg border border-slate-300 bg-white py-1 pl-7 pr-2 text-xs text-slate-700 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200 dark:focus:ring-indigo-500/20"
            />
            <span className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-slate-400">
              <FilterIcon />
            </span>
          </div>
        </div>
      </div>

      <div className="scroll-thin overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
            <tr>
              <SortHeader label="Line #" sortKey="line" />
              <SortHeader label="Description" sortKey="description" />
              <SortHeader label="Unit" sortKey="unit" />
              <SortHeader label="Bare total" sortKey="bare" align="right" />
              <SortHeader label="Total O&P" sortKey="op" align="right" />
              <th className="px-2 py-2.5 text-right font-medium">
                <span className="sr-only">Copy</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {shown.map((r) => {
              const isHl = hl && r.line_number.replace(/\D/g, "") === hl;
              const k = r.line_number;
              const hasBare = num(r.bare_total) !== 0;
              const hasOp = num(r.total_op) !== 0;
              return (
                <tr
                  key={k}
                  className={`group ${
                    isHl
                      ? "bg-indigo-50/70 dark:bg-indigo-500/10"
                      : "hover:bg-slate-50 dark:hover:bg-slate-800/40"
                  }`}
                >
                  <Cell
                    cellKey={`${k}:line`}
                    copyValue={prettyLine(r.line_number)}
                    className="whitespace-nowrap font-mono text-xs text-slate-500 dark:text-slate-400"
                  >
                    {prettyLine(r.line_number)}
                  </Cell>
                  <Cell
                    cellKey={`${k}:desc`}
                    copyValue={r.description}
                    className="text-slate-800 dark:text-slate-200"
                  >
                    {highlight(r.description, marks)}
                  </Cell>
                  {r.unit ? (
                    <Cell
                      cellKey={`${k}:unit`}
                      copyValue={r.unit}
                      className="whitespace-nowrap text-slate-500 dark:text-slate-400"
                    >
                      {r.unit}
                    </Cell>
                  ) : (
                    <td className="whitespace-nowrap px-4 py-2 text-slate-500 dark:text-slate-400">
                      —
                    </td>
                  )}
                  {hasBare ? (
                    <Cell
                      cellKey={`${k}:bare`}
                      copyValue={String(r.bare_total)}
                      className="whitespace-nowrap text-right tabular-nums text-slate-700 dark:text-slate-300"
                    >
                      {currency(r.bare_total)}
                    </Cell>
                  ) : (
                    <td
                      title="No published bare price for this row"
                      className="whitespace-nowrap px-4 py-2 text-right tabular-nums text-slate-400 dark:text-slate-500"
                    >
                      {currency(r.bare_total)}
                    </td>
                  )}
                  {hasOp ? (
                    <Cell
                      cellKey={`${k}:op`}
                      copyValue={String(r.total_op)}
                      className="whitespace-nowrap text-right font-medium tabular-nums text-slate-900 dark:text-slate-100"
                    >
                      {currency(r.total_op)}
                    </Cell>
                  ) : (
                    <td
                      title="No published O&P price for this row"
                      className="whitespace-nowrap px-4 py-2 text-right font-medium tabular-nums text-slate-400 dark:text-slate-500"
                    >
                      {currency(r.total_op)}
                    </td>
                  )}
                  <td className="px-2 py-2 text-right">
                    <CopyButton
                      text={rowToTsv(r)}
                      title="Copy row"
                      className="opacity-0 group-hover:opacity-100 focus:opacity-100"
                    />
                  </td>
                </tr>
              );
            })}
            {view.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  className="px-4 py-6 text-center text-sm text-slate-500 dark:text-slate-400"
                >
                  No rows match “{filter}”.
                </td>
              </tr>
            )}
            {(canExpand || canCollapse) && (
              <tr>
                <td colSpan={6} className="px-4 py-3 text-center">
                  <div className="inline-flex items-center gap-2">
                    {canExpand && (
                      <button
                        type="button"
                        onClick={() => setVisibleCount((v) => v + STEP)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition hover:border-indigo-400 hover:text-indigo-700 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-indigo-500 dark:hover:text-indigo-300"
                      >
                        Show {nextStep} more<Chevron />
                      </button>
                    )}
                    {canCollapse && (
                      <button
                        type="button"
                        onClick={() => setVisibleCount(COLLAPSED_LIMIT)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition hover:border-indigo-400 hover:text-indigo-700 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-indigo-500 dark:hover:text-indigo-300"
                      >
                        Show fewer<Chevron up />
                      </button>
                    )}
                  </div>
                  {canExpand && (
                    <span className="ml-2 text-xs text-slate-400 dark:text-slate-500">
                      {hiddenCount} more hidden
                    </span>
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Chevron({ up = false }: { up?: boolean }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={up ? "rotate-180" : ""}
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}

function FilterIcon() {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M22 3H2l8 9.5V19l4 2v-8.5L22 3z" />
    </svg>
  );
}
