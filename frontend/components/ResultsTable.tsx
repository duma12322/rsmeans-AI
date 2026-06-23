"use client";

import { useState } from "react";
import type { Row } from "@/lib/api";
import { currency, prettyLine, rowToTsv } from "@/lib/format";
import { copyText } from "@/lib/clipboard";
import { CopyButton } from "./CopyButton";

// The full grid of line-items under the chosen section. Numbers are right-
// aligned and tabular; the optional `highlightLine` row is tinted (the exact
// match). Click any value cell (code or a total) to copy it; each row also has
// a copy button for the whole line.
export function ResultsTable({
  rows,
  highlightLine,
}: {
  rows: Row[];
  highlightLine?: string | null;
}) {
  // Key of the cell most recently copied, e.g. "2:op", for a brief "Copied" tag.
  const [copied, setCopied] = useState<string | null>(null);

  if (!rows?.length) {
    return (
      <p className="rounded-lg border border-slate-200 bg-white px-4 py-6 text-center text-sm text-slate-500">
        No line items were found for this section.
      </p>
    );
  }

  const hl = (highlightLine || "").replace(/\D/g, "");

  async function copyCell(key: string, value: string) {
    if (await copyText(value)) {
      setCopied(key);
      setTimeout(() => setCopied((c) => (c === key ? null : c)), 1000);
    }
  }

  // A clickable value cell. `copyValue` is what lands on the clipboard; the
  // visible content is `children`. Renders a transient "Copied" tag on click.
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
        className={`relative cursor-pointer select-none px-4 py-2 transition-colors hover:bg-indigo-50/60 ${className}`}
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
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs text-slate-500">
        <span>
          {rows.length} line {rows.length === 1 ? "item" : "items"}
        </span>
        <span>Tip: click a value to copy</span>
      </div>

      <div className="scroll-thin overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2.5 text-left font-medium">Line #</th>
              <th className="px-4 py-2.5 text-left font-medium">Description</th>
              <th className="px-4 py-2.5 text-left font-medium">Unit</th>
              <th className="px-4 py-2.5 text-right font-medium">Bare total</th>
              <th className="px-4 py-2.5 text-right font-medium">Total O&amp;P</th>
              <th className="px-2 py-2.5 text-right font-medium">
                <span className="sr-only">Copy</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((r) => {
              const isHl = hl && r.line_number.replace(/\D/g, "") === hl;
              const k = r.line_number;
              const hasBare =
                r.bare_total !== null &&
                r.bare_total !== undefined &&
                r.bare_total !== 0;
              const hasOp =
                r.total_op !== null &&
                r.total_op !== undefined &&
                r.total_op !== 0;
              return (
                <tr
                  key={k}
                  className={`group ${
                    isHl ? "bg-indigo-50/70" : "hover:bg-slate-50"
                  }`}
                >
                  <Cell
                    cellKey={`${k}:line`}
                    copyValue={prettyLine(r.line_number)}
                    className="whitespace-nowrap font-mono text-xs text-slate-500"
                  >
                    {prettyLine(r.line_number)}
                  </Cell>
                  <Cell
                    cellKey={`${k}:desc`}
                    copyValue={r.description}
                    className="text-slate-800"
                  >
                    {r.description}
                  </Cell>
                  {r.unit ? (
                    <Cell
                      cellKey={`${k}:unit`}
                      copyValue={r.unit}
                      className="whitespace-nowrap text-slate-500"
                    >
                      {r.unit}
                    </Cell>
                  ) : (
                    <td className="whitespace-nowrap px-4 py-2 text-slate-500">
                      —
                    </td>
                  )}
                  {hasBare ? (
                    <Cell
                      cellKey={`${k}:bare`}
                      copyValue={String(r.bare_total)}
                      className="whitespace-nowrap text-right tabular-nums text-slate-700"
                    >
                      {currency(r.bare_total)}
                    </Cell>
                  ) : (
                    <td className="whitespace-nowrap px-4 py-2 text-right tabular-nums text-slate-700">
                      {currency(r.bare_total)}
                    </td>
                  )}
                  {hasOp ? (
                    <Cell
                      cellKey={`${k}:op`}
                      copyValue={String(r.total_op)}
                      className="whitespace-nowrap text-right font-medium tabular-nums text-slate-900"
                    >
                      {currency(r.total_op)}
                    </Cell>
                  ) : (
                    <td className="whitespace-nowrap px-4 py-2 text-right font-medium tabular-nums text-slate-900">
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
          </tbody>
        </table>
      </div>
    </div>
  );
}
