import type { Row } from "@/lib/api";
import { currency, prettyLine } from "@/lib/format";
import { CopyButton } from "./CopyButton";

// The single, exact line the user asked for (direct code lookup). Highlighted
// because it's THE answer, not one row among many.
export function MatchedLineCard({ row }: { row: Row }) {
  return (
    <div className="overflow-hidden rounded-xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white shadow-sm dark:border-indigo-500/30 dark:from-indigo-500/10 dark:to-slate-900">
      <div className="flex items-center justify-between border-b border-indigo-100 bg-indigo-50/60 px-5 py-2.5 dark:border-indigo-500/20 dark:bg-indigo-500/10">
        <span className="text-xs font-semibold uppercase tracking-wide text-indigo-700 dark:text-indigo-300">
          Exact match
        </span>
        <div className="flex items-center gap-2">
          <code className="font-mono text-xs text-indigo-700 dark:text-indigo-300">
            {prettyLine(row.line_number)}
          </code>
          <CopyButton
            text={prettyLine(row.line_number)}
            title="Copy line number"
            className="text-indigo-400 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-200"
          />
        </div>
      </div>

      <div className="px-5 py-4">
        <p className="text-base font-medium text-slate-900 dark:text-slate-100">
          {row.description}
        </p>
        {row.unit && (
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            per {row.unit}
          </p>
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
  const hasValue = value !== null && value !== undefined && value !== 0;
  return (
    <div
      className={`group rounded-lg border px-4 py-3 ${
        accent
          ? "border-indigo-200 bg-white dark:border-indigo-500/30 dark:bg-slate-900"
          : "border-slate-200 bg-slate-50/60 dark:border-slate-700 dark:bg-slate-800/40"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500 dark:text-slate-400">
          {label}
        </span>
        {hasValue && (
          <CopyButton
            text={String(value)}
            title={`Copy ${label.toLowerCase()}`}
            className="opacity-0 group-hover:opacity-100 focus:opacity-100"
          />
        )}
      </div>
      <div
        className={`mt-0.5 text-xl font-semibold tabular-nums ${
          accent
            ? "text-indigo-700 dark:text-indigo-300"
            : "text-slate-800 dark:text-slate-200"
        }`}
      >
        {currency(value)}
      </div>
    </div>
  );
}
