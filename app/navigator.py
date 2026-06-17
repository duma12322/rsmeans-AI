from app.tree_loader import load_tree
from app.tree_ai import choose_node
from app.knowledge_layer import formatting_guidance

TREE = load_tree()


def needs_clarification(meta):
    """
    True when we must STOP and ask the user instead of navigating on a guess.

    We refuse to proceed when the AI either had no usable answer (fallback) or
    explicitly flagged the request as ambiguous (a clarify question at low
    confidence). In those cases guessing a branch produces a confidently wrong
    cost, which is worse than asking the user to rephrase.
    """
    if meta.get("fallback"):
        return True
    return bool(meta.get("clarify")) and meta.get("confidence") == "low"


def build_clarification_response(question, path, meta):
    """Structured response telling the user how to ask, instead of a cost."""
    return {
        "status": "needs_clarification",
        "question": question,
        "message": (
            "Your request is too ambiguous to look up a cost. Please rephrase "
            "it more specifically — name the exact item or material and a "
            "single action."
        ),
        "clarify": meta.get("clarify"),
        "how_to_ask": formatting_guidance(),
        "path_so_far": path,
    }


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

    When the request is ambiguous (low confidence + a clarify question) or the
    AI returns nothing usable, this selects NOTHING — it returns code/name as
    None and a meta that the caller uses to stop and ask the user. We never
    guess a branch, because a guessed branch produces a confidently wrong cost.
    """
    children = get_children(path)
    options = format_options(children)

    print("\n" + "=" * 80)
    print("QUESTION:", question)
    print("CURRENT PATH:", " > ".join(path) if path else "ROOT")
    print(f"OPTIONS: {len(options)} children")

    if not options:
        print("NO OPTIONS -> NEEDS CLARIFICATION")
        print("=" * 80)
        return None, None, {
            "confidence": "low", "clarify": None, "ranked": [], "fallback": True
        }

    result = choose_node(question, options, path)
    ranked = result["ranked"]
    confidence = result["confidence"]
    clarify = result["clarify"]

    print("AI RANKED:", ranked or "(none)")
    print("CONFIDENCE:", confidence)
    if clarify:
        print("CLARIFY:", clarify)

    by_code = {o["code"]: o["name"] for o in options}
    best = next((c for c in ranked if c in by_code), None)

    # Ambiguous request: the AI is unsure and is asking the user to clarify.
    # Do NOT select anything — let the caller stop and prompt the user.
    if best is None or (confidence == "low" and clarify):
        print("AMBIGUOUS -> SELECTING NOTHING, NEEDS CLARIFICATION")
        print("=" * 80)
        return None, None, {
            "confidence": confidence,
            "clarify": clarify,
            "ranked": ranked,
            "fallback": True,
        }

    # Confident enough: take the best valid candidate.
    print(f"SELECTED: {best} - {by_code[best]}")
    print("=" * 80)
    return best, by_code[best], {
        "confidence": confidence,
        "clarify": clarify,
        "ranked": ranked,
        "fallback": False,
    }
