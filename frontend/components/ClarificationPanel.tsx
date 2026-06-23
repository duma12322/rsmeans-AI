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
    <div className="space-y-5 rounded-xl border border-amber-200 bg-amber-50/40 p-5">
      <header className="flex items-start gap-3">
        <Spark />
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            That could mean a few things
          </h3>
          <p className="mt-0.5 text-sm text-slate-600">
            Pick the closest match below, or answer a question to narrow it down.
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
                className="group flex flex-col items-start rounded-lg border border-slate-200 bg-white px-4 py-3 text-left transition hover:border-indigo-300 hover:shadow-sm"
              >
                <div className="flex w-full items-center justify-between">
                  <code className="font-mono text-xs text-slate-500">
                    {item ? prettyLine(c.line) : c.code}
                  </code>
                  {isBest && (
                    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                      best match
                    </span>
                  )}
                </div>
                <span className="mt-1 text-sm font-medium text-slate-800 group-hover:text-indigo-700">
                  {item ? c.description : c.name}
                </span>
                {item && (c.total_op != null || c.bare_total != null) && (
                  <span className="mt-1 text-xs text-slate-500">
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
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            A few questions
          </p>
          <ul className="space-y-1.5">
            {clarify_questions.map((q, i) => (
              <li key={i} className="flex gap-2 text-sm text-slate-700">
                <span className="font-semibold text-amber-600">{i + 1}.</span>
                {q}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-slate-500">
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
