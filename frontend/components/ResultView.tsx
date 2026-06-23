import type { AskResponse } from "@/lib/api";
import { ConfidenceBadge } from "./StatusBadge";
import { PathBreadcrumb } from "./PathBreadcrumb";
import { MatchedLineCard } from "./MatchedLineCard";
import { ResultsTable } from "./ResultsTable";
import { ClarificationPanel } from "./ClarificationPanel";
import { GuidancePanel } from "./GuidancePanel";

// Renders one backend response, branching on `status`. `onSuggest` feeds text
// back into the input (clicking a candidate / example / question answer).
export function ResultView({
  data,
  onSuggest,
  onRetry,
}: {
  data: AskResponse;
  onSuggest: (text: string) => void;
  onRetry?: () => void;
}) {
  if (data.status === "error") {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
        <span>{data.message}</span>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 rounded-lg border border-rose-300 bg-white px-3 py-1.5 text-xs font-medium text-rose-700 shadow-sm transition hover:bg-rose-100"
          >
            <RetryIcon />
            Retry
          </button>
        )}
      </div>
    );
  }

  if (data.status === "needs_subject") {
    return <GuidancePanel data={data} onExample={onSuggest} />;
  }

  if (data.status === "needs_clarification") {
    return <ClarificationPanel data={data} onAnswer={onSuggest} />;
  }

  // status === "ok"
  const single = data.matched_line && data.rows.length === 1;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">
            {data.final_name}
          </h2>
          <PathBreadcrumb path={data.path} />
        </div>
        <ConfidenceBadge value={data.confidence} />
      </div>

      {data.matched_line && <MatchedLineCard row={data.matched_line} />}

      {/* Show the table when there's more than the single matched line. */}
      {!single && (
        <ResultsTable
          rows={data.rows}
          highlightLine={data.matched_line?.line_number}
        />
      )}

      {data.fallback_used && (
        <p className="text-xs text-amber-600">
          Note: routing wasn&apos;t fully confident, so this section is a best
          effort. Refine your wording if it looks off.
        </p>
      )}
    </div>
  );
}

function RetryIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
      <path d="M3 3v5h5" />
    </svg>
  );
}
