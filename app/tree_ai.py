import json
import re

import requests

from app.config import DEEPSEEK_API_KEY, MARCE_API_URL
from app.knowledge_layer import build_root_context, get_division_context
from app.knowledge_records import options_preview


# =========================
# SEARCH-TERM TRANSLATION / EXTRACTION
# =========================
# Forced Spanish->English term choices. The model otherwise picks common product
# names (seguridad -> "safety scissors"); this pins the wording the user wants.
_SEARCH_GLOSSARY = {
    "seguridad": "security",
}


def english_search_term(question, timeout=20):
    """
    Turn a user request (in ANY language) into the concise ENGLISH phrase to type
    into the RSMeans search box. The catalog is English-only, so a Spanish query
    like "tijeras de seguridad de metal" must become "metal security scissors".

    Returns the phrase (lowercased words), or "" on any failure so the caller can
    fall back to the offline heuristic — this must never break a search.
    """
    glossary = "; ".join(f"{es} -> {en}" for es, en in _SEARCH_GLOSSARY.items())
    prompt = (
        "You prepare search terms for RSMeans, an ENGLISH construction cost "
        "catalog. Translate the user's request to English if needed and return "
        "ONLY the concise search phrase to type into the search box: the item "
        "plus its material/descriptor words, in natural order.\n"
        "Rules:\n"
        "- English only. No translation notes, no quotes, no punctuation.\n"
        "- Keep material and descriptor words (metal, security, folding, portable).\n"
        "- Drop filler (cost, price, find, the) and any 'not X' exclusions.\n"
        "- 2-4 words, singular or plural as natural.\n"
        f"- ALWAYS translate these exact terms this way: {glossary}.\n\n"
        f"User request: {question}\n"
        "Search phrase:"
    )
    try:
        res = requests.post(
            MARCE_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Return only the English search phrase."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
            },
            timeout=timeout,
        )
        res.raise_for_status()
        text = res.json()["choices"][0]["message"]["content"].strip()
        # Keep it to a clean lowercased word phrase.
        text = text.strip().strip('"').strip("'").splitlines()[0]
        words = re.findall(r"[a-z]+", text.lower())
        return " ".join(words)
    except Exception as e:  # noqa: BLE001 - translation is best-effort
        print(f"[tree_ai] english_search_term failed: {e}")
        return ""


# =========================
# SEARCH REFINEMENT SUGGESTIONS (too many hits)
# =========================
def suggest_refinements(question, descriptions, timeout=20):
    """
    A keyword search returned too many rows to be exact. Look at the user's
    original request PLUS a sample of the descriptions we actually pulled, and
    propose how to NARROW it: a couple of focused follow-up questions and a
    handful of short descriptor terms the user can ADD to the query.

    The suggestions must come from the real result set (not invented), so each
    chip actually shrinks the list when appended. Returns:

        {"questions": [str, ...], "refinements": [str, ...]}

    Best-effort: returns empty lists on any failure so a noisy search still
    renders (the caller falls back to the plain "add more detail" notice).
    """
    sample = [d for d in descriptions if d][:40]
    if not sample:
        return {"questions": [], "refinements": []}

    listing = "\n".join(f"- {d}" for d in sample)
    prompt = (
        "A user searched an RSMeans construction cost catalog and got too many "
        "results to be precise. Help them NARROW it.\n"
        "Below is their request and a sample of the descriptions that matched. "
        "Find the dimensions that vary across these rows (material, finish, size, "
        "type, interior/exterior, use) and propose how to disambiguate.\n\n"
        f"USER REQUEST: {question}\n\n"
        f"SAMPLE OF MATCHING DESCRIPTIONS:\n{listing}\n\n"
        "Return ONLY JSON, no prose, in exactly this shape:\n"
        '{"questions": ["<short follow-up question>"], '
        '"refinements": ["<short descriptor to add>"]}\n'
        "Rules:\n"
        "- 1-3 questions, each pointing at ONE distinguishing dimension.\n"
        "- 4-8 refinements: short descriptor words/phrases (1-3 words each) that "
        "actually appear as distinguishing traits in the sample, so ADDING one to "
        "the request shrinks the results. No duplicates, no generic filler.\n"
        "- Match the language of the user's request for the questions; keep "
        "refinements as the catalog's English terms.\n"
    )
    try:
        res = requests.post(
            MARCE_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Return only the requested JSON object."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
            },
            timeout=timeout,
        )
        res.raise_for_status()
        text = res.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return {"questions": [], "refinements": []}
        data = json.loads(m.group(0))

        def _clean_list(key):
            vals = data.get(key)
            if not isinstance(vals, list):
                return []
            out, seen = [], set()
            for v in vals:
                if not isinstance(v, str):
                    continue
                v = v.strip().strip('"').strip("'")
                k = v.lower()
                if v and k not in seen:
                    seen.add(k)
                    out.append(v)
            return out

        return {
            "questions": _clean_list("questions")[:3],
            "refinements": _clean_list("refinements")[:8],
        }
    except Exception as e:  # noqa: BLE001 - refinement hints are best-effort
        print(f"[tree_ai] suggest_refinements failed: {e}")
        return {"questions": [], "refinements": []}


