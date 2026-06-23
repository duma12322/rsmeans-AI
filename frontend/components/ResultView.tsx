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
}: {
  data: AskResponse;
  onSuggest: (text: string) => void;
}) {
  if (data.status === "error") {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
        {data.message}
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
