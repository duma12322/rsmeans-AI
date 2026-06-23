import type { Row } from "@/lib/api";
import { currency, prettyLine } from "@/lib/format";

// The full grid of line-items under the chosen section. Numbers are right-
// aligned and tabular; the optional `highlightLine` row is tinted (the exact
// match, when the user pasted a full code).
export function ResultsTable({
  rows,
  highlightLine,
}: {
  rows: Row[];
  highlightLine?: string | null;
}) {
  if (!rows?.length) {
    return (
      <p className="rounded-lg border border-slate-200 bg-white px-4 py-6 text-center text-sm text-slate-500">
        No line items were found for this section.
      </p>
    );
  }

  const hl = (highlightLine || "").replace(/\D/g, "");

  return (
    <div className="scroll-thin overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-2.5 text-left font-medium">Line #</th>
            <th className="px-4 py-2.5 text-left font-medium">Description</th>
            <th className="px-4 py-2.5 text-left font-medium">Unit</th>
            <th className="px-4 py-2.5 text-right font-medium">Bare total</th>
            <th className="px-4 py-2.5 text-right font-medium">Total O&amp;P</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r) => {
            const isHl = hl && r.line_number.replace(/\D/g, "") === hl;
            return (
              <tr
                key={r.line_number}
                className={isHl ? "bg-indigo-50/70" : "hover:bg-slate-50"}
              >
                <td className="whitespace-nowrap px-4 py-2 font-mono text-xs text-slate-500">
                  {prettyLine(r.line_number)}
                </td>
                <td className="px-4 py-2 text-slate-800">{r.description}</td>
                <td className="whitespace-nowrap px-4 py-2 text-slate-500">
                  {r.unit || "—"}
                </td>
                <td className="whitespace-nowrap px-4 py-2 text-right tabular-nums text-slate-700">
                  {currency(r.bare_total)}
                </td>
                <td className="whitespace-nowrap px-4 py-2 text-right font-medium tabular-nums text-slate-900">
                  {currency(r.total_op)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