# =========================
# OBJECT vs. PROPERTIES CLASSIFIER
# =========================
def names_object(question, timeout=15):
    """
    Decide whether the text NAMES A PHYSICAL OBJECT to price, or gives ONLY its
    PROPERTIES (material, finish, color, size, use) with no object named:
    "stainless steel white" -> no object; "stainless steel sink" -> a sink.

    A curated word list can't know every finish/color/adjective, so we let the
    model judge — it has the world knowledge to tell an object from its
    attributes. Returns:
        True  -> an object/item is named (route it),
        False -> only properties (ask the user WHICH object),
        None  -> model unavailable/unparseable, so the caller falls back to its
                 heuristic. Classification must never break routing.
    """
    prompt = (
        "You screen searches for RSMeans, a construction cost catalog. Decide if "
        "the text NAMES A PHYSICAL OBJECT/ITEM that can be priced (sink, pipe, "
        "door, cabinet, gate, water heater, wall, countertop...), or gives ONLY "
        "its PROPERTIES with NO object named — material, finish, color, size, or "
        "use (steel, stainless, white, 6 inch, portable, security).\n"
        "The text may be Spanish (lavaplatos = sink, tubo = pipe, puerta = door).\n"
        "Reply with ONLY JSON, no prose: "
        '{"names_object": true|false, "object": "<the object noun, or null>"}.\n'
        "Examples:\n"
        '- "stainless steel" -> {"names_object": false, "object": null}\n'
        '- "stainless steel white" -> {"names_object": false, "object": null}\n'
        '- "security" -> {"names_object": false, "object": null}\n'
        '- "brushed nickel" -> {"names_object": false, "object": null}\n'
        '- "stainless steel sink" -> {"names_object": true, "object": "sink"}\n'
        '- "lavaplatos de acero" -> {"names_object": true, "object": "lavaplatos"}\n'
        '- "steel folding gate" -> {"names_object": true, "object": "gate"}\n'
        '- "paint interior walls" -> {"names_object": true, "object": "walls"}\n\n'
        f"Text: {question}\nJSON:"
    )
    try:
        res = requests.post(
            MARCE_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Return only the JSON object."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
            },
            timeout=timeout,
        )
        res.raise_for_status()
        text = res.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        val = json.loads(m.group(0)).get("names_object")
        return val if isinstance(val, bool) else None
    except Exception as e:  # noqa: BLE001 - classification is best-effort
        print(f"[tree_ai] names_object failed: {e}")
        return None


# =========================
# OPTIONS FORMATTING
# =========================
def build_options_text(options):
    return "\n".join([
        f"{o['code']} - {o['name']}"
        for o in options
    ])


# =========================
# KNOWLEDGE CONTEXT BY DEPTH
# =========================
def _knowledge_context(path):
    """
    Inject the knowledge layer based on how deep we are in the tree.

    - At the root (no path yet) the first hop is the most error-prone, so we
      give the model the full division reference.
    - Deeper in, we only need focused context for the division branch we are
      already inside (path[0] is the division code).
    """
    if not path:
        return build_root_context()

    division_context = get_division_context(path[0])
    if division_context:
        return f"Context for the current branch:\n{division_context}"
    return ""


