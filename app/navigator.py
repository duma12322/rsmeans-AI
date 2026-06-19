from app.tree_loader import load_tree
from app.tree_ai import choose_node
from app.knowledge_layer import formatting_guidance

TREE = load_tree()

# Penalty added to a hop's cost based on how sure the AI was about it. A low-confidence hop makes 
# its whole branch more expensive, so beam search naturally prefers paths it was confident about.
_CONFIDENCE_PENALTY = {"high": 0.0, "medium": 1.0, "low": 2.0}


def needs_clarification(meta):
    """
    True when we must PAUSE and ask the user instead of navigating further.

    This happens when the AI flagged the request as ambiguous (it returned
    follow-up questions) or had no usable candidate at all. We do not navigate
    on, but — importantly — we still keep the candidate matches we found.
    """
    return bool(meta.get("ambiguous"))


def build_clarification_response(question, path, meta):
    """
    Ambiguity response that PRESENTS the candidate matches and asks follow-up
    questions, rather than discarding the results. Follows the required format.
    """
    candidates = meta.get("candidates", [])
    questions = meta.get("clarify_questions", [])
    best = candidates[0] if (candidates and meta.get("confidence") == "high") else None

    # Build the human-readable message in the required format.
    lines = [
        "Your question appears to be ambiguous and could fall into several "
        "categories within RSMeans. To help you find the correct option, "
        "I found the following possible results:",
        "",
    ]
    for c in candidates:
        tag = "  (best match)" if best and c["code"] == best["code"] else ""
        lines.append(f"* {c['code']} - {c['name']}{tag}")

    if questions:
        lines += ["", "To determine which is correct, I need to ask a few additional questions:", ""]
        for i, q in enumerate(questions, 1):
            lines.append(f"{i}. {q}")

    lines += [
        "",
        "While you answer these questions, the results above represent the "
        "most likely matches found in RSMeans.",
    ]

    return {
        "status": "needs_clarification",
        "question": question,
        "message": "\n".join(lines),
        "candidates": candidates,
        "best_match": best,
        "clarify_questions": questions,
        "confidence": meta.get("confidence"),
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
            "clarify_question":    str | None,   # question to ask when ambiguous
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
            "confidence": "low", "clarify_questions": [], "ranked": [],
            "candidates": [], "ambiguous": True,
        }

    result = choose_node(question, options, path)
    ranked = result["ranked"]
    confidence = result["confidence"]
    clarify_questions = result["clarify_questions"]

    print("AI RANKED:", ranked or "(none)")
    print("CONFIDENCE:", confidence)
    if clarify_questions:
        print("CLARIFY:", clarify_questions)

    by_code = {o["code"]: o["name"] for o in options}
    # Candidate matches we found, names attached, top 3 — kept even if ambiguous.
    candidates = [
        {"code": c, "name": by_code[c]} for c in ranked if c in by_code
    ][:3]

    # Ambiguous = the AI explicitly asked follow-up questions, OR we found no
    # usable candidate at all. We PAUSE but keep the candidates. Medium
    # confidence without follow-up questions still navigates (best effort).
    ambiguous = bool(clarify_questions) or not candidates

    meta = {
        "confidence": confidence,
        "clarify_questions": clarify_questions,
        "ranked": ranked,
        "candidates": candidates,
        "ambiguous": ambiguous,
    }

    if ambiguous:
        print(f"AMBIGUOUS -> PRESENTING {len(candidates)} CANDIDATES + "
              f"{len(clarify_questions)} QUESTIONS, NOT NAVIGATING")
        print("=" * 80)
        return None, None, meta

    # Confident single match: navigate into it.
    best = candidates[0]
    print(f"SELECTED: {best['code']} - {best['name']}")
    print("=" * 80)
    return best["code"], best["name"], meta


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

    # Captured from the very first (division-level) decision so we can present
    # the candidate divisions and follow-up questions if the request turns out
    # to be ambiguous at the top — the most common and most useful case.
    root_candidates = []
    root_questions = []
    root_fallback = False

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

            # Capture the root-level picture for a possible clarification reply.
            if cand["path"] == []:
                root_candidates = [{"code": c, "name": by_code[c]} for c in top]
                root_questions = result["clarify_questions"]
                root_fallback = is_fallback

            for rank, code in enumerate(top):
                expansions.append({
                    "path": cand["path"] + [code],
                    "cost": cand["cost"] + rank + conf_penalty,
                    "hops": cand["hops"] + [{
                        "code": code,
                        "name": by_code[code],
                        "confidence": result["confidence"],
                        "clarify_questions": result["clarify_questions"],
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
        return {
            "path": [], "hops": [], "confidence": "low",
            "candidates": root_candidates, "clarify_questions": root_questions,
            "fallback_used": True, "ambiguous": True,
        }

    # Compare leaves fairly regardless of depth: average cost per hop.
    completed.sort(key=lambda c: c["cost"] / len(c["path"]))
    best = completed[0]

    order = {"high": 3, "medium": 2, "low": 1}
    overall_confidence = min(
        (h["confidence"] for h in best["hops"]),
        key=lambda c: order.get(c, 1),
        default="low",
    )

    # The route is ambiguous (present candidates + ask) when the top division
    # decision was a guess or the AI asked follow-up questions there.
    ambiguous = root_fallback or bool(root_questions)

    print(f">>> DECISION FINAL: {' > '.join(best['path'])} "
          f"| costo/salto={best['cost'] / len(best['path']):.2f} "
          f"| confianza={overall_confidence} | ambiguo={ambiguous}")
    print("=" * 70 + "\n")

    return {
        "path": best["path"],
        "hops": best["hops"],
        "confidence": overall_confidence,
        "candidates": root_candidates,
        "clarify_questions": root_questions,
        "fallback_used": any(h.get("fallback") for h in best["hops"]),
        "ambiguous": ambiguous,
    }
