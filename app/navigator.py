import re

from app.tree_loader import load_tree
from app.tree_ai import choose_node
from app.knowledge_layer import formatting_guidance
from app.knowledge_records import resolve_code, search_items
from app.cancellation import check_cancel

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


# Words that carry no item/work meaning. A question made of ONLY these has no
# subject to price ("what is the cost?"), so candidate divisions would be pure
# guesses — we guide the user instead of showing them. (EN + ES.)
_CONTENTLESS_WORDS = {
    "cost", "costs", "costo", "costos", "price", "prices", "precio", "precios",
    "much", "many", "what", "whats", "which", "how", "the", "this", "that",
    "for", "and", "with", "value", "total", "give", "tell", "show", "need",
    "want", "please", "rsmeans", "code", "codigo", "number", "line", "item",
    "cuanto", "cuesta", "cuestan", "que", "cual", "dame", "dime", "por", "favor",
    "valor", "del", "los", "las", "una", "uno",
    # short filler/verbs (the {2,} regex never captures 1-letter words)
    "is", "are", "be", "am", "of", "it", "me", "my", "do", "does", "did",
    "in", "on", "at", "or", "us", "we", "to", "es", "un", "la", "el", "de",
}


# Dimension/unit words. A request that names ONLY a measure ("6 inch deep")
# and no thing names no subject to price — hundreds of items share that
# dimension — so it is ambiguous, the same as "what is the cost?". (EN + ES.)
_MEASURE_WORDS = {
    "inch", "inches", "deep", "depth", "wide", "width", "thick", "thickness",
    "high", "height", "tall", "long", "length", "ft", "feet", "foot", "yard",
    "yards", "meter", "metre", "cm", "mm", "gauge", "ga", "diameter", "dia",
    "diam", "radius", "round", "square", "thk",
    "pulgada", "pulgadas", "profundo", "profundidad", "ancho", "grueso",
    "espesor", "alto", "altura", "largo", "longitud", "pie", "pies", "metro",
    "metros", "diametro", "diámetro", "redondo", "cuadrado",
}

# Words that point at a PLACE in the catalog (a section/division), not at an
# item. "the 6 inch deep one in section 31" still names no item.
_SECTION_WORDS = {
    "section", "seccion", "sección", "division", "divisi", "divisor",
    "chapter", "capitulo", "capítulo", "div",
}


def _has_concrete_subject(question):
    """
    True when the question names something to price — a material, item, or work
    word beyond generic 'cost' filler, a bare measure, or a section reference.
    False for contentless asks like "what is the cost?" / "how much?" AND for
    measure-only asks like "6 inch deep" / "the 6 inch deep one in section 31",
    where any candidate we surfaced would just be a guess.
    """
    # A pasted RSMeans code is itself a concrete subject.
    if _extract_code(question):
        return True
    words = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]{2,}", question.lower())
    return any(
        w not in _CONTENTLESS_WORDS
        and w not in _MEASURE_WORDS
        and w not in _SECTION_WORDS
        for w in words
    )


def _masterformat_orientation(limit=8):
    """A few real MasterFormat divisions (code - name) from the taxonomy, to
    orient a lost user toward the categories they can ask about."""
    out = []
    for code, node in TREE.items():
        name = (node.get("_name") or "").strip()
        if name:
            out.append({"code": code, "name": name})
        if len(out) >= limit:
            break
    return out


