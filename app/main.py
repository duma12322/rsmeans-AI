import os
import re
import sys
import json
import time
import uuid
import queue
import asyncio
import tempfile
import threading
import unicodedata
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.scraper import start_browser
from app.navigator import chapter_reference

app = FastAPI()

# Allow the Next.js frontend (dev server + any local origin) to call the API.
# Override with FRONTEND_ORIGINS="https://app.example.com,https://..." in .env.
_origins = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

# correr el scraper en un hilo dedicado con su propio Proactor loop.
_executor = ThreadPoolExecutor(max_workers=1)

# Multi-turn conversation state:
#   {session_id: {"question", "answers", "locked_path", "candidates", "last_seen"}}
# Each clarification turn re-runs routing with the original question PLUS every
# answer (for wording), while `locked_path` records the branch the user has
# explicitly committed to so routing drills DOWN instead of restarting.
#
# This store is bounded so abandoned conversations can't leak memory:
#   - TTL: a session idle longer than SESSION_TTL is purged on the next request.
#   - Cap: at most MAX_SESSIONS live at once; the least-recently-seen is evicted.
# A lock guards the dict so concurrent requests can't corrupt it.
#
# The dict is ALSO mirrored to CONVERSATIONS_FILE on every mutation so an open
# clarification survives a server restart (uvicorn --reload, a crash): otherwise
# the frontend holds a session_id the backend forgot and the user has to retype
# the whole question. It is NOT a substitute for an external store across MULTIPLE
# uvicorn workers — each worker would still write its own file. With one worker
# (which the single RSMeans account forces anyway) that's a non-issue.
SESSION_TTL = 600        # seconds of inactivity before a conversation is dropped
MAX_SESSIONS = 500       # hard ceiling on concurrent conversations
REFINE_MAX_ROUNDS = 3    # refinement rounds on a still-broad search before we stop

CONVERSATIONS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "conversations.json"
)

_SESSIONS_LOCK = threading.Lock()


def _persist_sessions_locked():
    """Write _SESSIONS to disk atomically. Caller MUST hold _SESSIONS_LOCK.

    Same temp-file + os.replace dance as app/session.py: a concurrent reader (a
    restart mid-write) never sees a truncated file. Best-effort — a disk error
    must not take down a request, since the in-memory dict is still authoritative.
    """
    target_dir = os.path.dirname(os.path.abspath(CONVERSATIONS_FILE))
    try:
        fd, tmp = tempfile.mkstemp(dir=target_dir, prefix=".conversations.", suffix=".tmp")
    except OSError:
        return
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(_SESSIONS, f)
        os.replace(tmp, CONVERSATIONS_FILE)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _load_sessions():
    """Load persisted conversations on startup, dropping any already past TTL.

    A malformed/partial file (or none) yields an empty store rather than crashing
    boot — a lost conversation history is recoverable; a server that won't start
    is not."""
    try:
        with open(CONVERSATIONS_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    now = time.time()
    return {
        sid: v for sid, v in data.items()
        if isinstance(v, dict) and now - v.get("last_seen", 0) <= SESSION_TTL
    }


_SESSIONS = _load_sessions()


def _get_session(session_id):
    """Purge idle sessions, then return the live session for `session_id`
    (touching its last_seen) or None. Thread-safe."""
    if not session_id:
        return None
    now = time.time()
    with _SESSIONS_LOCK:
        expired = [s for s, v in _SESSIONS.items() if now - v["last_seen"] > SESSION_TTL]
        for sid in expired:
            _SESSIONS.pop(sid, None)
        sess = _SESSIONS.get(session_id)
        if sess is not None:
            sess["last_seen"] = now
        if expired:
            _persist_sessions_locked()
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
        _persist_sessions_locked()
        return sid, _SESSIONS[sid]


def _drop_session(session_id):
    with _SESSIONS_LOCK:
        if _SESSIONS.pop(session_id, None) is not None:
            _persist_sessions_locked()


def _run_scraper(question: str, start_path, progress=None, cancel=None):
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            start_browser(
                question, start_path=start_path, progress=progress, cancel=cancel
            )
        )
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
        max_length=500,
        description="Natural-language cost question (required to START a conversation).",
        examples=["Cost to paint interior walls"],
    )
    session_id: Optional[str] = Field(
        None,
        pattern=r"^[0-9a-f]{12}$",
        description="Returned by a previous needs_clarification response; send it back to continue.",
    )
    answer: Optional[str] = Field(
        None,
        min_length=1,
        max_length=500,
        description="Your reply to the clarification questions.",
    )

    @field_validator("question", "answer", mode="before")
    @classmethod
    def _normalize_text(cls, v):
        """
        Normalize free text BEFORE the length checks run: convert any whitespace
        (newlines, tabs) to single spaces, drop other control characters, trim,
        and treat blank / Swagger's literal "string" as absent (None).

        It only ever touches whitespace and control chars — NEVER digits — so an
        RSMeans code keeps every separator format intact ("09 91 23 72. 01 00",
        "09 91 23 720100", … all survive; the digits-only extractor handles them
        downstream).
        """
        if not isinstance(v, str):
            return v
        v = re.sub(r"\s+", " ", v)
        v = "".join(ch for ch in v if ch == " " or not unicodedata.category(ch).startswith("C"))
        v = v.strip()
        if not v or v.lower() == "string":
            return None
        return v

    @field_validator("session_id", mode="before")
    @classmethod
    def _normalize_session(cls, v):
        """Trim the session id and treat blank / Swagger's "string" as absent, so
        the strict pattern only validates a real id."""
        if isinstance(v, str):
            v = v.strip()
            if not v or v.lower() == "string":
                return None
        return v


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


