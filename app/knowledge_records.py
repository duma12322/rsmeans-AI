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
