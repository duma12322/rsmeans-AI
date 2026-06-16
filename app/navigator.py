from app.tree_loader import load_tree
from app.tree_ai import choose_node

TREE = load_tree()


def get_children(path):
    node = TREE

    for p in path:
        node = node[p]["_children"]

    return node


def format_options(children):
    return [
        {
            "code": k,
            "name": v["_name"]
        }
        for k, v in children.items()
    ]


def select_level(question, path):
    """
    Select the next node in the hierarchy.

    Returns (code, name, meta) where meta carries the routing diagnostics:
        {
            "confidence": "high" | "medium" | "low",
            "clarify":    str | None,   # question to ask when ambiguous
            "ranked":     [code, ...],  # full ranking the AI returned
            "fallback":   bool,         # True if we had to guess
        }

    Unlike the previous version, this never *silently* falls back to the first
    option: if the AI is unavailable or returns nothing usable, we still must
    return something for the browser to click, but we flag it as low-confidence
    fallback so the caller can surface that to the user.
    """
    children = get_children(path)
    options = format_options(children)

    if not options:
        return None, None, {
            "confidence": "low", "clarify": None, "ranked": [], "fallback": True
        }

    print("\n" + "=" * 80)
    print("QUESTION:", question)
    print("CURRENT PATH:", " > ".join(path) if path else "ROOT")
    print(f"OPTIONS: {len(options)} children")

    result = choose_node(question, options, path)
    ranked = result["ranked"]
    confidence = result["confidence"]
    clarify = result["clarify"]

    print("AI RANKED:", ranked or "(none)")
    print("CONFIDENCE:", confidence)
    if clarify:
        print("CLARIFY:", clarify)

    # Best valid candidate = first ranked code that exists as an option.
    by_code = {o["code"]: o["name"] for o in options}
    for code in ranked:
        if code in by_code:
            print(f"SELECTED: {code} - {by_code[code]}")
            print("=" * 80)
            return code, by_code[code], {
                "confidence": confidence,
                "clarify": clarify,
                "ranked": ranked,
                "fallback": False,
            }

    # Nothing usable came back — last-resort guess, clearly flagged.
    fallback = options[0]
    print(f"NO VALID RANKING -> FALLBACK GUESS: {fallback['code']} - {fallback['name']}")
    print("=" * 80)
    return fallback["code"], fallback["name"], {
        "confidence": "low",
        "clarify": clarify,
        "ranked": ranked,
        "fallback": True,
    }
