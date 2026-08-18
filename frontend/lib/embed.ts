import type { Row } from "./api";
import { prettyLine } from "./format";

// This app runs two ways: standalone, or embedded as an iframe inside the
// CostSeg Blazor app (the "Ask AI (RSMeans)" side panel on the Element form).
// When embedded, a result row can be pushed straight into the open form.
//
// The two apps sit on different origins, so postMessage is the only channel the
// browser allows. The Blazor side listens for this exact shape and validates our
// origin before applying anything:
//
//   { type: "rsmeans:select", payload: { csiNumber, description, unit, unitCost } }

export const SELECT_MESSAGE = "rsmeans:select";

export interface CostSegSelection {
  csiNumber?: string;
  description?: string;
  unit?: string;
  unitCost?: string;
  amount?: string;
  // Both cost figures, so CostSeg can ask the estimator which one to use:
  // new construction / improvement -> Bare Total; otherwise -> Total O&P.
  bareTotal?: string;
  totalOp?: string;
}

// The CostSeg Element form only accepts these units (DTO/Element.cs -> Units).
// RSMeans writes them differently ("L.F.", "Ea."),  so they are normalized.
const COSTSEG_UNITS = ["EA", "LF", "SF", "PCT", "LOT", "NA"];

export function normalizeUnit(
  unit: string | null | undefined,
  isPercent?: boolean
): string | undefined {
  // A percentage row (cost adjustment) maps to the form's PCT regardless of how
  // RSMeans labelled the column.
  if (isPercent) return "PCT";
  const cleaned = (unit || "").replace(/[^a-zA-Z]/g, "").toUpperCase();
  return COSTSEG_UNITS.includes(cleaned) ? cleaned : undefined;
}

// Are we inside an iframe? Only then is there a parent to send to. Call this
// from an effect, never during render
export function isEmbedded(): boolean {
  return typeof window !== "undefined" && window.parent !== window;
}

// Where to send. They never post to "*" — that would hand the payload to any page
// that manages to embed this app — so They need the parent's real origin, tried in
// three ways:
//
//  1. NEXT_PUBLIC_COSTSEG_ORIGIN, when it's pinned per environment.
//  2. The `parentOrigin` query param CostSeg puts on the iframe URL. This is the
//     one that normally answers, and it exists because of (3).
//  3. document.referrer — unreliable: CostSeg is https and this app is http, and
//     on that downgrade the browser strips the referrer entirely.
export function targetOrigin(): string | null {
  const configured = process.env.NEXT_PUBLIC_COSTSEG_ORIGIN?.replace(/\/$/, "");
  if (configured) return configured;

  if (typeof window !== "undefined") {
    const fromUrl = new URLSearchParams(window.location.search).get(
      "parentOrigin"
    );
    if (fromUrl) {
      try {
        return new URL(fromUrl).origin;
      } catch {
        /* malformed param — keep looking */
      }
    }
  }

  if (typeof document !== "undefined" && document.referrer) {
    try {
      return new URL(document.referrer).origin;
    } catch {
      /* malformed referrer — fall through */
    }
  }

  return null;
}

// Map an RSMeans row onto the CostSeg form fields.
// `amount` is deliberately absent: that's the take-off quantity the estimator
// enters, not something RSMeans knows.
export function rowToSelection(row: Row): CostSegSelection {
  // Total incl. O&P is the default the estimate is built on; bare total is the
  // fallback for rows RSMeans publishes without it. Both are sent so CostSeg can
  // let the estimator choose (new construction / improvement -> Bare Total).
  const price = row.total_op ?? row.bare_total;

  return {
    csiNumber: prettyLine(row.line_number),
    description: row.description,
    unit: normalizeUnit(row.unit, row.is_percent),
    unitCost: price != null ? String(price) : undefined,
    bareTotal: row.bare_total != null ? String(row.bare_total) : undefined,
    totalOp: row.total_op != null ? String(row.total_op) : undefined,
  };
}

// Push a row into the CostSeg form. Returns false when there's nowhere to send
// it (not embedded, or the parent origin couldn't be determined).
export function sendToCostSeg(row: Row): boolean {
  if (!isEmbedded()) return false;

  const origin = targetOrigin();
  if (!origin) {
    console.warn(
      "[embed] Can't determine the CostSeg origin. Set NEXT_PUBLIC_COSTSEG_ORIGIN."
    );
    return false;
  }

  window.parent.postMessage(
    { type: SELECT_MESSAGE, payload: rowToSelection(row) },
    origin
  );

  return true;
}