def _prepare_turn(req: "AskRequest"):
    """
    Resolve/create the session and compute the query to route on this turn.
    Returns (sid, sess, combined, error) — on error the first three are None and
    `error` is the response dict to return. Shared by /ask and /ask/stream.
    """
    question = _clean(req.question)
    answer = _clean(req.answer)

    # ---- Resolve or create the conversation session ----
    sess = _get_session(req.session_id)
    if sess is not None:
        sid = req.session_id
    else:
        if not question:
            return None, None, None, {
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

        # Persist the new answer / locked branch now, so a crash DURING the
        # (potentially long) scrape doesn't lose this turn's progress.
        with _SESSIONS_LOCK:
            _persist_sessions_locked()

    combined = route_query or _combined_text(sess)
    return sid, sess, combined, None


def _finalize_turn(sid, sess, result):
    """Multi-turn bookkeeping: persist candidates if still ambiguous, otherwise
    drop the session. Stamps session_id onto the result. Shared by both endpoints."""
    if isinstance(result, dict) and result.get("status") == "needs_clarification":
        # Still ambiguous: remember the candidates we just offered and their kind
        # (item vs division) so the next answer is interpreted correctly.
        with _SESSIONS_LOCK:
            sess["candidates"] = result.get("candidates", [])
            sess["candidate_kind"] = result.get("match_type", "division")
            sess["last_seen"] = time.time()
            _persist_sessions_locked()
        result["session_id"] = sid
        result["locked_path"] = list(sess["locked_path"])
        return result

    # A truncated keyword search DID answer, but with too many rows to be exact.
    # Keep the session alive so the user's next REFINEMENT (a chip click) is
    # APPENDED to the original query and re-run as a narrower search. Each stored
    # answer is one refinement round; after REFINE_MAX_ROUNDS still-broad rounds
    # we stop refining this query so it can't loop forever — the user starts a
    # fresh search instead. No candidates to lock — the answer is just extra
    # search words (see `_combined_text`).
    if isinstance(result, dict) and result.get("truncated"):
        rounds = len(sess.get("answers", []))
        if rounds < REFINE_MAX_ROUNDS:
            with _SESSIONS_LOCK:
                sess["candidates"] = []
                sess["candidate_kind"] = "search"
                sess["last_seen"] = time.time()
                _persist_sessions_locked()
            result["session_id"] = sid
            result["continue_session"] = True
            return result
        # Round cap reached and still broad: stop the refinement loop. Drop the
        # session, clear the now-dead chips/questions, and leave a terminal notice.
        shown = result.get("shown_records") or len(result.get("rows") or [])
        result["refinements"] = []
        result["refine_questions"] = []
        result["continue_session"] = False
        result["notice"] = (
            f"Still a broad match — showing the closest {shown}. "
            "Start a new search to change tack."
        )
        _drop_session(sid)
        result["session_id"] = sid
        return result

    # Answered (or errored): the conversation is done, drop the session.
    _drop_session(sid)
    if isinstance(result, dict):
        result.setdefault("status", "ok")
        result["session_id"] = sid
    return result


@app.post("/ask")
async def ask(req: AskRequest):
    sid, sess, combined, error = _prepare_turn(req)
    if error is not None:
        return error

    # ---- Route (offline) + scrape if confident, off the event loop ----
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        _executor, _run_scraper, combined, list(sess["locked_path"])
    )
    return _finalize_turn(sid, sess, result)


