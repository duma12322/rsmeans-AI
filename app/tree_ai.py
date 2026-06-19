import json

import requests

from app.config import DEEPSEEK_API_KEY, MARCE_API_URL
from app.knowledge_layer import build_root_context, get_division_context


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
========================

RULES:
- Follow the RSMeans hierarchy strictly; do NOT jump branches.
- ALWAYS rank the most relevant children (up to 3), most relevant first —
  even when the request is ambiguous. Never return an empty ranking if any
  option is plausibly relevant.
- Use the domain knowledge to disambiguate natural-language terms.
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
        single = data.get("clarify_questions")
        clarify_questions = [single] if single else []
    clarify_questions = [q.strip() for q in clarify_questions if isinstance(q, str) and q.strip()]

    return {"ranked": ranked, "confidence": confidence, "clarify_questions": clarify_questions}
