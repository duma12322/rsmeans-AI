import sqlite3
import os

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DB_PATH = os.path.join(BASE_DIR, "rsmeans.db")

print("📦 DB:", DB_PATH)


def init_db():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rsmeans_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level3_code TEXT,
            level4_code TEXT,
            description TEXT,
            unit TEXT,
            bare_total REAL,
            total_op REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    print("✅ DB READY")


def save_to_db(rows, level3_code, level4_code):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    values = []

    for r in rows:
        values.append((
            level3_code,
            level4_code,
            r["description"],
            r["unit"],
            r["bare_total"],
            r["total_op"]
        ))

    cursor.executemany("""
        INSERT INTO rsmeans_items (
            level3_code,
            level4_code,
            description,
            unit,
            bare_total,
            total_op
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, values)

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM rsmeans_items")
    total = cursor.fetchone()[0]

    print(f"💾 INSERTED: {len(values)}")
    print(f"📊 TOTAL DB ROWS: {total}")

    conn.close()