def _sse(obj) -> str:
    """Format one Server-Sent Events frame."""
    return f"data: {json.dumps(obj)}\n\n"


@app.post("/ask/stream")
async def ask_stream(req: AskRequest, request: Request):
    """
    Same as /ask, but streams real progress milestones (Server-Sent Events) while
    the scraper runs, then a final `{"type":"result", "data": <ask-response>}`.

    The scraper still runs on the dedicated Proactor thread; it pushes phase names
    ("analyzing", "opening", "login", "navigating", "scraping") into a thread-safe
    queue that this generator drains on the event loop — no browser call moves
    onto the FastAPI loop.

    Cancellation: a thread in the executor can't be killed, so when the client
    disconnects (the user hits Stop) we set a threading.Event the scraper polls at
    each phase boundary. It then unwinds, closes the browser, and frees the single
    worker — instead of finishing the whole scrape in the background and blocking
    the next request.
    """
    sid, sess, combined, error = _prepare_turn(req)
    if error is not None:
        async def _err_gen():
            yield _sse({"type": "result", "data": error})
        return StreamingResponse(_err_gen(), media_type="text/event-stream")

    locked = list(sess["locked_path"])

    async def _gen():
        events: "queue.Queue" = queue.Queue()
        cancel = threading.Event()

        # Called from the scraper thread; queue.put is thread-safe.
        def progress(phase, detail=None):
            events.put({"type": "progress", "phase": phase, "detail": detail})

        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(
            _executor, _run_scraper, combined, locked, progress, cancel
        )
        # Retrieve any exception once the future settles so a cancelled scrape
        # doesn't log an "exception was never retrieved" warning.
        future.add_done_callback(lambda f: f.cancelled() or f.exception())

        try:
            # Relay progress events as they arrive; poll the queue without blocking
            # the loop. Also watch for the client going away so we can stop early.
            while not future.done():
                try:
                    yield _sse(events.get_nowait())
                except queue.Empty:
                    if await request.is_disconnected():
                        return  # `finally` signals the scraper to stop
                    await asyncio.sleep(0.05)
            # Flush any events queued in the final moment.
            while True:
                try:
                    yield _sse(events.get_nowait())
                except queue.Empty:
                    break

            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001 - surface as a result, not a 500
                result = {
                    "status": "error",
                    "message": "Hubo un problema procesando la consulta.",
                    "error": str(exc),
                }
            # A cooperatively-cancelled scrape returns this; the client is already
            # gone, so just stop without finalizing the turn.
            if isinstance(result, dict) and result.get("status") == "cancelled":
                return
            final = _finalize_turn(sid, sess, result)
            yield _sse({"type": "result", "data": final})
        finally:
            # Generator closed early (client disconnected, GeneratorExit) or we
            # returned on is_disconnected: tell the still-running scraper to stop.
            cancel.set()

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
