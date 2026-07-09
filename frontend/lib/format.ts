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

// The Bare Total / Total O&P columns are NOT always dollars: RSMeans flags some
// rows (cost adjustments, add-ons) as percentages. For those, render "10%" — not
// "$10.00" — so the value isn't misread as money. Everything else is currency.
export function amount(
  value: number | null | undefined,
  isPercent?: boolean
): string {
  if (value === null || value === undefined || value === 0) return "—";
  if (isPercent) {
    return `${value.toLocaleString("en-US", { maximumFractionDigits: 2 })}%`;
  }
  return currency(value);
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
  high: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-400/20",
  medium: "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-400/20",
  low: "bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-500/10 dark:text-rose-300 dark:ring-rose-400/20",
};
