"use client";

import { useEffect, useRef, useState } from "react";
import {
  Abbreviations,
  AbbreviationLevel,
  COSTSEG_DESCRIPTION_MAX,
  LEVEL_ORDER,
  LIMITS,
  abbreviateAllLocally,
  fetchAbbreviations,
} from "@/lib/abbreviate";

const LEVEL_LABELS: Record<AbbreviationLevel, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

// Shown when the chosen line's description doesn't fit the CostSeg field.
// The user picks one of three abbreviation levels (or edits the text)
export function AbbreviateDialog({
  description,
  onConfirm,
  onCancel,
}: {
  description: string;
  onConfirm: (text: string) => void;
  onCancel: () => void;
}) {
  // Start with the local rules so the dialog has content on the first paint;
  // the model's versions replace them when they arrive.
  const [levels, setLevels] = useState<Abbreviations>(() =>
    abbreviateAllLocally(description)
  );
  const [loading, setLoading] = useState(true);
  const [usedFallback, setUsedFallback] = useState(false);
  const [selected, setSelected] = useState<AbbreviationLevel>("low");
  const [text, setText] = useState("");
  // True once the user types: from then on their wording is never overwritten by
  // a level switch or by the model's answer landing late.
  const edited = useRef(false);

  useEffect(() => {
    const controller = new AbortController();

    fetchAbbreviations(description, controller.signal)
      .then((res) => {
        setLevels(res.levels);
        setUsedFallback(res.usedFallback);
        if (!edited.current) setText(res.levels.low ?? "");
      })
      .catch(() => {
        /* aborted — the dialog is gone */
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [description]);

  // Seed the editable field from the local suggestion until the fetch answers.
  useEffect(() => {
    if (!edited.current) setText(levels[selected] ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  useEffect(() => {
    if (!edited.current && !text) setText(levels.low ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [levels]);

  // Escape closes, as in any modal.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  function choose(level: AbbreviationLevel) {
    setSelected(level);
    // Picking a level is an explicit "use this one", so it overrides whatever
    // was typed — unlike the async arrival of the model's answer.
    edited.current = false;
    setText(levels[level] ?? "");
  }

  const length = text.trim().length;
  const tooLong = length > COSTSEG_DESCRIPTION_MAX;
  const canSend = length > 0 && !tooLong;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      onClick={onCancel}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Shorten description"
        // Clicks inside must not reach the backdrop's close handler.
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900"
      >
        <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-700">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Description too long
          </h3>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            The CostSeg field accepts {COSTSEG_DESCRIPTION_MAX} characters. Pick
            a shorter version or write your own.
          </p>
          <p className="mt-2 rounded-md bg-slate-50 px-2 py-1.5 text-xs text-slate-600 dark:bg-slate-800/60 dark:text-slate-300">
            {description}
            <span className="ml-1 font-medium text-rose-600 dark:text-rose-400">
              ({description.length})
            </span>
          </p>
        </div>

        <div className="space-y-1.5 px-4 py-3">
          {LEVEL_ORDER.map((level) => {
            const value = levels[level] ?? "";
            const active = selected === level && !edited.current;
            return (
              <button
                key={level}
                type="button"
                onClick={() => choose(level)}
                className={`flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left transition ${
                  active
                    ? "border-indigo-400 bg-indigo-50/60 dark:border-indigo-500/50 dark:bg-indigo-500/10"
                    : "border-slate-200 hover:border-indigo-300 dark:border-slate-700 dark:hover:border-indigo-500/40"
                }`}
              >
                <span className="w-14 flex-none text-[11px] font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  {LEVEL_LABELS[level]}
                </span>
                <span className="flex-1 text-sm text-slate-800 dark:text-slate-200">
                  {value || <span className="text-slate-400">…</span>}
                </span>
                <span className="flex-none text-[11px] tabular-nums text-slate-400 dark:text-slate-500">
                  {value.length}/{LIMITS[level]}
                </span>
              </button>
            );
          })}

          {loading && (
            <p className="pt-1 text-[11px] text-slate-400 dark:text-slate-500">
              Refining suggestions…
            </p>
          )}
          {!loading && usedFallback && (
            <p className="pt-1 text-[11px] text-amber-600 dark:text-amber-400">
              Backend unreachable — these are rule-based suggestions.
            </p>
          )}
        </div>

        <div className="border-t border-slate-200 px-4 py-3 dark:border-slate-700">
          <label className="block text-[11px] font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Text to send
          </label>
          <input
            value={text}
            onChange={(e) => {
              edited.current = true;
              setText(e.target.value);
            }}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-800 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200 dark:focus:ring-indigo-500/20"
          />
          <div className="mt-1 flex items-center justify-between">
            <span
              className={`text-[11px] tabular-nums ${
                tooLong
                  ? "text-rose-600 dark:text-rose-400"
                  : "text-slate-400 dark:text-slate-500"
              }`}
            >
              {length}/{COSTSEG_DESCRIPTION_MAX}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onCancel}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!canSend}
                onClick={() => onConfirm(text.trim())}
                className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
