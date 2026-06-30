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
                created_at TEXT,
                question TEXT,
                c3 TEXT,
                c4 TEXT,
                final_code TEXT,
                final_name TEXT,
                path TEXT,
                line_number TEXT,
                description TEXT,
                unit TEXT,
                bare_total REAL,
                total_op REAL
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

        # Additively migrate older DBs to the split-column schema. Each column is
        # added only if missing, so this is safe to run on any existing data.db.
        cols = [row[1] for row in cur.execute("PRAGMA table_info(results)").fetchall()]
        for name, decl in (
            ("created_at", "TEXT"),
            ("path", "TEXT"),
            ("line_number", "TEXT"),
            ("description", "TEXT"),
            ("unit", "TEXT"),
            ("bare_total", "REAL"),
            ("total_op", "REAL"),
        ):
            if name not in cols:
                cur.execute(f"ALTER TABLE results ADD COLUMN {name} {decl}")


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


def save_to_db(rows, question, c3, c4, final_code, final_name, path=None):
    """Persist each scraped grid row as its own typed record. Costs are stored as
    REAL numbers (no `$`); formatting for display happens at the edge, not here.
    `path` is the full route (list of codes) the row came from, stored as a
    "a > b > c" string so a saved result is self-describing."""
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path_str = " > ".join(path) if path else None
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.executemany("""
            INSERT INTO results (
                created_at, question, c3, c4, final_code, final_name, path,
                line_number, description, unit, bare_total, total_op
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                created_at,
                question,
                c3,
                c4,
                final_code,
                final_name,
                path_str,
                r.get("line_number"),
                r.get("description"),
                r.get("unit"),
                r.get("bare_total"),
                r.get("total_op"),
            )
            for r in rows
        ])