import type { Row } from "@/lib/api";
import { currency, prettyLine } from "@/lib/format";

// The single, exact line the user asked for (direct code lookup). Highlighted
// because it's THE answer, not one row among many.
export function MatchedLineCard({ row }: { row: Row }) {
  return (
    <div className="overflow-hidden rounded-xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white shadow-sm">
      <div className="flex items-center justify-between border-b border-indigo-100 bg-indigo-50/60 px-5 py-2.5">
        <span className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
          Exact match
        </span>
        <code className="font-mono text-xs text-indigo-700">
          {prettyLine(row.line_number)}
        </code>
      </div>

      <div className="px-5 py-4">
        <p className="text-base font-medium text-slate-900">
          {row.description}
        </p>
        {row.unit && (
          <p className="mt-0.5 text-xs text-slate-500">per {row.unit}</p>
        )}

        <div className="mt-4 grid grid-cols-2 gap-3">
          <PriceTile label="Bare total" value={row.bare_total} />
          <PriceTile label="Total incl. O&P" value={row.total_op} accent />
        </div>
      </div>
    </div>
  );
}

function PriceTile({
  label,
  value,
  accent,
}: {
  label: string;
  value: number | null;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border px-4 py-3 ${
        accent
          ? "border-indigo-200 bg-white"
          : "border-slate-200 bg-slate-50/60"
      }`}
    >
      <div className="text-xs text-slate-500">{label}</div>
      <div
        className={`mt-0.5 text-xl font-semibold tabular-nums ${
          accent ? "text-indigo-700" : "text-slate-800"
        }`}
      >
        {currency(value)}
      </div>
    </div>
  );
}
