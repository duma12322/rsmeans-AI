import { API_URL } from "./api";

// The CostSeg description field caps at 50 characters and many RSMeans lines run
// past it. Before sending, the user picks one of three progressively shorter
// versions. The backend asks the model for them (better wording, knows which
// detail matters); these local rules are the fallback for when it can't answer,
// so a down backend degrades the suggestions instead of blocking the send.

// What the CostSeg form accepts (DTO/Element.cs -> [StringLength(50)]).
export const COSTSEG_DESCRIPTION_MAX = 50;

export type AbbreviationLevel = "low" | "medium" | "high";

// Ceiling per level. "low" leaves headroom under 50 so the estimator can still
// append a note; "high" is the aggressive one.
export const LIMITS: Record<AbbreviationLevel, number> = {
  low: 45,
  medium: 35,
  high: 20,
};

export const LEVEL_ORDER: AbbreviationLevel[] = ["low", "medium", "high"];

export type Abbreviations = Partial<Record<AbbreviationLevel, string>>;

// Standard construction abbreviations, longest first so "reinforced concrete"
// doesn't get half-replaced. Applied whole-word only.
const ABBREVIATIONS: Array<[string, string]> = [
  ["galvanized", "galv"],
  ["reinforced", "reinf"],
  ["thickness", "thk"],
  ["insulated", "insul"],
  ["including", "incl"],
  ["aluminum", "alum"],
  ["concrete", "conc"],
  ["diameter", "dia"],
  ["standard", "std"],
  ["assembly", "assy"],
  ["material", "matl"],
  ["average", "avg"],
  ["maximum", "max"],
  ["minimum", "min"],
  ["exterior", "ext"],
  ["interior", "int"],
  ["horizontal", "horiz"],
  ["vertical", "vert"],
  ["copper", "Cu"],
  ["stainless", "SS"],
  ["square", "sq"],
  ["round", "rnd"],
  ["volt", "V"],
  ["gauge", "ga"],
  ["inch", "in"],
  ["foot", "ft"],
  ["feet", "ft"],
  ["pound", "lb"],
  ["number", "no"],
];

// Words that carry no identifying information in a cost line. Dropped before any
// real content is.
const FILLER = [
  "with",
  "and",
  "for",
  "the",
  "type",
  "each",
  "per",
  "of",
  "or",
  "to",
];

function applyDictionary(text: string): string {
  let out = text;
  for (const [long, short] of ABBREVIATIONS) {
    // \b = word boundary, so "involt" is untouched; "gi" = all matches, any case.
    out = out.replace(new RegExp(`\\b${long}s?\\b`, "gi"), short);
  }
  return out;
}

function dropFiller(text: string): string {
  return text
    .replace(new RegExp(`\\b(${FILLER.join("|")})\\b`, "gi"), " ")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+,/g, ",")
    .trim();
}

// Cut on a word boundary only — returns "" when not even the first word fits.
// Used where a severed word would be read as a typo rather than an abbreviation.
function truncateWords(text: string, limit: number): string {
  const clean = text.trim();
  if (clean.length <= limit) return clean;

  const space = clean.slice(0, limit + 1).lastIndexOf(" ");
  if (space <= 0) return "";

  return clean.slice(0, space).replace(/[\s,;:\-/]+$/, "");
}

// Cut on a word boundary rather than mid-word, unless that would gut the string.
function truncate(text: string, limit: number): string {
  const clean = text.trim();
  if (clean.length <= limit) return clean;

  let cut = clean.slice(0, limit).trimEnd();
  const space = cut.lastIndexOf(" ");
  if (space >= limit * 0.6) cut = cut.slice(0, space);

  return cut.replace(/[\s,;:\-/]+$/, "");
}

