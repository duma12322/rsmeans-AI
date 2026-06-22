import sqlite3
from datetime import datetime

DB_PATH = "data.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
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

    conn.commit()
    conn.close()


def log_error(question, path, message, error=None):
    """Persist a scrape failure to the `errors` table. Best-effort: never raises,
    so a logging problem can't mask the original error."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO errors (created_at, question, path, message, error)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(timespec="seconds"),
            question,
            " > ".join(path) if path else None,
            message,
            str(error) if error is not None else None,
        ))
        conn.commit()
        conn.close()
    except Exception as e:  # noqa: BLE001 - logging must not break the request
        print(f"[db] no se pudo registrar el error: {e}")


def save_to_db(rows, question, c3, c4, final_code, final_name):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for r in rows:
        cur.execute("""
            INSERT INTO results (
                question, c3, c4, final_code, final_name, line_number, data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            question,
            c3,
            c4,
            final_code,
            final_name,
            r.get("line_number"),
            str(r)
        ))

    conn.commit()
    conn.close()