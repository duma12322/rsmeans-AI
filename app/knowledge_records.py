"""
Knowledge records access layer.

Reads route_items.json (built by app/record_scraper.py) and exposes the REAL
RSMeans line-items that live under any tree path. This is what lets the AI
navigator decide and disambiguate using the actual catalog content of each
branch instead of only division-level keywords.

route_items.json shape:
    {division: {leaf_path: {"path": [...], "name": str,
                            "items": [{"line": str, "description": str}, ...]}}}

Prices are deliberately NOT stored here (they go stale); these descriptions are
used purely to GUIDE routing and the user.
"""
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUTE_ITEMS_PATH = os.path.join(BASE_DIR, "route_items.json")

_ROUTE_ITEMS = None


def _load():
    """Lazy-load and cache route_items.json (empty dict if missing/invalid)."""
    global _ROUTE_ITEMS
    if _ROUTE_ITEMS is None:
        try:
            with open(ROUTE_ITEMS_PATH, "r", encoding="utf-8") as f:
                _ROUTE_ITEMS = json.load(f)
        except (OSError, ValueError):
            _ROUTE_ITEMS = {}
    return _ROUTE_ITEMS


def has_records() -> bool:
    """True when a non-empty knowledge base is available."""
    return bool(_load())


def items_under(path, limit=None):
    """
    De-duplicated line-item descriptions under a tree path prefix.

    `path` is a list of codes, e.g. ["1", "0111", "011131"] (a branch) or a full
    leaf path. Every leaf whose key starts with this prefix contributes its
    items, in tree order, descriptions deduped (case-insensitive). `limit` caps
    how many are returned (None = all).
    """
    if not path:
        return []

    data = _load()
    leaves = data.get(path[0], {})
    prefix = " > ".join(path)

    out = []
    seen = set()
    for leaf_key, leaf in leaves.items():
        # Exact leaf, or any deeper leaf under this branch. The trailing " > "
        # guard stops "011131" from matching a sibling like "0111312".
        if leaf_key == prefix or leaf_key.startswith(prefix + " > "):
            for it in leaf.get("items", []):
                desc = it.get("description", "").strip()
                key = desc.lower()
                if desc and key not in seen:
                    seen.add(key)
                    out.append(desc)
                    if limit and len(out) >= limit:
                        return out
    return out


def find_by_line(code):
    """
    Resolve an explicit RSMeans line number to its exact leaf — no AI needed.

    `code` is matched on digits only, so "265613.10 2870", "265613102870" and
    "26 5613 1028 70" all resolve the same. An exact line match wins; otherwise
    the first leaf whose line STARTS WITH the code is returned (the user gave a
    shorter section-level code). Returns None when nothing matches.

    Result: {"path": [...], "name": str, "division": str,
             "match": "exact"|"prefix", "line": str, "description": str}
    """
    code = "".join(ch for ch in str(code) if ch.isdigit())
    if not code:
        return None

    data = _load()
    prefix_hit = None
    for division, leaves in data.items():
        for leaf in leaves.values():
            for it in leaf.get("items", []):
                line = "".join(ch for ch in it.get("line", "") if ch.isdigit())
                if not line:
                    continue
                if line == code:
                    return {
                        "path": leaf["path"], "name": leaf["name"],
                        "division": division, "match": "exact",
                        "line": it["line"], "description": it["description"],
                    }
                if prefix_hit is None and line.startswith(code):
                    prefix_hit = {
                        "path": leaf["path"], "name": leaf["name"],
                        "division": division, "match": "prefix",
                        "line": it["line"], "description": it["description"],
                    }
    return prefix_hit


_SEARCH_STOPWORDS = {
    "the", "of", "for", "a", "an", "to", "and", "or", "with", "in", "on", "at",
    "by", "cost", "costs", "price", "install", "installation", "replace",
    "repair", "per", "each", "new", "used", "type", "size",
    # Spanish filler — without these, "dame el ... de la" pollute the score.
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "y",
    "o", "con", "en", "por", "para", "que", "cual", "dame", "dime", "costo",
    "precio", "instalar", "reemplazar", "reparar", "cada", "nuevo", "tipo",
    "tamaño", "tamano",
}

# A reference to a place in the catalog ("section 31", "seccion 31") — its
# number is a LOCATION, not a dimension, so it must be stripped before
# tokenizing or it would be scored as a spec value and penalize every item.
_SECTION_REF = re.compile(
    r"\b(?:cap[ií]tulo|chapter|secci[oó]n|section|divisi[oó]n|division|div)"
    r"\s*#?\s*[\d.]+",
)


