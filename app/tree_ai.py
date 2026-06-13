import requests
from app.config import DEEPSEEK_API_KEY, MARCE_API_URL


def build_options_text(options):
    return "\n".join([
        f"{o['code']} - {o['name']}"
        for o in options
    ])


def choose_node(question, options_text, path):

    prompt = f"""
You are a STRICT RSMeans navigation engine.

You are NOT answering the question.

You are selecting ONLY the next correct child node.

========================
QUESTION:
{question}

CURRENT PATH:
{path}

AVAILABLE CHILD NODES:
{options_text}

========================

RULES:
- Follow RSMeans hierarchy strictly
- Do NOT jump branches
- Choose MOST semantically relevant child
- Motor wiring connections → Wiring Connections branch
- Controllers ≠ Wiring Connections
- Stay consistent with previous path

Return ONLY ONE option exactly as shown.
"""

    res = requests.post(
        MARCE_API_URL,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Return exactly one option from the list."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0
        }
    )

    return res.json()["choices"][0]["message"]["content"].strip()