def _build_formulation_guidance(question, path):
    """
    Response for a contentless question (no item named). Instead of fake
    "possible results", it tells the user what's missing and shows how to ask —
    real MasterFormat categories plus well-formed example questions.
    """
    guide = formatting_guidance()
    divisions = _masterformat_orientation()

    lines = [
        "I can look up a cost, but your question doesn't name what to price "
        "yet — \"the cost of what?\". Tell me the item or work and I'll find it.",
        "",
        "RSMeans is organized by MasterFormat categories. Some you can ask about:",
        "",
    ]
    lines += [f"* {d['code']} - {d['name']}" for d in divisions]
    lines += [
        "",
        "Phrase it as an action plus the specific item, for example:",
        "",
    ]
    lines += [f"* {ex}" for ex in guide["good_examples"]]
    lines += [
        "",
        "Tip: name the material or item, ask about one thing at a time, and "
        "everyday words are fine — you don't need an RSMeans code.",
    ]

    return {
        "status": "needs_subject",
        "question": question,
        "message": "\n".join(lines),
        "candidates": [],
        "best_match": None,
        "clarify_questions": [],
        "confidence": "low",
        "categories": divisions,
        "how_to_ask": guide,
        "path_so_far": path,
    }


def build_clarification_response(question, path, meta):
    """
    Ambiguity response that PRESENTS the candidate matches and asks follow-up
    questions, rather than discarding the results. Follows the required format.

    Exception: when the question names no subject at all (e.g. "what is the
    cost?"), the candidate divisions would be meaningless guesses — so we return
    formulation guidance (how to ask + MasterFormat examples) instead.
    """
    if not _has_concrete_subject(question):
        return _build_formulation_guidance(question, path)

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


def _node_name(path):
    """Display name of the node at `path` in the tree ('' if not found)."""
    node = TREE
    name = ""
    for p in path:
        entry = node.get(p) if isinstance(node, dict) else None
        if not entry:
            return name
        name = entry.get("_name", "")
        node = entry.get("_children", {})
    return name


def path_for_code(text):
    """
    Map a tree-code reference inside free text to its deepest tree path.

    Handles the way users name a place in the catalog — "section 31.36",
    "3136", "313613.10" — by walking the tree greedily along whichever child
    code is a digit-prefix of the token. Returns e.g. ["31", "3136"], or [] when
    no code-like token (>=4 digits) resolves to at least a section (depth >= 2).
    Requiring depth >= 2 means a bare division number does NOT lock here — that
    stays with candidate matching.
    """
    for tok in re.findall(r"\d[\d.]*\d", str(text)):
        digits = tok.replace(".", "")
        if len(digits) < 4:
            continue
        node = TREE
        path = []
        while isinstance(node, dict) and node:
            best, best_len = None, 0
            for code in node:
                cd = "".join(c for c in code if c.isdigit())
                if cd and digits.startswith(cd) and len(cd) > best_len:
                    best, best_len = code, len(cd)
            if best is None:
                break
            path.append(best)
            node = node[best].get("_children", {})
        if len(path) >= 2:
            return path
    return []


def chapter_reference(text):
    """
    Detect a reference to a chapter/section in free text and return its tree
    path. Covers the ways users point at the catalog:

      - a real section code anywhere   "31.36" / "313613.10" -> ['31','3136'...]
      - a cue word + number            "capitulo 1" -> ['1'], "division 31" ->
                                        ['31'], "seccion 2103" -> ['21']
      - a division NAME                "Earthwork" -> ['31'], "Metals" -> ['5']

    Returns [] when nothing explicit is found. A bare number WITHOUT a cue only
    locks when it resolves to a real section (via the code walk) — so quantities
    like "1500 sqft" never lock a chapter by accident.
    """
    t = str(text).lower()

    # 1) An explicit, real section code anywhere in the text.
    deep = path_for_code(text)
    if deep:
        return deep

    # 2) A cue word followed by a code/number.
    m = re.search(
        r"\b(cap[ií]tulo|chapter|secci[oó]n|section|divisi[oó]n|division|div)\s*#?\s*(\d[\d.]*)",
        t,
    )
    if m:
        tok = m.group(2)
        deep = path_for_code(tok)
        if deep:
            return deep
        d = tok.replace(".", "")
        for cand in (d[:2], (str(int(d[:2])) if d[:2].isdigit() else ""), d[:1]):
            if cand and cand in TREE:
                return [cand]

    # 3) A division name (or its parenthetical alias, e.g. "(HVAC)") as a
    #    bounded phrase. Longest name first so specific names win.
    for code, entry in sorted(TREE.items(), key=lambda kv: -len(kv[1].get("_name", ""))):
        name = entry.get("_name", "").lower()
        if not name:
            continue
        for alias in [name, *re.findall(r"\(([^)]+)\)", name)]:
            alias = alias.strip()
            if alias and re.search(r"\b" + re.escape(alias) + r"\b", t):
                return [code]

    return []


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
# DIRECT CODE LOOKUP
# =========================
def _extract_code(question):
    """
    Pull an explicit RSMeans line number out of the question, if any.

    Returns the digits-only code when the question contains a run of 6+ digits
    (optionally split by spaces/dots/dashes, as users paste them), else None. A
    6-digit floor avoids catching quantities like "200 amp" or "4 inch".
    """
    runs = re.findall(r"\d[\d.\s\-]{4,}\d", question)
    if not runs:
        return None
    best = max(runs, key=lambda s: sum(c.isdigit() for c in s))
    digits = "".join(c for c in best if c.isdigit())
    return digits if len(digits) >= 6 else None


