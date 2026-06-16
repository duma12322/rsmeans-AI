import requests
from app.config import DEEPSEEK_API_KEY, MARCE_API_URL
from app.knowledge_layer import build_root_context, get_division_context


def build_options_text(options):
    return "\n".join([
        f"{o['code']} - {o['name']}"
        for o in options
    ])


def choose_node(question, options_text, path):

    # Inject knowledge context based on depth
    if not path:
        # Level 1: full division reference so the AI knows what each section covers
        knowledge_context = build_root_context()
    else:
        # Deeper levels: focused context for the current division branch
        knowledge_context = get_division_context(path[0])

    prompt = f"""
You are a STRICT RSMeans navigation engine.

You are NOT answering the question.

You are selecting ONLY the next correct child node.

========================
KNOWLEDGE BASE — use this to interpret the user's natural language:
{knowledge_context}

========================
QUESTION:
{question}

CURRENT PATH:
{path}

AVAILABLE CHILD NODES:
{options_text}

========================

RULES:
- Use the knowledge base above to map the user's words to the correct RSMeans category
- Follow RSMeans hierarchy strictly
- Do NOT jump branches
- Choose MOST semantically relevant child
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