"use client";

import { useEffect, useState } from "react";
import type { Row } from "@/lib/api";
import { isEmbedded, sendToCostSeg } from "@/lib/embed";
import { COSTSEG_DESCRIPTION_MAX } from "@/lib/abbreviate";
import { AbbreviateDialog } from "./AbbreviateDialog";

// Pushes one row into the CostSeg Element form open behind this panel.
// Renders nothing when the app isn't embedded — standalone there's no form to
// send to, so the button would be a dead end.
export function SendToFormButton({
  row,
  label,
  className = "",
}: {
  row: Row;
  label?: string;
  className?: string;
}) {
  // `isEmbedded` reads `window`, which doesn't exist during SSR. Resolving it in
  // an effect keeps the server and first client render identical.
  const [embedded, setEmbedded] = useState(false);
  const [state, setState] = useState<"idle" | "sent" | "failed">("idle");
  // Open while the user picks how to shorten a description that doesn't fit.
  const [shortening, setShortening] = useState(false);

  useEffect(() => setEmbedded(isEmbedded()), []);

  if (!embedded) return null;

  function send(description?: string) {
    // A failed send is shown, not swallowed: silently doing nothing on click
    // reads as a broken button with no way to tell why.
    const ok = sendToCostSeg(row, description);
    setState(ok ? "sent" : "failed");
    setTimeout(() => setState("idle"), ok ? 1200 : 2500);
  }

  function onClick() {
    // Over the form's cap, the user chooses the wording instead of CostSeg
    // truncating mid-word — that cut usually lands on the detail that
    // identifies the line (gauge, voltage, type code).
    if ((row.description || "").length > COSTSEG_DESCRIPTION_MAX) {
      setShortening(true);
      return;
    }
    send();
  }

  const failed = state === "failed";

  return (
    <>
    <button
      type="button"
      onClick={onClick}
      title={
        failed
          ? "Couldn't reach the CostSeg form — check the browser console"
          : "Send this line to the CostSeg description form"
      }
      aria-label="Send to form"
      className={
        "inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 transition " +
        (failed
          ? "text-rose-600 dark:text-rose-400 "
          : "text-slate-500 hover:bg-indigo-50 hover:text-indigo-600 dark:text-slate-400 dark:hover:bg-indigo-500/10 dark:hover:text-indigo-400 ") +
        className
      }
    >
      {state === "sent" ? <CheckIcon /> : failed ? <AlertIcon /> : <SendIcon />}
      {label && (
        <span className="text-xs font-medium">
          {state === "sent" ? "Sent" : failed ? "Failed" : label}
        </span>
      )}
    </button>

    {shortening && (
      <AbbreviateDialog
        description={row.description}
        onCancel={() => setShortening(false)}
        onConfirm={(text) => {
          setShortening(false);
          send(text);
        }}
      />
    )}
    </>
  );
}

function SendIcon() {
  return (
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
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </svg>
  );
}

function AlertIcon() {
  return (
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
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v5M12 16h.01" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-emerald-600"
      aria-hidden="true"
    >
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}