_CODE_STOPWORDS = {
    "cost", "costo", "price", "precio", "code", "codigo", "número", "numero",
    "line", "linea", "rsmeans", "for", "the", "and", "del", "the",
}


def _residual_text(question, code):
    """
    The descriptive part of the question with the code (and generic filler)
    removed — e.g. "electrical panel codigo 9999" -> "electrical panel". Empty
    when nothing meaningful remains (the user only gave a bare code).
    """
    without_code = re.sub(r"\d[\d.\s\-]{4,}\d", " ", question)
    words = [
        w for w in re.findall(r"[A-Za-z]{3,}", without_code)
        if w.lower() not in _CODE_STOPWORDS
    ]
    return " ".join(words)


def _route_from_leaf(hit):
    """Build a find_path-shaped route dict from a code-resolution hit."""
    path = hit["path"]
    # An exact/prefix line is a confident pinpoint; a section match is only the
    # right grid (the exact line wasn't in our snapshot), so soften confidence.
    confidence = "medium" if hit["match"] == "section" else "high"
    hops = [
        {
            "code": c,
            "name": hit["name"] if i == len(path) - 1 else "",
            "confidence": confidence,
            "clarify_questions": [],
            "rank": 0,
            "fallback": False,
        }
        for i, c in enumerate(path)
    ]
    return {
        "path": path,
        "hops": hops,
        "confidence": confidence,
        "candidates": [{"code": path[-1], "name": hit["name"]}],
        "clarify_questions": [],
        "fallback_used": False,
        "ambiguous": False,
        "matched_line": hit["line"],
        "matched_item": hit["description"],
        "code_match": hit["match"],
    }


def _item_candidates(question, start_path):
    """
    Text-match candidates: when the wording matches REAL catalog items (AI-free
    lookup over route_items.json), surface the top 3 so the user can confirm
    which exact line they mean — far more useful than abstract division
    questions.

    Only items whose description contains all the query's words (score >= 1.0)
    qualify. Crucially, this fires ONLY for SPECIFIC wording: if a generic term
    ("concrete", "pipe") matches lots of items, we bail out and let the old
    semantic beam search / division questions handle it — adding the item
    shortcut WITHOUT replacing the existing ambiguity flow.
    Returns an item-clarification route (ambiguous, match_type='item') or None.
    """
    matches = search_items(question, within_path=start_path or None, limit=60)
    strong = [m for m in matches if m["score"] >= 1.0]

    # No literal match, or the wording is too generic (many hits) -> defer to the
    # semantic beam search so it can ask the usual division/section questions.
    if not strong or len(strong) > 12:
        return None

    strong = strong[:3]

    candidates = [
        {
            "code": m["line"],          # the line number doubles as the pick id
            "name": m["description"],    # what the user sees
            "line": m["line"],
            "path": m["path"],
            "division": m["division"],
            "leaf_name": m["name"],
            "score": m["score"],
        }
        for m in strong
    ]

    print("\n" + "=" * 70)
    print(f">>> COINCIDENCIAS DE TEXTO: {len(candidates)} item(s) -> se piden a confirmar")
    for i, c in enumerate(candidates, 1):
        print(f"    {i}. {c['name']}  [linea {c['line']}]  ({' > '.join(c['path'])})")
    print("=" * 70 + "\n")

    return {
        "path": [], "hops": [],
        "confidence": "medium",
        "candidates": candidates,
        "clarify_questions": [
            "Which of these items do you mean? Reply with its number (1-3) or its line number."
        ],
        "fallback_used": False,
        "ambiguous": True,
        "match_type": "item",
    }


