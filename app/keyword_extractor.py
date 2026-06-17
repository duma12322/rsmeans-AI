"""
Keyword extractor / knowledge-layer enricher.

For each division we rank the most relevant terms found in the grid line-items
scraped LIVE for that section (division_records.json, produced by
app/record_scraper.py) and append them, in place, to that division's "keywords"
list inside app/knowledge_layer.py. The scraped descriptions are the ONLY
keyword source — no pre-existing tree/name files are used.

Existing curated keywords are kept; only genuinely new terms are added (deduped,
case-insensitive). Running it repeatedly is safe/idempotent.

Run standalone:   python -m app.keyword_extractor
Or it runs automatically after each section in app/record_scraper.py.
"""
import json
import os
import re
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDS_PATH = os.path.join(BASE_DIR, "division_records.json")
KNOWLEDGE_PATH = os.path.join(BASE_DIR, "app", "knowledge_layer.py")

# How many auto-derived terms to keep per division.
TOP_N = 25

# Generic English words plus RSMeans pricing/qualifier noise (minimum, each,
# cost, ...) that carry no domain signal. These would otherwise pollute the
# permanently-written keyword lists.
STOPWORDS = {
    "and", "or", "of", "for", "the", "a", "an", "to", "in", "on", "with",
    "by", "from", "as", "at", "is", "are", "be", "this", "that", "these",
    "those", "other", "general", "common", "work", "results", "type",
    "types", "system", "systems", "equipment", "unit", "units", "misc",
    "miscellaneous", "various", "standard", "duty", "factor", "factors",
    "based", "per",
    # pricing / quantity qualifiers from line-item descriptions
    "minimum", "maximum", "average", "each", "cost", "costs", "over", "under",
    "total", "add", "deduct", "included", "including", "incl", "excl", "plus",
    "minus", "day", "days", "week", "month", "months", "year", "hour", "hours",
    "high", "low", "wide", "long", "deep", "thick", "size", "sizes", "use",
    "device", "rent", "value", "note", "item", "items", "set", "ea",
    # connectors / fragments that produce junk bigrams (see section, less than)
    "see", "section", "than", "less", "only", "both", "made", "etc", "above",
    "left", "right", "side", "sides", "single", "double", "plain", "fancy",
    "equal", "round", "medium", "soft", "old", "new", "first", "second",
    "complete", "manual", "automatic", "mounted", "posts", "track", "star",
    "form", "series", "level", "class", "price", "grade", "stock", "sheets",
    "squares", "square", "areas", "place", "pocket", "colors", "depth",
    "density", "passes", "load",
    # generic words too broad to help routing
    "material", "materials", "building", "construction", "project",
    "economy", "deluxe", "premium", "heavy", "light", "lights",
    # measurement / spec units that only form fragments (mbh input, gpm psi)
    "psi", "gpm", "mbh", "rpm", "fpm", "mph", "cfm", "kva", "kcmil", "kvar",
    "gpd", "mgd", "bhp", "cycle", "amp", "amps", "watt", "watts", "volt",
    "input", "output", "capacity", "discharge", "radius", "gal", "mils",
    "thk", "diam", "dlh", "slh", "rib", "std", "fin",
}

# RSMeans phrases that prefix almost every branch and say nothing about scope.
BOILERPLATE = [
    "common work results for",
    "operation and maintenance of",
    "operation and maint. of",
    "selective demolition for",
    "selective demolition",
    "maintenance of",
    "labor adjustment factors",
    "labor adjustments",
    "labor adjustment",
    "cleaning of",
    "pointing",
]

# Tokens that, inside a 2-word term, mark it as a measurement/spec fragment.
# Only units/specs here — NOT generic words like "out"/"exit", which appear in
# legitimate terms ("strip out", "exit device").
_BLOCK_TOKENS = {
    "psi", "gpm", "mbh", "rpm", "fpm", "mph", "cfm", "kva", "kcmil", "kvar",
    "gpd", "mgd", "bhp", "amp", "amps", "watt", "watts", "volt", "input",
    "output", "capacity", "discharge", "radius", "cycle", "passes", "load",
}

# Specific two-word fragments that are real words but carry no routing signal.
_FRAGMENT_DENY = {
    "lock out", "entry exit", "physical search", "search entry",
    "same hole", "forms place", "tipped legs", "direct chute",
    "thickness same", "left place", "drive extract", "than tall",
}