def _stem(word):
    """Very light normalization so 'excavations' matches 'excavation': drop a
    trailing plural 's' (and 'es') on words long enough for it to be safe."""
    if len(word) > 4 and word.endswith("es"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def _is_spec_value(token):
    """
    True for a numeric specification the user typed — a size, rating or
    dimension that pinpoints the exact catalog line ("4" inch, "200" amp,
    "40" gal). These are the strongest discriminators between near-identical
    items, so they must NOT be dropped as short tokens.
    """
    return any(ch.isdigit() for ch in token)


def _query_tokens(query):
    """
    Meaningful search tokens from a free-text query.

    Keeps alphabetic words of length >= 2 (minus stopwords) AND every numeric
    spec value regardless of length — a lone "4" or "2" is a size/rating
    ("4 inch", "2 ton") that identifies the exact line, so it must survive
    tokenization. Without this, "4 inch slab" and "6 inch slab" would score
    identically and the right record could not be told apart.
    """
    text = _SECTION_REF.sub(" ", str(query).lower())
    out = []
    for t in re.findall(r"[a-z0-9]+", text):
        if t in _SEARCH_STOPWORDS:
            continue
        if len(t) >= 2 or _is_spec_value(t):
            out.append(t)
    return out


def _token_hits(tokens, words):
    """
    How many query `tokens` are present in a description's `words` set, tolerant
    of plurals and minor variants: exact match, stem match, or (for longer
    tokens) one being a substring of the other.
    """
    word_stems = {_stem(w) for w in words}
    hits = 0
    for t in tokens:
        if t in words or _stem(t) in word_stems:
            hits += 1
        # Substring fallback only between LONG words, so a short description
        # token (e.g. "c" from "C.Y.") can't match inside a query word.
        elif len(t) >= 4 and any(len(w) >= 4 and (t in w or w in t) for w in words):
            hits += 1
    return hits


def search_items(query, within_path=None, limit=20):
    """
    Rank catalog item descriptions by a literal text match to `query` — a fast,
    AI-free lookup over route_items.json (like a scored Ctrl+F). Best first.

    score = fraction of the query's meaningful words present in the description
    (0..1), PLUS 1.0 when the whole query phrase appears as a substring. So an
    exact-wording hit scores ~2.0 and a partial word overlap scores <1.0.

    Numeric SPEC VALUES the user typed (a size/rating like "4" inch or "200"
    amp) are treated as discriminators: a description carrying every spec the
    user gave is rewarded, and one missing or contradicting a spec is pushed
    down — so "4 inch slab" outranks "6 inch slab" instead of tying it.

    `within_path` restricts the search to one branch (used while a conversation
    has a locked path). Returns dicts:
        {line, description, path, name, division, leaf_key, score}
    """
    tokens = _query_tokens(query)
    if not tokens:
        return []
    phrase = " ".join(tokens)
    spec_values = [t for t in tokens if _is_spec_value(t)]

    data = _load()
    prefix = " > ".join(within_path) if within_path else None

    results = []
    for division, leaves in data.items():
        if within_path and division != within_path[0]:
            continue
        for leaf_key, leaf in leaves.items():
            if prefix and not (leaf_key == prefix or leaf_key.startswith(prefix + " > ")):
                continue
            for it in leaf.get("items", []):
                desc_raw = it.get("description", "")
                desc = desc_raw.lower()
                words = set(re.findall(r"[a-z0-9]+", desc))
                hits = _token_hits(tokens, words)
                if not hits:
                    continue
                score = hits / len(tokens)
                if phrase in desc:
                    score += 1.0
                # Spec-value emphasis: the size/rating the user typed identifies
                # the exact line. Reward a description that carries every spec;
                # sink one that is missing or contradicts a spec the user gave.
                if spec_values:
                    matched = sum(1 for s in spec_values if s in words)
                    if matched == len(spec_values):
                        score += 0.5
                    else:
                        score -= 0.5 * (len(spec_values) - matched)
                results.append({
                    "line": it.get("line", ""),
                    "description": desc_raw,
                    "path": leaf["path"],
                    "name": leaf["name"],
                    "division": division,
                    "leaf_key": leaf_key,
                    "score": round(score, 3),
                })

    results.sort(key=lambda r: (-r["score"], len(r["description"])))
    return results[:limit]


def resolve_code(code):
    """
    Graded resolution of an explicit RSMeans code, best match first:

      "exact"   - a line number equals the code            -> that exact item
      "prefix"  - a line number STARTS WITH the code       -> user gave a short code
      "section" - the code falls UNDER a known leaf's code -> exact line not in our
                  snapshot, but we know its section (live scrape will have it)
      None      - the code matches nothing we know         -> caller must not guess

    Matching is digits-only, so separators/format don't matter.
    """
    code = "".join(ch for ch in str(code) if ch.isdigit())
    if not code:
        return None

    data = _load()
    prefix_hit = None
    section_hit = None
    section_len = -1

    for division, leaves in data.items():
        for leaf in leaves.values():
            leaf_digits = "".join(ch for ch in leaf["path"][-1] if ch.isdigit())
            # The requested code lives somewhere inside this leaf's grid.
            if leaf_digits and code.startswith(leaf_digits) and len(leaf_digits) > section_len:
                section_len = len(leaf_digits)
                section_hit = {
                    "path": leaf["path"], "name": leaf["name"],
                    "division": division, "match": "section",
                    "line": None, "description": None,
                }
            for it in leaf.get("items", []):
                line = "".join(ch for ch in it.get("line", "") if ch.isdigit())
                if not line:
                    continue
                if line == code:
                    return {
                        "path": leaf["path"], "name": leaf["name"],
                        "division": division, "match": "exact",
                        "line": it["line"], "description": it["description"],
                    }
                if prefix_hit is None and line.startswith(code):
                    prefix_hit = {
                        "path": leaf["path"], "name": leaf["name"],
                        "division": division, "match": "prefix",
                        "line": it["line"], "description": it["description"],
                    }

    return prefix_hit or section_hit


def options_preview(path, options, per_option=12, max_chars=4000):
    """
    For each child option, a short sample of the real items found beneath it.

    Returns a text block the navigator injects into the prompt so the model can
    match the user request against actual catalog content. Empty string when no
    option has any records (e.g. records not built yet, or root level where we
    rely on division keywords instead).
    """
    lines = []
    for o in options:
        child_path = list(path) + [o["code"]]
        sample = items_under(child_path, limit=per_option)
        if not sample:
            continue
        lines.append(f"- {o['code']} ({o['name']}): {'; '.join(sample)}")

    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars].rsplit("\n", 1)[0] + "\n  …(more items omitted)"
    return text
