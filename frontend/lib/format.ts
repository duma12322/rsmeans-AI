import type { Confidence } from "./api";

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

export const confidenceStyles: Record<Confidence, string> = {
  high: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  medium: "bg-amber-50 text-amber-700 ring-amber-600/20",
  low: "bg-rose-50 text-rose-700 ring-rose-600/20",
};