_WORD_RE = re.compile(r"[a-z][a-z\-']*[a-z]|[a-z]")


def _is_noise(term):
    """True for degenerate doubles, measurement fragments, and known junk."""
    toks = term.split()
    if len(toks) == 2 and toks[0] == toks[1]:        # "gal gal", "diam diam"
        return True
    if term in _FRAGMENT_DENY:
        return True
    if len(toks) == 2 and any(t in _BLOCK_TOKENS for t in toks):
        return True
    return False


def _strip_boilerplate(name):
    text = name.lower()
    for phrase in BOILERPLATE:
        text = text.replace(phrase, " ")
    return text


def _tokens(name):
    """Return the meaningful words (unigrams) from a single text string."""
    text = _strip_boilerplate(name)
    return [w for w in _WORD_RE.findall(text) if w not in STOPWORDS and len(w) > 2]


def _rank_terms(names, top_n=TOP_N):
    """Rank terms by frequency, mixing strong bigrams with unigrams."""
    unigrams = Counter()
    bigrams = Counter()

    for name in names:
        toks = _tokens(name)
        unigrams.update(toks)
        for a, b in zip(toks, toks[1:]):
            bigrams.update([f"{a} {b}"])

    # Keep bigrams that recur — they capture real phrases ("water heater",
    # "fire alarm") that a bare unigram would split.
    strong_bigrams = [(bg, c) for bg, c in bigrams.items() if c >= 3]

    # Drop unigrams that only ever appear inside a kept bigram.
    covered = set()
    for bg, _ in strong_bigrams:
        covered.update(bg.split())

    scored = list(strong_bigrams)
    scored += [(w, c) for w, c in unigrams.items() if w not in covered]
    scored.sort(key=lambda x: (-x[1], x[0]))

    ranked = [term for term, _ in scored if not _is_noise(term)]
    return ranked[:top_n]


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _merge_keywords(existing, new_terms):
    """Curated/existing first, then new terms not already present (case-insensitive)."""
    seen = {k.lower() for k in existing}
    merged = list(existing)
    for term in new_terms:
        if term.lower() not in seen:
            merged.append(term)
            seen.add(term.lower())
    return merged


def _serialize_knowledge(knowledge):
    """Render the DIVISION_KNOWLEDGE dict back to a Python literal block."""
    lines = ["DIVISION_KNOWLEDGE = {"]
    for code, entry in knowledge.items():
        lines.append(f"    {json.dumps(code)}: {{")
        lines.append(f'        "description": {json.dumps(entry["description"], ensure_ascii=False)},')
        lines.append(f'        "keywords": {json.dumps(entry["keywords"], ensure_ascii=False)},')
        lines.append(f'        "not": {json.dumps(entry["not"], ensure_ascii=False)}')
        lines.append("    },")
    lines.append("}")
    return "\n".join(lines)


def _rewrite_knowledge_layer(knowledge):
    """Replace the DIVISION_KNOWLEDGE block in knowledge_layer.py in place."""
    with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    start = text.index("DIVISION_KNOWLEDGE = {")
    # The dict closes on a line that is exactly "}" at column 0 ("\n}").
    end = text.index("\n}", start)

    new_block = _serialize_knowledge(knowledge)
    updated = text[:start] + new_block + text[end + 2:]

    with open(KNOWLEDGE_PATH, "w", encoding="utf-8") as f:
        f.write(updated)


def generate(records_path=RECORDS_PATH):
    """Rank keywords from the scraped records and enrich knowledge_layer.py."""
    # Imported lazily so a partial/edited knowledge_layer never breaks import.
    from app.knowledge_layer import DIVISION_KNOWLEDGE

    records = _load_json(records_path, {})

    added = 0
    for code, entry in DIVISION_KNOWLEDGE.items():
        descriptions = records.get(code)
        if not descriptions:
            continue
        ranked = _rank_terms(descriptions)
        before = len(entry["keywords"])
        entry["keywords"] = _merge_keywords(entry["keywords"], ranked)
        added += len(entry["keywords"]) - before

    _rewrite_knowledge_layer(DIVISION_KNOWLEDGE)

    print(f"[keyword_extractor] added {added} new keywords from scraped records "
          f"-> {os.path.relpath(KNOWLEDGE_PATH, BASE_DIR)}")
    return DIVISION_KNOWLEDGE


if __name__ == "__main__":
    generate()
