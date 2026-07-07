"use client";

import { useEffect, useRef, useState } from "react";
import { askStream, type AskResponse, type Phase } from "@/lib/api";
import { AskForm } from "@/components/AskForm";
import { ResultView } from "@/components/ResultView";
import { ThemeToggle } from "@/components/ThemeToggle";

interface Turn {
  id: string;
  query: string;
  response: AskResponse | null; // null while loading
  phase?: Phase; // live backend phase while loading
}

const STARTERS = [
  "scissors, steel, security",
  "Cost to paint interior walls",
  "What is the cost of code 26 56 13. 10 2870?",
  "Replace a residential water heater",
];

// sessionStorage key for the persisted conversation (feed + open session_id), so
// a browser refresh continues the conversation instead of losing it.
const STORAGE_KEY = "rsmeans_conversation";

export default function Home() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  // Set while a clarification conversation is open; sent back as session_id.
  const [sessionId, setSessionId] = useState<string | null>(null);
  // True when the open session is a truncated-SEARCH refinement (not a
  // clarification). In that mode only chip clicks continue the search; typing a
  // fresh query in the box starts a NEW search instead of appending.
  const [refineOnly, setRefineOnly] = useState(false);
  const feedEnd = useRef<HTMLDivElement>(null);
  // Aborts the in-flight /ask/stream request when the user hits Stop.
  const abortRef = useRef<AbortController | null>(null);

  // Rehydrate the conversation on mount so a page reload doesn't drop an open
  // clarification: the backend still holds the session (conversations.json), but
  // the session_id lived only in React state, so a refresh forgot it. We mirror
  // both the feed and the session_id into sessionStorage (per-tab; cleared when
  // the tab closes) and read them back here. A turn that was still loading when
  // the page reloaded has no in-flight request anymore — surface it as
  // interrupted instead of a spinner that never resolves.
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw) as {
        turns?: Turn[];
        sessionId?: string | null;
        refineOnly?: boolean;
      };
      const restored = (saved.turns ?? []).map((t) =>
        t.response
          ? t
          : {
              ...t,
              phase: undefined,
              response: {
                status: "cancelled",
                message:
                  "This query was interrupted by a page reload — retry to run it again.",
              } as AskResponse,
            }
      );
      setTurns(restored);
      setSessionId(saved.sessionId ?? null);
      setRefineOnly(saved.refineOnly ?? false);
    } catch {
      /* corrupt or unavailable storage: start fresh, not fatal */
    }
  }, []);

  // Persist the feed + open session on every change (removing the key once the
  // conversation is cleared).
  useEffect(() => {
    try {
      if (turns.length === 0) sessionStorage.removeItem(STORAGE_KEY);
      else
        sessionStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ turns, sessionId, refineOnly })
        );
    } catch {
      /* quota exceeded / storage disabled: degrade to in-memory only */
    }
  }, [turns, sessionId, refineOnly]);

  function scrollToEnd() {
    requestAnimationFrame(() =>
      feedEnd.current?.scrollIntoView({ behavior: "smooth" })
    );
  }

  // `refine` marks a refinement of the current search (a chip click): it appends
  // to the open session. Plain typing/examples leave it false — so in a
  // truncated-search session, typed text starts a NEW search instead of being
  // glued onto the old query. Clarification sessions always continue (they have
  // no results yet, so the next message is necessarily an answer).
  async function submit(text?: string, opts?: { refine?: boolean }) {
    const q = (text ?? input).trim();
    if (!q || loading) return;

    const refine = opts?.refine ?? false;
    const useSession = !!sessionId && (refine || !refineOnly);

    const id = crypto.randomUUID();
    setTurns((t) => [...t, { id, query: q, response: null }]);
    setInput("");
    setLoading(true);
    // Jump to the just-sent message (and its loading card) right away, instead
    // of waiting for the response to arrive.
    scrollToEnd();

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await askStream(
        useSession ? { session_id: sessionId!, answer: q } : { question: q },
        (phase) =>
          setTurns((t) =>
            t.map((turn) => (turn.id === id ? { ...turn, phase } : turn))
          ),
        controller.signal
      );

      setTurns((t) =>
        t.map((turn) => (turn.id === id ? { ...turn, response: res } : turn))
      );
      // Keep the session alive while clarifying, and for a truncated search that
      // is still open for refinement (`continue_session`) — so a chip click
      // appends to the original query. `refineOnly` records which kind of open
      // session it is, so typed text is routed correctly (continue vs. new).
      if (res.status === "needs_clarification") {
        setSessionId(res.session_id);
        setRefineOnly(false);
      } else if (res.status === "ok" && res.continue_session) {
        setSessionId(res.session_id ?? null);
        setRefineOnly(true);
      } else {
        setSessionId(null);
        setRefineOnly(false);
      }
    } catch (e) {
      // User stopped the request: keep the turn (query + record) but swap the
      // loading card for a "paused" notice instead of erasing everything.
      if ((e as Error)?.name === "AbortError") {
        setTurns((t) =>
          t.map((turn) =>
            turn.id === id
              ? {
                  ...turn,
                  phase: undefined,
                  response: {
                    status: "cancelled",
                    message:
                      "Query paused — you stopped this request before it finished.",
                  },
                }
              : turn
          )
        );
      } else {
        setTurns((t) =>
          t.map((turn) =>
            turn.id === id
              ? {
                  ...turn,
                  response: { status: "error", message: "Something went wrong." },
                }
              : turn
          )
        );
      }
    } finally {
      abortRef.current = null;
      setLoading(false);
      scrollToEnd();
    }
  }

  function cancel() {
    abortRef.current?.abort();
  }

  function reset() {
    abortRef.current?.abort();
    setTurns([]);
    setSessionId(null);
    setRefineOnly(false);
    setInput("");
  }

  const empty = turns.length === 0;

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-4">
      {/* Header */}
      <header className="flex items-center justify-between py-6">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
            R
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              RSMeans Cost Assistant
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Ask in plain language, or by line number
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!empty && (
            <button
              onClick={reset}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-indigo-500 dark:hover:bg-slate-700 dark:hover:text-indigo-300"
            >
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
                <path d="M12 5v14M5 12h14" />
              </svg>
              New search
            </button>
          )}
          <ThemeToggle />
        </div>
      </header>

      {/* Conversation feed */}
      <div className="flex-1 space-y-6 pb-4">
        {empty && (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              What would you like to price?
            </h2>
            <p className="mx-auto mt-1 max-w-md text-sm text-slate-500 dark:text-slate-400">
              Search one item at a time — name the item first, then its
              characteristics (e.g. scissors, steel, security). Or paste an
              RSMeans line number in any format.
            </p>
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              {STARTERS.map((s) => (
                <button
                  key={s}
                  onClick={() => submit(s)}
                  className="rounded-full border border-slate-200 bg-slate-50 px-3.5 py-1.5 text-sm text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-indigo-500 dark:hover:bg-slate-700 dark:hover:text-indigo-300"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((turn) => (
          <div key={turn.id} className="space-y-3">
            {/* user query bubble */}
            <div className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-sm text-white shadow-sm">
                {turn.query}
              </div>
            </div>

            {/* bot response */}
            <div>
              {turn.response ? (
                <ResultView
                  data={turn.response}
                  onSuggest={submit}
                  onRefine={(t) => submit(t, { refine: true })}
                  onRetry={() => submit(turn.query)}
                />
              ) : (
                <LoadingCard phase={turn.phase} />
              )}
            </div>
          </div>
        ))}
        <div ref={feedEnd} />
      </div>

      {/* Input bar */}
      <div className="sticky bottom-0 -mx-4 border-t border-slate-200 bg-slate-50/90 px-4 py-4 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90">
        <AskForm
          value={input}
          onChange={setInput}
          onSubmit={() => submit()}
          onCancel={cancel}
          loading={loading}
          clarifying={sessionId !== null && !refineOnly}
        />
        <p className="mt-2 text-center text-[11px] text-slate-400 dark:text-slate-500">
          Prices are scraped live from RSMeans Online. This may open a browser
          window on the server and take a few seconds.
        </p>
      </div>
    </main>
  );
}

// Real backend phases streamed over SSE (see lib/api.ts askStream). Each maps to
// a human label; the seconds counter is live wall-clock. Before the first event
// arrives we default to "analyzing" (the backend emits it immediately).
const PHASE_LABELS: Record<Phase, string> = {
  analyzing: "Analyzing your question…",
  opening: "Opening RSMeans…",
  login: "Signing in…",
  navigating: "Browsing the catalog…",
  scraping: "Scanning live prices…",
};

// The backend emits these in order. The stepper fills up to (and including) the
// current one, so the user sees forward motion even while the clock keeps ticking
// — a bare rising counter reads as "stuck" once a healthy scrape passes ~15s.
const PHASE_ORDER: Phase[] = [
  "analyzing",
  "opening",
  "login",
  "navigating",
  "scraping",
];

function LoadingCard({ phase }: { phase?: Phase }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const current = phase ?? "analyzing";
  const idx = PHASE_ORDER.indexOf(current);
  const label = PHASE_LABELS[current];

  return (
    // role=status + aria-live announces each phase change to screen readers; the
    // per-second counter is aria-hidden so it isn't read aloud every tick.
    <div
      role="status"
      aria-live="polite"
      className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span
            className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600 dark:border-slate-700 dark:border-t-indigo-400"
            aria-hidden="true"
          />
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
            {label}
          </span>
        </div>
        <span
          className="text-xs tabular-nums text-slate-400 dark:text-slate-500"
          aria-hidden="true"
        >
          {elapsed}s
        </span>
      </div>

      {/* 5-phase progress: completed + current filled, the rest muted. */}
      <div className="flex gap-1.5" aria-hidden="true">
        {PHASE_ORDER.map((p, i) => (
          <span
            key={p}
            className={`h-1.5 flex-1 rounded-full transition-colors ${
              i < idx
                ? "bg-indigo-600 dark:bg-indigo-500"
                : i === idx
                  ? "animate-pulse bg-indigo-600 dark:bg-indigo-400"
                  : "bg-slate-200 dark:bg-slate-700"
            }`}
          />
        ))}
      </div>

      <p className="text-[11px] text-slate-400 dark:text-slate-500">
        Step {idx + 1} of {PHASE_ORDER.length} · this usually takes 15–30s
      </p>
    </div>
  );
}