def build_item_clarification(question, candidates):
    """needs_clarification response that lists matching ITEMS (not divisions)."""
    top_score = candidates[0]["score"] if candidates else 0.0
    # A clear front-runner: the top item is a full-phrase match (>= 1.5) and
    # strictly stronger than the next. The score decides — that's the method.
    runner_up = candidates[1]["score"] if len(candidates) > 1 else 0.0
    best = candidates[0] if (top_score >= 1.5 and top_score > runner_up) else None

    lines = [
        "I found these catalog items matching your wording. Which one do you mean?",
        "",
    ]
    for i, c in enumerate(candidates, 1):
        tag = "  (best match)" if best and c["line"] == best["line"] else ""
        lines.append(
            f"{i}. {c['name']}  (line {c['line']}, in {' > '.join(c['path'])}){tag}"
        )
    lines += [
        "",
        "Reply with its number (1-3) or its line number to confirm, "
        "or describe it differently to refine the search.",
    ]
    return {
        "status": "needs_clarification",
        "match_type": "item",
        "question": question,
        "message": "\n".join(lines),
        "candidates": candidates,
        "best_match": best,
        "top_score": top_score,
        "clarify_questions": [
            "Which of these items do you mean? Reply with its number (1-3) or its line number."
        ],
        "confidence": "high" if best else "medium",
        "how_to_ask": formatting_guidance(),
        "path_so_far": [],
    }


def _unknown_code_response(code):
    """Code given but unresolvable and no description to fall back on: ask,
    never guess a branch from a code we don't recognize."""
    return {
        "path": [], "hops": [], "confidence": "low",
        "candidates": [],
        "clarify_questions": [
            f"I couldn't find code {code} in the RSMeans catalog. Please "
            "double-check the line number, or describe the item in words."
        ],
        "fallback_used": True, "ambiguous": True, "unknown_code": code,
    }


