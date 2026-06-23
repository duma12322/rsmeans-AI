"use client";

import { useRef, useState } from "react";
import { ask, type AskResponse } from "@/lib/api";
import { AskForm } from "@/components/AskForm";
import { ResultView } from "@/components/ResultView";

interface Turn {
  id: string;
  query: string;
  response: AskResponse | null; // null while loading
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

  async function submit(text?: string) {
    const q = (text ?? input).trim();
    if (!q || loading) return;

    const id = crypto.randomUUID();
    setTurns((t) => [...t, { id, query: q, response: null }]);
    setInput("");
    setLoading(true);

    const res = await ask(
      sessionId ? { session_id: sessionId, answer: q } : { question: q }
    );

    setTurns((t) =>
      t.map((turn) => (turn.id === id ? { ...turn, response: res } : turn))
    );
    setSessionId(
      res.status === "needs_clarification" ? res.session_id : null
    );
    setLoading(false);
    requestAnimationFrame(() =>
      feedEnd.current?.scrollIntoView({ behavior: "smooth" })
    );
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
            className="rounded-lg px-3 py-1.5 text-xs font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
          >
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
                <LoadingCard />
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

function LoadingCard() {
  return (
    <div className="animate-pulse space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="h-3 w-1/3 rounded bg-slate-200" />
      <div className="h-20 rounded-lg bg-slate-100" />
      <div className="h-3 w-2/3 rounded bg-slate-200" />
    </div>
  );
}
