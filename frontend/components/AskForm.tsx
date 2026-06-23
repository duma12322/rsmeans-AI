"use client";

import { useEffect, useRef } from "react";

// The input bar. `clarifying` switches the placeholder/label so the user knows
// they're answering a follow-up rather than starting a new search.
export function AskForm({
  value,
  onChange,
  onSubmit,
  onCancel,
  loading,
  clarifying,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
  loading: boolean;
  clarifying: boolean;
}) {
  const ref = useRef<HTMLInputElement>(null);

  // Keep focus on the field after each turn so the conversation flows.
  useEffect(() => {
    if (!loading) ref.current?.focus();
  }, [loading]);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!loading && value.trim()) onSubmit();
      }}
      className="flex items-center gap-2"
    >
      <div className="relative flex-1">
        <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
          <SearchIcon />
        </span>
        <input
          ref={ref}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={loading}
          placeholder={
            clarifying
              ? "Type your answer…"
              : "e.g. Cost to paint interior walls — or — What is the cost of code 26 56 13. 10 2870?"
          }
          className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-4 text-sm shadow-sm outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 disabled:opacity-60"
        />
      </div>
      {loading ? (
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex items-center gap-2 rounded-xl border border-rose-300 bg-white px-5 py-3 text-sm font-medium text-rose-600 shadow-sm transition hover:bg-rose-50"
        >
          <StopIcon /> Stop
        </button>
      ) : (
        <button
          type="submit"
          disabled={!value.trim()}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {clarifying ? "Answer" : "Ask"}
        </button>
      )}
    </form>
  );
}

function StopIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" strokeLinecap="round" />
    </svg>
  );
}