# =========================
# BEAM SEARCH (BACKTRACKING)
# =========================
def find_path(question, start_path=None, beam_width=3, max_depth=10, cancel=None):
    """
    Walk the tree to a leaf using beam search instead of a greedy per-level
    pick, so a single bad guess high up no longer dooms the whole route.

    `start_path` locks an already-chosen prefix (codes the user committed to
    during a multi-turn clarification) and drills DOWN from there, instead of
    re-deciding the division every turn — which is what made the conversation
    loop. Empty/None == search from the root.

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

    `cancel` (a threading.Event) makes the search COOPERATIVELY interruptible: it's
    polled before each AI hop, so when the client disconnects the beam search stops
    instead of running every remaining `choose_node` call. Raises ScrapeCancelled.
    """
    # Fast path: the user pasted an explicit RSMeans code. A code is an exact
    # identifier, so resolve it against route_items.json instead of letting the
    # semantic beam search mangle it. Resolution is graded (exact/prefix/section)
    # and, when it fails, we fall back to the DESCRIPTION — never to the bare
    # code, which is what produced bad results before.
    code = _extract_code(question)
    if code:
        hit = resolve_code(code)
        if hit:
            print("\n" + "=" * 70)
            print(f">>> CODIGO {code} -> {' > '.join(hit['path'])} "
                  f"({hit['name']} | match={hit['match']}) <<<")
            if hit["match"] == "section":
                print(">>> Linea exacta no esta en la base; navego a su SECCION "
                      "(el scrape en vivo la tendra)")
            else:
                print(f">>> Item: {hit['description']}")
            print("=" * 70 + "\n")
            route = _route_from_leaf(hit)
            # Remember the exact digits the user typed so the scraper can return
            # ONLY the line(s) under this leaf that start with that code: a full
            # 12-digit code -> one line; a shorter section code -> all its lines.
            route["requested_code"] = code
            return route

        residual = _residual_text(question, code)
        if residual:
            print(f"\n>>> Codigo {code} NO encontrado; navego por la descripcion "
                  f"residual: {residual!r} <<<")
            question = residual  # fall through to semantic search on the text
        else:
            print(f"\n>>> Codigo {code} NO encontrado y sin descripcion -> "
                  f"pido aclaracion (no adivino) <<<")
            return _unknown_code_response(code)

    # A request that names only a MEASURE ("6 inch deep") with no item names no
    # subject to price — countless lines share that dimension — so don't let
    # beam search confidently pick one. Skip this gate when a branch is already
    # locked (multi-turn): there a bare measure DOES disambiguate within it.
    if not (start_path or []) and not _has_concrete_subject(question):
        print("\n>>> Sin sujeto concreto (solo medida/relleno) -> ambiguo, "
              "pido aclaracion en vez de adivinar <<<")
        return {
            "path": [], "hops": [], "confidence": "low",
            "candidates": [], "clarify_questions": [],
            "fallback_used": False, "ambiguous": True,
        }

    # Second fast path: the wording literally matches real catalog items — show
    # the top matches for confirmation instead of deliberating divisions.
    item_match = _item_candidates(question, start_path)
    if item_match is not None:
        return item_match

    # >>> Console indicator: the new (beam-search) routing decision starts here.
    print("\n" + "=" * 70)
    print(">>> NUEVA DECISION DE LA IA (beam search con backtracking) <<<")
    print(f">>> Pregunta: {question!r}  | beam_width={beam_width}")
    print("=" * 70)

    # Seed the beam at the locked prefix so we search DOWN from there. Validate
    # it against the tree; ignore a bad prefix rather than crash.
    start_path = list(start_path or [])
    try:
        get_children(start_path)
    except (KeyError, TypeError):
        start_path = []
    base_len = len(start_path)
    if start_path:
        print(f">>> Rama bloqueada (inicio): {' > '.join(start_path)}")

    # Synthetic high-confidence hops for the locked codes, so hops stay aligned
    # with path even when the route starts mid-tree.
    init_hops = [
        {
            "code": c, "name": _node_name(start_path[:i + 1]),
            "confidence": "high", "clarify_questions": [], "rank": 0,
            "fallback": False,
        }
        for i, c in enumerate(start_path)
    ]

    # Each beam item: {"path", "cost", "hops"}.
    beam = [{"path": list(start_path), "cost": 0.0, "hops": list(init_hops)}]
    completed = []

    # Captured from the FRONTIER decision (first level below the locked prefix)
    # so we can present those candidates + follow-up questions if still
    # ambiguous — at the root this is the division choice, the usual case.
    root_candidates = []
    root_questions = []
    root_fallback = False

    for depth in range(max_depth):
        expansions = []

        for cand in beam:
            # Stop deliberating if the client went away: the next AI hop is the
            # expensive part, so check right before it.
            check_cancel(cancel)

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

            # Capture the frontier decision (first level below the lock) for a
            # possible clarification reply.
            if len(cand["path"]) == base_len:
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
