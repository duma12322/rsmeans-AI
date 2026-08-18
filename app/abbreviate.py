"""
Shorten an RSMeans line description so it fits the CostSeg description field.

That field caps at 50 characters and plenty of catalog descriptions run past it
("Copper wire, 600 volt, type THW, stranded, #12 AWG" is 49 already, and many are
longer). Rather than truncating mid-word — which drops exactly the identifying
detail an estimator needs — we ask the model for three progressively shorter
versions and let the user pick.

The three levels exist because how much can be dropped depends on the line: for
some, losing the gauge is fatal; for others the material alone identifies it.
"""

import json
import re

import requests

from app.config import DEEPSEEK_API_KEY, MARCE_API_URL

# Character ceiling per level. "low" leaves headroom under the form's 50 so the
# estimator can still append a note; "high" is the aggressive one, meant for when
# the description shares a row with other identifying columns (CSI, unit).
LIMITS = {"low": 45, "medium": 35, "high": 20}


def _truncate(text, limit):
    """
    Hard ceiling, applied on top of whatever the model returned. Cuts on a word
    boundary when there is one, so we never hand back a severed word.
    """
    text = (text or "").strip()
    if len(text) <= limit:
        return text

    cut = text[:limit].rstrip()
    # Only respect the word boundary if it doesn't gut the string (a single very
    # long word would otherwise collapse to almost nothing).
    space = cut.rfind(" ")
    if space >= limit * 0.6:
        cut = cut[:space]

    return cut.rstrip(" ,;:-/")


def abbreviate_description(description, timeout=20):
    """
    Return {"low": str, "medium": str, "high": str} — the same description at
    three levels of abbreviation, each within its LIMITS ceiling.

    Never raises: on any failure it returns {} so the caller (and ultimately the
    frontend, which has its own rule-based abbreviator) can fall back instead of
    blocking the user's send.
    """
    description = (description or "").strip()
    if not description:
        return {}

    prompt = (
        "You shorten construction cost line descriptions from the RSMeans "
        "catalog so they fit a short database field, for a cost segregation "
        "estimator who knows the trade.\n\n"
        f"DESCRIPTION: {description}\n\n"
        "Return ONLY JSON, no prose, in exactly this shape:\n"
        '{"low": "<= 45 chars", "medium": "<= 35 chars", "high": "<= 20 chars"}\n'
        "Rules:\n"
        "- NEVER exceed the character limit of each level. Count the characters.\n"
        "- MEASUREMENTS ARE THE HIGHEST PRIORITY after the item itself. Sizes, "
        "diameters, gauges, voltages, thicknesses, capacities and their units "
        "(3/4\", 1/2 inch, #12 AWG, 600V, 20 amp, 2 coats, 1 C.Y.) must survive "
        "at EVERY level, including the shortest one. They are what tells two "
        "otherwise identical catalog lines apart.\n"
        "- Order of priority when something has to go: the item itself, then "
        "measurements and their units, then type codes (THW, EMT), then "
        "material, then finish and everything else.\n"
        "- Drop filler words first (with, and, for, type, each, per).\n"
        "- Abbreviate the units rather than dropping the number: inch->in or \", "
        "foot->ft or ', gauge->ga, volt->V, pound->lb, diameter->dia.\n"
        "- Use standard construction abbreviations: concrete->conc, "
        "galvanized->galv, copper->Cu, aluminum->alum, diameter->dia, "
        "minimum->min, maximum->max, thickness->thk, insulated->insul, "
        "reinforced->reinf, average->avg, including->incl.\n"
        "- Keep the catalog's English. Never invent details that aren't in the "
        "description, and never add units or numbers of your own.\n"
        "- Each level must stay readable as a description, not a code.\n"
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

        # The model sometimes wraps the object in prose or code fences; take the
        # first {...} block, same defensive parse the routing code uses.
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return {}
        data = json.loads(m.group(0))

        out = {}
        for level, limit in LIMITS.items():
            value = data.get(level)
            if not isinstance(value, str):
                continue
            # Models overshoot character counts routinely — enforce the ceiling
            # ourselves instead of trusting the instruction.
            value = _truncate(value.strip().strip('"').strip("'"), limit)
            if value:
                out[level] = value

        return out

    except Exception as e:  # noqa: BLE001 - abbreviation is best-effort
        print(f"[abbreviate] failed: {e}")
        return {}
