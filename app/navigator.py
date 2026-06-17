from app.tree_loader import load_tree
from app.tree_ai import choose_node
from app.knowledge_layer import formatting_guidance

TREE = load_tree()

# Penalty added to a hop's cost based on how sure the AI was about it. A low-confidence hop makes 
# its whole branch more expensive, so beam search naturally prefers paths it was confident about.
_CONFIDENCE_PENALTY = {"high": 0.0, "medium": 1.0, "low": 2.0}


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


# =========================
# BEAM SEARCH (BACKTRACKING)
# =========================
def find_path(question, beam_width=3, max_depth=10):
    """
    Walk the tree to a leaf using beam search instead of a greedy per-level
    pick, so a single bad guess high up no longer dooms the whole route.

    We keep the `beam_width` cheapest partial paths alive at all times. Each
    surviving path branches into the AI's top-ranked children; a hop's cost is
    its rank position plus a confidence penalty. When a path reaches a leaf it
    is finalized. The cheapest leaf path (by average cost per hop) wins — and
    because several branches are explored in parallel, the search effectively
    backtracks: a promising level-1 option that dead-ends is overtaken.

    Runs entirely against tree.json (no browser), so exploring alternatives is
    free; the browser only navigates the single chosen path afterwards.

    Returns a dict with path / hops / confidence / clarifications /
    fallback_used, or None if the tree is empty / unreachable.
    """
    # >>> Console indicator: the new (beam-search) routing decision starts here.
    print("\n" + "=" * 70)
    print(">>> NUEVA DECISION DE LA IA (beam search con backtracking) <<<")
    print(f">>> Pregunta: {question!r}  | beam_width={beam_width}")
    print("=" * 70)

    # Each beam item: {"path", "cost", "hops"}.
    beam = [{"path": [], "cost": 0.0, "hops": []}]
    completed = []

    for depth in range(max_depth):
        expansions = []

        for cand in beam:
            options = format_options(get_children(cand["path"]))
            here = " > ".join(cand["path"]) if cand["path"] else "ROOT"

            # No children -> this path has reached a real leaf.
            if not options:
                print(f"[BEAM] depth {depth}: hoja alcanzada en [{here}] -> camino finalizado")
                completed.append(cand)
                continue

            result = choose_node(question, options, cand["path"])
            by_code = {o["code"]: o["name"] for o in options}

            # If the AI returned nothing usable, fall back to the raw option
            # order but flag every resulting hop as a guess.
            is_fallback = not result["ranked"]
            ranked = result["ranked"] or [o["code"] for o in options]
            conf_penalty = _CONFIDENCE_PENALTY.get(result["confidence"], 1.0)

            top = [c for c in ranked[:beam_width] if c in by_code]
            print(f"[BEAM] depth {depth}: desde [{here}] | IA rankeó {top} "
                  f"(conf={result['confidence']}{', FALLBACK' if is_fallback else ''}) "
                  f"-> ramifica {len(top)}")

            for rank, code in enumerate(top):
                expansions.append({
                    "path": cand["path"] + [code],
                    "cost": cand["cost"] + rank + conf_penalty,
                    "hops": cand["hops"] + [{
                        "code": code,
                        "name": by_code[code],
                        "confidence": result["confidence"],
                        "clarify": result["clarify"],
                        "rank": rank,
                        "fallback": is_fallback,
                    }],
                })

        if not expansions:
            break

        expansions.sort(key=lambda c: c["cost"])
        beam = expansions[:beam_width]
        kept = [(" > ".join(c["path"]), round(c["cost"], 2)) for c in beam]
        print(f"[BEAM] depth {depth}: caminos mantenidos (más baratos primero): {kept}")

    # Any branches still active at max_depth are accepted as-is.
    completed.extend(beam)
    completed = [c for c in completed if c["path"]]
    if not completed:
        print("[BEAM] !! sin caminos validos -> None\n")
        return None

    # Compare leaves fairly regardless of depth: average cost per hop.
    completed.sort(key=lambda c: c["cost"] / len(c["path"]))
    best = completed[0]

    order = {"high": 3, "medium": 2, "low": 1}
    overall_confidence = min(
        (h["confidence"] for h in best["hops"]),
        key=lambda c: order.get(c, 1),
        default="low",
    )

    print(f">>> DECISION FINAL: {' > '.join(best['path'])} "
          f"| costo/salto={best['cost'] / len(best['path']):.2f} "
          f"| confianza={overall_confidence}")
    print("=" * 70 + "\n")

    return {
        "path": best["path"],
        "hops": best["hops"],
        "confidence": overall_confidence,
        "clarifications": [h["clarify"] for h in best["hops"] if h.get("clarify")],
        "fallback_used": any(h.get("fallback") for h in best["hops"]),
    }
