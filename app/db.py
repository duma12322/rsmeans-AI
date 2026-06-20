import sqlite3

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

    # Add line_number to pre-existing tables (older DBs created before this column).
    cols = [row[1] for row in cur.execute("PRAGMA table_info(results)").fetchall()]
    if "line_number" not in cols:
        cur.execute("ALTER TABLE results ADD COLUMN line_number TEXT")

    conn.commit()
    conn.close()


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