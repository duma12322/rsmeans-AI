"use client";

import { useState } from "react";
import type { OkResponse } from "@/lib/api";

// A keyword search returned too many rows to be exact. We still show the rows
// (never a dead end), but this panel guides the user to narrow: clickable
// descriptor chips + AI follow-up questions. Clicking a chip — or typing an
// answer — APPENDS to the original query via the kept session, re-running a
// narrower search. `onRefine` is the page's submit(): with a live session it
// sends { session_id, answer }.
export function RefinePanel({
  data,
  onRefine,
}: {
  data: OkResponse;
  onRefine: (text: string) => void;
}) {
  const questions = data.refine_questions ?? [];
  const chips = data.refinements ?? [];
  const [custom, setCustom] = useState("");

  function addCustom() {
    const t = custom.trim();
    if (!t) return;
    onRefine(t);
    setCustom("");
  }

  return (
    <div className="space-y-4 rounded-xl border border-amber-200 bg-amber-50/50 p-5 dark:border-amber-500/30 dark:bg-amber-500/5">
      <header className="flex items-start gap-3">
        <Filter />
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Too many matches — let&apos;s narrow it down
          </h3>
          <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-400">
            {data.total_records != null
              ? `Found ${data.total_records.toLocaleString()} matches — showing the first ${
                  data.shown_records ?? data.rows.length
                }.`
              : "That's a lot to be exact about."}{" "}
            Add a characteristic below — pick one or type your own — to get a
            shorter, more precise list.
          </p>
        </div>
      </header>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Add a characteristic
        </p>
        {chips.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {chips.map((c) => (
              <button
                key={c}
                onClick={() => onRefine(c)}
                className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-white px-3 py-1.5 text-sm text-indigo-700 transition hover:border-indigo-400 hover:bg-indigo-50 dark:border-indigo-500/30 dark:bg-slate-900 dark:text-indigo-300 dark:hover:bg-indigo-500/10"
              >
                <span className="text-indigo-400">+</span>
                {c}
              </button>
            ))}
          </div>
        )}
        {/* Free-text refinement: type any extra characteristic and it's appended
            to the current search (same as clicking a chip), not a new query. */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            addCustom();
          }}
          className="flex items-center gap-2"
        >
          <input
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            placeholder="Type another detail — e.g. interior, 2 coats, galvanized"
            className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:ring-indigo-500/20"
          />
          <button
            type="submit"
            disabled={!custom.trim()}
            className="flex-none rounded-lg bg-indigo-600 px-3.5 py-1.5 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Add
          </button>
        </form>
      </div>

      {questions.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            What to consider
          </p>
          <ul className="space-y-1.5">
            {questions.map((q, i) => (
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
            Add the matching characteristic above to narrow it down.
          </p>
        </div>
      )}
    </div>
  );
}

function Filter() {
  return (
    <svg
      className="mt-0.5 h-5 w-5 flex-none text-amber-500"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" />
    </svg>
  );
}
