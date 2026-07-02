import type {
  ClarifyResponse,
  DivisionCandidate,
  ItemCandidate,
} from "@/lib/api";
import { currency, prettyLine } from "@/lib/format";

function isItem(c: DivisionCandidate | ItemCandidate): c is ItemCandidate {
  return (c as ItemCandidate).line !== undefined;
}

// Ambiguous query: we DID find likely matches — present them (clickable to
// answer) and ask focused follow-up questions. Never a dead end.
export function ClarificationPanel({
  data,
  onAnswer,
}: {
  data: ClarifyResponse;
  onAnswer: (text: string) => void;
}) {
  const { candidates, clarify_questions, best_match } = data;

  return (
    <div className="space-y-5 rounded-xl border border-amber-200 bg-amber-50/40 p-5 dark:border-amber-500/30 dark:bg-amber-500/5">
      <header className="flex items-start gap-3">
        <Spark />
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            {candidates.length > 0
              ? "That could mean a few things"
              : "That search is a bit broad"}
          </h3>
          <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-400">
            {candidates.length > 0
              ? "Pick the closest match below, or answer a question to narrow it down."
              : "Add a bit more detail below and I'll find it."}
          </p>
        </div>
      </header>

      {candidates.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-2">
          {candidates.map((c) => {
            const item = isItem(c);
            const label = item ? c.line : c.code;
            const isBest =
              !item && best_match && c.code === best_match.code;
            return (
              <button
                key={label}
                onClick={() => onAnswer(label)}
                className="group flex flex-col items-start rounded-lg border border-slate-200 bg-white px-4 py-3 text-left transition hover:border-indigo-300 hover:shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:hover:border-indigo-500"
              >
                <div className="flex w-full items-center justify-between">
                  <code className="font-mono text-xs text-slate-500 dark:text-slate-400">
                    {item ? prettyLine(c.line) : c.code}
                  </code>
                  {isBest && (
                    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-400/20">
                      best match
                    </span>
                  )}
                </div>
                <span className="mt-1 text-sm font-medium text-slate-800 group-hover:text-indigo-700 dark:text-slate-200 dark:group-hover:text-indigo-300">
                  {item ? c.description : c.name}
                </span>
                {item && (c.leaf_name || c.section) && (
                  <span className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">
                    in {c.leaf_name || c.section}
                  </span>
                )}
                {item && (c.total_op != null || c.bare_total != null) && (
                  <span className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {currency(c.bare_total)} bare · {currency(c.total_op)} O&amp;P
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {clarify_questions.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            A few questions
          </p>
          <ul className="space-y-1.5">
            {clarify_questions.map((q, i) => (
              <li
                key={i}
                className="flex gap-2 text-sm text-slate-700 dark:text-slate-300"
              >
                <span className="font-semibold text-amber-600 dark:text-amber-400">
                  {i + 1}.
                </span>
                {q}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
            Type your answer below to keep refining this search.
          </p>
        </div>
      )}
    </div>
  );
}

function Spark() {
  return (
    <svg
      className="mt-0.5 h-5 w-5 flex-none text-amber-500"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden
    >
      <path d="M12 2l1.9 5.6L19.5 9l-4.4 3.3L16.5 18 12 14.8 7.5 18l1.4-5.7L4.5 9l5.6-1.4L12 2z" />
    </svg>
  );
}
