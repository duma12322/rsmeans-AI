import os
import json
import time
import tempfile
import threading

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

SESSION_FILE = os.path.join(
    BASE_DIR,
    "..",
    "session.json"
)

SESSION_EXPIRATION = 600

# Guards the read/replace of the session file so two logins (or a login racing a
# read) can't observe a half-written session. The scrape currently runs on a
# single dedicated worker, but this keeps the cache correct if that ever changes.
_SESSION_LOCK = threading.Lock()


def is_session_valid():
    """True when a cached session exists and is younger than SESSION_EXPIRATION.

    Freshness is the session file's OWN mtime — there is no separate timestamp
    file that could fall out of sync with the cookies it describes. The mtime is
    set atomically by the os.replace() in save_session.
    """
    with _SESSION_LOCK:
        try:
            age = time.time() - os.path.getmtime(SESSION_FILE)
        except OSError:
            return False
    return age < SESSION_EXPIRATION


def touch_session():
    """Slide the cache window: mark the cached session as freshly used.

    is_session_valid measures the session file's mtime, so bumping it to 'now'
    AFTER a successful scrape means the SESSION_EXPIRATION window counts from the
    last USE, not the last login — continuous use never forces a re-login, and it
    only re-authenticates after real inactivity.

    Call this ONLY right after a scrape that actually worked (which proves the
    cookies are still alive). Touching an unproven session would keep a dead one
    alive forever and every request would then fail behind a logged-out wall.
    """
    with _SESSION_LOCK:
        try:
            os.utime(SESSION_FILE, None)
        except OSError:
            pass


async def save_session(context):
    """Persist Playwright's storage state atomically.

    We grab the state as a dict, write it to a temp file in the SAME directory,
    then os.replace() it onto the real path. os.replace is an atomic rename, so a
    concurrent reader never sees a truncated/half-written file, and the rename
    stamps a fresh mtime — which is exactly what is_session_valid reads, so the
    cookies and their freshness timestamp can never disagree.
    """
    state = await context.storage_state()

    target_dir = os.path.dirname(os.path.abspath(SESSION_FILE))
    fd, tmp = tempfile.mkstemp(dir=target_dir, prefix=".session.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f)
        with _SESSION_LOCK:
            os.replace(tmp, SESSION_FILE)
    except BaseException:
        # The replace never happened — drop the orphan temp file.
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