# =========================
# AI CALL (ROBUST + RANKED)
# =========================
def choose_node(question, options, path, timeout=30, retries=2):
    """
    Ask the model to RANK the most relevant child nodes instead of returning a
    single guess. Returns a structured dict:

        {
            "ranked":            [code, code, ...]  # best first, codes only
            "confidence":        "high" | "medium" | "low",
            "clarify_questions": [str, ...]         # follow-ups when ambiguous
        }

    On ambiguity we keep the ranked candidates AND return follow-up questions,
    so the caller can present the likely matches and ask the user to refine —
    never discarding the results just because there is ambiguity.
    """
    options_text = build_options_text(options)
    valid_codes = [o["code"] for o in options]
    knowledge = _knowledge_context(path)
    path_str = " > ".join(path) if path else "ROOT"

    # Real catalog content beneath each option (from route_items.json). This is
    # the strongest disambiguation signal: it shows what each branch ACTUALLY
    # contains, not just its title. Empty at root, where we rely on keywords.
    items_block = ""
    preview = options_preview(path, options)
    if preview:
        items_block = (
            "\nACTUAL LINE-ITEMS UNDER EACH OPTION (real RSMeans rows found "
            "beneath each code — use these to match the request precisely and to "
            "write specific clarify_questions):\n"
            f"{preview}\n"
        )

    prompt = f"""
You are a STRICT RSMeans navigation engine.

You are NOT answering the question. You are selecting the next correct child
node(s) in the RSMeans hierarchy.

========================
USER REQUEST:
{question}

CURRENT PATH:
{path_str}

DOMAIN KNOWLEDGE (use this to map natural language to the right area):
{knowledge}

AVAILABLE CHILD NODES (you may ONLY choose from these codes):
{options_text}
{items_block}========================

RULES:
- Follow the RSMeans hierarchy strictly; do NOT jump branches.
- ALWAYS rank the most relevant children (up to 3), most relevant first —
  even when the request is ambiguous. Never return an empty ranking if any
  option is plausibly relevant.
- Use the domain knowledge AND the actual line-items above to disambiguate
  natural-language terms; prefer the branch whose real items best match the
  request.
- If the request could reasonably fall into several of the options, set
  confidence "low" or "medium" and provide 1-3 short "clarify_questions" that
  would let the user pinpoint the right one. If the best option is clear, set
  confidence "high" and return an empty "clarify_questions" list.

Return ONLY a JSON object, no prose, in exactly this shape:
{{"ranked": ["<code>", "<code>"], "confidence": "high|medium|low", "clarify_questions": ["<question>"]}}

Every code in "ranked" MUST be one of the available codes above.
"""

    last_error = None
    for attempt in range(retries + 1):
        try:
            res = requests.post(
                MARCE_API_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "Return only the requested JSON object."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0,
                },
                timeout=timeout,
            )
            res.raise_for_status()
            content = res.json()["choices"][0]["message"]["content"]
            return _parse_ranking(content, valid_codes)
        except Exception as e:  # noqa: BLE001 - network/parse errors are all recoverable here
            last_error = e
            print(f"[tree_ai] AI call failed (attempt {attempt + 1}/{retries + 1}): {e}")

    # All attempts exhausted: signal failure, do NOT fabricate a choice.
    print(f"[tree_ai] AI unavailable after retries: {last_error}")
    return {"ranked": [], "confidence": "low", "clarify_questions": []}


# =========================
# PARSE + VALIDATE MODEL OUTPUT
# =========================
def _parse_ranking(content, valid_codes):
    """Parse the model's JSON, tolerating code fences and stray text."""
    text = content.strip()

    # Strip ```json ... ``` fences if present.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]

    # Fall back to extracting the first {...} block.
    if not text.lstrip().startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        # Last-resort: treat the raw content as a single "CODE - name" line.
        code = content.strip().split(" - ")[0].strip()
        ranked = [code] if code in valid_codes else []
        return {"ranked": ranked, "confidence": "low", "clarify_questions": []}

    # Keep only codes that actually exist as options, preserving order.
    ranked = [c for c in data.get("ranked", []) if c in valid_codes]
    confidence = data.get("confidence", "medium")
    if confidence not in ("high", "medium", "low"):
        confidence = "medium"

    # Accept the list form, or a single legacy "clarify" string.
    clarify_questions = data.get("clarify_questions")
    if not isinstance(clarify_questions, list):
        single = data.get("clarify") or clarify_questions
        clarify_questions = [single] if single else []
    clarify_questions = [q.strip() for q in clarify_questions if isinstance(q, str) and q.strip()]

    return {"ranked": ranked, "confidence": confidence, "clarify_questions": clarify_questions}
