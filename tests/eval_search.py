"""
Text-search accuracy eval — the "score method".

Measures how well the AI-free catalog search (app.knowledge_records.search_items)
maps natural-language wording to the correct RSMeans line item, by comparing the
user input against the EXPECTED result. No browser, no AI — a pure, fast
regression gate for the knowledge-base search quality. Run it before/after any
change to search_items, the scoring, or route_items.json.

Two measurements:
  - CURATED:    realistic phrasings -> the exact line they should resolve to.
  - ROUND-TRIP: each distinctive item's own description must find it back at #1
                (self-consistency over a deterministic sample of the catalog).

Run:  python -m tests.eval_search
"""
import re

from app.knowledge_records import search_items, _load

# (query, expected_line_number) — how a user might ask vs the line it must hit.
CASES = [
    ("steel mesh mats", "313613100400"),
    ("galvanized steel mesh mats", "313613100400"),
    ("asphalt shingles", "070505103170"),
    ("hollow metal door", "081313130010"),
    ("welded wire fabric", "032213100010"),
    ("suspended acoustic ceiling", "095123100010"),
    ("cast iron pipe", "024113382700"),
    ("Including excavations, concrete, 50 lb", "316326130015"),
]


def _digits(s):
    return "".join(c for c in str(s) if c.isdigit())


def _rank_of(line, results):
    """0-based rank of `line` in results, or None if absent."""
    target = _digits(line)
    for i, r in enumerate(results):
        if _digits(r["line"]) == target:
            return i
    return None


def curated():
    top1 = top3 = 0
    rr_sum = 0.0
    print("=" * 80)
    print("CURATED CASES (realistic wording -> expected line)")
    print("=" * 80)
    for q, expected in CASES:
        results = search_items(q, limit=10)
        rank = _rank_of(expected, results)
        score = results[0]["score"] if results else 0.0

        if rank is None:
            flag = "MISS"
        elif rank == 0:
            flag = "TOP1"; top1 += 1; top3 += 1; rr_sum += 1.0
        elif rank < 3:
            flag = "TOP3"; top3 += 1; rr_sum += 1.0 / (rank + 1)
        else:
            flag = "FAR "; rr_sum += 1.0 / (rank + 1)

        rank_str = "-" if rank is None else f"#{rank + 1}"
        print(f"[{flag}] {q!r:44} -> {expected} at {rank_str:>3}  top-score={score:.2f}")

    n = len(CASES)
    print("-" * 80)
    print(f"Top-1: {top1}/{n} ({100 * top1 / n:.0f}%)   "
          f"Top-3: {top3}/{n} ({100 * top3 / n:.0f}%)   "
          f"MRR: {rr_sum / n:.2f}")
    return top1, n


def roundtrip(step=137, min_words=4):
    """Each distinctive item's own description should find it back at #1."""
    items = [
        it
        for leaves in _load().values()
        for leaf in leaves.values()
        for it in leaf.get("items", [])
        if it.get("line") and len(re.findall(r"[a-z0-9]+", it.get("description", "").lower())) >= min_words
    ]
    sample = items[::step]

    top1 = sum(
        1 for it in sample
        if _rank_of(it["line"], search_items(it["description"], limit=5)) == 0
    )
    n = len(sample) or 1
    print("\n" + "=" * 80)
    print("ROUND-TRIP SELF-TEST (each description must find its own line at #1)")
    print("=" * 80)
    print(f"Top-1: {top1}/{len(sample)} ({100 * top1 / n:.0f}%)   "
          f"[distinctive items, sampled every {step}]")
    return top1, len(sample)


def main():
    curated()
    roundtrip()


if __name__ == "__main__":
    main()
