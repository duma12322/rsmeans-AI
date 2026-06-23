"use client";

import { useEffect, useRef, useState } from "react";
import { askStream, type AskResponse, type Phase } from "@/lib/api";
import { AskForm } from "@/components/AskForm";
import { ResultView } from "@/components/ResultView";

interface Turn {
  id: string;
  query: string;
  response: AskResponse | null; // null while loading
  phase?: Phase; // live backend phase while loading
}

const STARTERS = [
  "Cost to paint interior walls",
  "What is the cost of code 26 56 13. 10 2870?",
  "Replace a residential water heater",
];

export default function Home() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  // Set while a clarification conversation is open; sent back as session_id.
  const [sessionId, setSessionId] = useState<string | null>(null);
  const feedEnd = useRef<HTMLDivElement>(null);

  function scrollToEnd() {
    requestAnimationFrame(() =>
      feedEnd.current?.scrollIntoView({ behavior: "smooth" })
    );
  }

  async function submit(text?: string) {
    const q = (text ?? input).trim();
    if (!q || loading) return;

    const id = crypto.randomUUID();
    setTurns((t) => [...t, { id, query: q, response: null }]);
    setInput("");
    setLoading(true);
    // Jump to the just-sent message (and its loading card) right away, instead
    // of waiting for the response to arrive.
    scrollToEnd();

    const res = await askStream(
      sessionId ? { session_id: sessionId, answer: q } : { question: q },
      (phase) =>
        setTurns((t) =>
          t.map((turn) => (turn.id === id ? { ...turn, phase } : turn))
        )
    );

    setTurns((t) =>
      t.map((turn) => (turn.id === id ? { ...turn, response: res } : turn))
    );
    setSessionId(
      res.status === "needs_clarification" ? res.session_id : null
    );
    setLoading(false);
    scrollToEnd();
  }

  function reset() {
    setTurns([]);
    setSessionId(null);
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
            <h1 className="text-sm font-semibold text-slate-900">
              RSMeans Cost Assistant
            </h1>
            <p className="text-xs text-slate-500">
              Ask in plain language, or by line number
            </p>
          </div>
        </div>
        {!empty && (
          <button
            onClick={reset}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
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
      </header>

      {/* Conversation feed */}
      <div className="flex-1 space-y-6 pb-4">
        {empty && (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">
              What would you like to price?
            </h2>
            <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
              Describe a single item as an action plus material, or paste an
              RSMeans line number in any format.
            </p>
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              {STARTERS.map((s) => (
                <button
                  key={s}
                  onClick={() => submit(s)}
                  className="rounded-full border border-slate-200 bg-slate-50 px-3.5 py-1.5 text-sm text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
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
                <ResultView data={turn.response} onSuggest={submit} />
              ) : (
                <LoadingCard phase={turn.phase} />
              )}
            </div>
          </div>
        ))}
        <div ref={feedEnd} />
      </div>

      {/* Input bar */}
      <div className="sticky bottom-0 -mx-4 border-t border-slate-200 bg-slate-50/90 px-4 py-4 backdrop-blur">
        <AskForm
          value={input}
          onChange={setInput}
          onSubmit={() => submit()}
          loading={loading}
          clarifying={sessionId !== null}
        />
        <p className="mt-2 text-center text-[11px] text-slate-400">
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

function LoadingCard({ phase }: { phase?: Phase }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const label = PHASE_LABELS[phase ?? "analyzing"];

  return (
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600" />
          <span className="text-sm font-medium text-slate-700">{label}</span>
        </div>
        <span className="text-xs tabular-nums text-slate-400">{elapsed}s</span>
      </div>
      <div className="animate-pulse space-y-3">
        <div className="h-16 rounded-lg bg-slate-100" />
        <div className="h-3 w-2/3 rounded bg-slate-200" />
      </div>
    </div>
  );
}
