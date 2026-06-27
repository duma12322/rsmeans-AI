import sqlite3
from contextlib import closing
from datetime import datetime, timezone

DB_PATH = "data.db"


def init_db():
    # `closing` guarantees the connection is closed even on error; the inner
    # `with conn:` runs the statements in a transaction (commit on success,
    # rollback on exception).
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT,
                c3 TEXT,
                c4 TEXT,
                final_code TEXT,
                final_name TEXT,
                line_number TEXT,
                data TEXT
            )
        """)

        # Live-scrape failures (login/grid/timeout/stale path), so they can be
        # reviewed instead of vanishing into the console.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                question TEXT,
                path TEXT,
                message TEXT,
                error TEXT
            )
        """)

        # Add line_number to pre-existing tables (older DBs created before this column).
        cols = [row[1] for row in cur.execute("PRAGMA table_info(results)").fetchall()]
        if "line_number" not in cols:
            cur.execute("ALTER TABLE results ADD COLUMN line_number TEXT")


def log_error(question, path, message, error=None):
    """Persist a scrape failure to the `errors` table. Best-effort: never raises,
    so a logging problem can't mask the original error."""
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn, conn:
            conn.execute("""
                INSERT INTO errors (created_at, question, path, message, error)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                question,
                " > ".join(path) if path else None,
                message,
                str(error) if error is not None else None,
            ))
    except Exception as e:  # noqa: BLE001 - logging must not break the request
        print(f"[db] no se pudo registrar el error: {e}")


def save_to_db(rows, question, c3, c4, final_code, final_name):
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.executemany("""
            INSERT INTO results (
                question, c3, c4, final_code, final_name, line_number, data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                question,
                c3,
                c4,
                final_code,
                final_name,
                r.get("line_number"),
                str(r),
            )
            for r in rows
        ])