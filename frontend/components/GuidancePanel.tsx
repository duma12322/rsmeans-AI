import type { SubjectResponse } from "@/lib/api";

// needs_subject: the question named nothing to price ("what is the cost?").
// We DON'T show fake candidates — we teach how to ask, with real MasterFormat
// categories and example questions (clickable to drop into the input).
export function GuidancePanel({
  data,
  onExample,
}: {
  data: SubjectResponse;
  onExample: (text: string) => void;
}) {
  const { categories, how_to_ask } = data;

  return (
    <div className="space-y-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <header className="flex items-start gap-3">
        <Compass />
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            The cost of what?
          </h3>
          <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-400">
            {data.message?.split("\n")[0] ||
              "Tell me the item or work and I'll find it."}
          </p>
        </div>
      </header>

      {how_to_ask?.good_examples?.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Try one of these
          </p>
          <div className="flex flex-wrap gap-2">
            {how_to_ask.good_examples.map((ex) => (
              <button
                key={ex}
                onClick={() => onExample(ex)}
                className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-sm text-indigo-700 transition hover:bg-indigo-100 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-300 dark:hover:bg-indigo-500/20"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      {categories?.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Or browse a category
          </p>
          <div className="flex flex-wrap gap-1.5">
            {categories.map((c) => (
              <span
                key={c.code}
                className="rounded-md bg-slate-100 px-2.5 py-1 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300"
              >
                <span className="font-mono text-slate-400 dark:text-slate-500">
                  {c.code}
                </span>{" "}
                {c.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {how_to_ask?.rules?.length > 0 && (
        <ul className="space-y-1 border-t border-slate-100 pt-4 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
          {how_to_ask.rules.map((r, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-indigo-400">•</span>
              {r}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Compass() {
  return (
    <svg
      className="mt-0.5 h-5 w-5 flex-none text-indigo-500"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M15.5 8.5l-2 5-5 2 2-5 5-2z" strokeLinejoin="round" />
    </svg>
  );
}
