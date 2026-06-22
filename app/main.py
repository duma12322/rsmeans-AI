import re
import sys
import time
import uuid
import asyncio
import threading
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.scraper import start_browser
from app.navigator import chapter_reference

app = FastAPI()

# correr el scraper en un hilo dedicado con su propio Proactor loop.
_executor = ThreadPoolExecutor(max_workers=1)

# Multi-turn conversation state, in memory:
#   {session_id: {"question", "answers", "locked_path", "candidates", "last_seen"}}
# Each clarification turn re-runs routing with the original question PLUS every
# answer (for wording), while `locked_path` records the branch the user has
# explicitly committed to so routing drills DOWN instead of restarting.
#
# This store is bounded so abandoned conversations can't leak memory:
#   - TTL: a session idle longer than SESSION_TTL is purged on the next request.
#   - Cap: at most MAX_SESSIONS live at once; the least-recently-seen is evicted.
# A lock guards the dict so concurrent requests can't corrupt it. NOTE: this is
# still in-process — it does NOT survive a restart and does NOT work across
# multiple uvicorn workers (run a single worker, or move to an external store).
SESSION_TTL = 600        # seconds of inactivity before a conversation is dropped
MAX_SESSIONS = 500       # hard ceiling on concurrent conversations

_SESSIONS = {}
_SESSIONS_LOCK = threading.Lock()


def _get_session(session_id):
    """Purge idle sessions, then return the live session for `session_id`
    (touching its last_seen) or None. Thread-safe."""
    if not session_id:
        return None
    now = time.time()
    with _SESSIONS_LOCK:
        for sid in [s for s, v in _SESSIONS.items() if now - v["last_seen"] > SESSION_TTL]:
            _SESSIONS.pop(sid, None)
        sess = _SESSIONS.get(session_id)
        if sess is not None:
            sess["last_seen"] = now
        return sess


def _create_session(question):
    """Create a new session, evicting the oldest if at capacity. Thread-safe."""
    now = time.time()
    with _SESSIONS_LOCK:
        while len(_SESSIONS) >= MAX_SESSIONS:
            oldest = min(_SESSIONS, key=lambda s: _SESSIONS[s]["last_seen"])
            _SESSIONS.pop(oldest, None)
        sid = uuid.uuid4().hex[:12]
        _SESSIONS[sid] = {
            "question": question, "answers": [],
            "locked_path": [], "candidates": [], "candidate_kind": None,
            "last_seen": now,
        }
        return sid, _SESSIONS[sid]


def _drop_session(session_id):
    with _SESSIONS_LOCK:
        _SESSIONS.pop(session_id, None)


def _run_scraper(question: str, start_path):
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(start_browser(question, start_path=start_path))
    finally:
        loop.close()


def _combined_text(sess) -> str:
    """Original question plus every clarification answer, as one query."""
    return " ".join(p for p in [sess["question"], *sess["answers"]] if p)


def _pick_candidate(answer, candidates):
    """
    If the user's answer names one of the candidates we just presented (by its
    code as a standalone token, or its name as a substring), return that code so
    we can lock that branch. Else None.
    """
    if not answer:
        return None
    a = answer.lower()
    for c in candidates or []:
        code = str(c.get("code", "")).lower()
        name = str(c.get("name", "")).lower()
        if code and re.search(rf"\b{re.escape(code)}\b", a):
            return c["code"]
        if name and name in a:
            return c["code"]
    return None


class AskRequest(BaseModel):
    question: Optional[str] = Field(
        None,
        min_length=3,
        description="Natural-language cost question (required to START a conversation).",
        examples=["Cost to paint interior walls"],
    )
    session_id: Optional[str] = Field(
        None, description="Returned by a previous needs_clarification response; send it back to continue."
    )
    answer: Optional[str] = Field(
        None, description="Your reply to the clarification questions."
    )


def _pick_item(answer, candidates):
    """
    When the last turn offered ITEM candidates, resolve the user's confirmation
    to a line number: by ordinal ('1', '2', '3'), by the line number itself, or
    by a plain 'yes' when there is only one candidate. Returns the line or None.
    """
    a = (answer or "").strip().lower()
    if not a or not candidates:
        return None

    m = re.fullmatch(r"#?\s*(\d{1,2})", a)
    if m:
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(candidates):
            return candidates[idx]["line"]

    digits = "".join(c for c in a if c.isdigit())
    if len(digits) >= 6:
        for c in candidates:
            if "".join(ch for ch in str(c.get("line", "")) if ch.isdigit()) == digits:
                return c["line"]

    if len(candidates) == 1 and a in (
        "yes", "si", "sí", "ok", "okay", "correct", "confirm", "yeah", "that one", "ese", "este"
    ):
        return candidates[0]["line"]

    return None


def _clean(value):
    """Drop Swagger's literal 'string' placeholder so it doesn't pollute a turn."""
    if value is None:
        return None
    return None if value.strip().lower() == "string" else value


@app.post("/ask")
async def ask(req: AskRequest):
    question = _clean(req.question)
    answer = _clean(req.answer)

    # ---- Resolve or create the conversation session ----
    sess = _get_session(req.session_id)
    if sess is not None:
        sid = req.session_id
    else:
        if not question:
            return {
                "status": "error",
                "message": "Send a 'question' to start, or a valid 'session_id' to continue.",
            }
        sid, sess = _create_session(question)

    # `route_query` overrides what we route on this turn — set when the user
    # confirms one of the ITEM candidates (we route straight to its line number).
    route_query = None

    if answer:
        sess["answers"].append(answer)

        # 1) Confirming a previously-offered item -> route directly to its line.
        if sess.get("candidate_kind") == "item":
            picked_line = _pick_item(answer, sess["candidates"])
            if picked_line:
                route_query = picked_line

        # 2) Otherwise, try to lock a branch from the answer: an explicit tree
        #    code/section ("31.36"), or the name/number of an offered candidate.
        if route_query is None:
            coded = chapter_reference(answer)
            is_prefix_of_lock = (
                len(coded) <= len(sess["locked_path"])
                and sess["locked_path"][: len(coded)] == coded
            )
            if coded and not is_prefix_of_lock:
                sess["locked_path"] = coded
            else:
                chosen = _pick_candidate(answer, sess["candidates"])
                if chosen and chosen not in sess["locked_path"]:
                    sess["locked_path"].append(chosen)

    combined = route_query or _combined_text(sess)

    # ---- Route (offline) + scrape if confident, off the event loop ----
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        _executor, _run_scraper, combined, list(sess["locked_path"])
    )

    # ---- Multi-turn bookkeeping ----
    if isinstance(result, dict) and result.get("status") == "needs_clarification":
        # Still ambiguous: remember the candidates we just offered and their kind
        # (item vs division) so the next answer is interpreted correctly.
        with _SESSIONS_LOCK:
            sess["candidates"] = result.get("candidates", [])
            sess["candidate_kind"] = result.get("match_type", "division")
            sess["last_seen"] = time.time()
        result["session_id"] = sid
        result["locked_path"] = list(sess["locked_path"])
        return result

    # Answered (or errored): the conversation is done, drop the session.
    _drop_session(sid)
    if isinstance(result, dict):
        result.setdefault("status", "ok")
        result["session_id"] = sid
    return result
