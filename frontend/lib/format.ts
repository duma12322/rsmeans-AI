import type { Confidence, Row } from "./api";

// RSMeans stores no price for header/section rows -> 0 or null. Show those as a
// dash rather than a misleading "$0.00".
export function currency(value: number | null | undefined): string {
  if (value === null || value === undefined || value === 0) return "—";
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// "265613102870" -> "26 56 13 10 28 70" for readability (RSMeans 2+2+2+2+2+2).
export function prettyLine(line: string): string {
  const digits = (line || "").replace(/\D/g, "");
  if (digits.length < 6) return line;
  return digits.replace(/(\d{2})(?=\d)/g, "$1 ").trim();
}

// One result row as a tab-separated line — pastes cleanly into a spreadsheet
// cell-by-cell. Used for the per-row "copy" action.
export function rowToTsv(r: Row): string {
  const cell = (v: number | null | undefined) =>
    v === null || v === undefined || v === 0 ? "" : String(v);
  return [
    prettyLine(r.line_number),
    r.description,
    r.unit || "",
    cell(r.bare_total),
    cell(r.total_op),
  ].join("\t");
}

export const confidenceStyles: Record<Confidence, string> = {
  high: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  medium: "bg-amber-50 text-amber-700 ring-amber-600/20",
  low: "bg-rose-50 text-rose-700 ring-rose-600/20",
};