// A clause carrying a measurement: a number, a fraction, an inch/foot mark, a
// gauge/voltage/capacity, or a bare unit word. These are what tell two otherwise
// identical catalog lines apart ("3/4 inch" vs "1 inch" conduit), so they're the
// last thing to go — right after the item itself.
const MEASUREMENT =
  /\d|["'#%]|\b(in|inch|ft|foot|feet|lf|sf|sy|cy|ea|ga|awg|kv|amp|hp|lb|oz|gal|psi|mm|cm|dia|thk|thick|gauge|volt)\b/i;

// The last clause we're willing to drop: prefer one with no measurement in it,
// and never the first (that's the item). Returns -1 when only measurement-
// bearing clauses are left.
function lastDroppable(parts: string[]): number {
  for (let i = parts.length - 1; i > 0; i--) {
    if (!MEASUREMENT.test(parts[i])) return i;
  }
  return -1;
}

// Rule-based abbreviation, applied in escalating steps and stopping as soon as
// the text fits. Each step costs more meaning than the one before it: shorten
// words, drop filler, drop clauses that carry no measurement, drop the trailing
// measurement clauses, and only then cut.
export function abbreviateLocally(description: string, limit: number): string {
  const original = (description || "").trim();
  if (original.length <= limit) return original;

  let text = applyDictionary(original);
  if (text.length <= limit) return text;

  text = dropFiller(text);
  if (text.length <= limit) return text;

  const parts = text.split(",").map((p) => p.trim()).filter(Boolean);

  // First pass: shed descriptive clauses wherever they sit, keeping the sizes.
  // Without this, "EMT conduit, 3/4 inch, with couplings" would lose the size
  // (the last clause) instead of the couplings.
  while (parts.length > 1 && parts.join(", ").length > limit) {
    const i = lastDroppable(parts);
    if (i < 0) break;
    parts.splice(i, 1);
  }

  // Second pass: only measurement clauses are left. Make room by shortening the
  // ITEM instead of dropping them — "Electrical metallic tubing, 1/2 in" beats
  // "Electrical metallic tubing set screw", which fits but prices nothing in
  // particular. Measurements only start falling once the item has no room left.
  while (parts.length > 1 && parts.join(", ").length > limit) {
    const tail = parts.slice(1).join(", ");
    const head = truncateWords(parts[0], limit - tail.length - 2); // 2 = ", "

    // Below ~8 characters the item stops being recognizable ("galv, 3/4 in"),
    // and a measurement with nothing to attach it to is worse than one less
    // measurement — so shed a measurement instead and try again.
    if (head.length < 8) {
      parts.pop();
      continue;
    }

    return `${head}, ${tail}`;
  }

  return truncate(parts.join(", "), limit);
}

export function abbreviateAllLocally(description: string): Abbreviations {
  return {
    low: abbreviateLocally(description, LIMITS.low),
    medium: abbreviateLocally(description, LIMITS.medium),
    high: abbreviateLocally(description, LIMITS.high),
  };
}

// Ask the backend for model-written versions, falling back to the local rules.
// Any level the backend omits or returns over its limit is filled in locally, so
// the caller always gets all three.
export async function fetchAbbreviations(
  description: string,
  signal?: AbortSignal
): Promise<{ levels: Abbreviations; usedFallback: boolean }> {
  let fromApi: Abbreviations = {};
  let usedFallback = true;

  try {
    const res = await fetch(`${API_URL}/abbreviate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description }),
      signal,
    });
    if (res.ok) {
      const body = await res.json();
      if (body?.levels && typeof body.levels === "object") {
        fromApi = body.levels as Abbreviations;
        usedFallback = false;
      }
    }
  } catch (e) {
    // Aborted by the caller (dialog closed): let it through, there's no result
    // to fall back to either.
    if ((e as Error)?.name === "AbortError") throw e;
  }

  const levels: Abbreviations = {};
  for (const level of LEVEL_ORDER) {
    const value = (fromApi[level] || "").trim();
    levels[level] =
      value && value.length <= LIMITS[level]
        ? value
        : abbreviateLocally(description, LIMITS[level]);
  }

  return { levels, usedFallback };
}
