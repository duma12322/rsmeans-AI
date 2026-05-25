import sqlite3
from pathlib import Path

# ===================================================
# ROOT FIX
# ===================================================
BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "rsmeans.db"

print("📦 USING DB:", DB_PATH)


# ===================================================
# CONNECTION
# ===================================================
def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


# ===================================================
# INIT DB
# ===================================================
def init_db():
    conn = get_connection()
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS master_divisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    print("✅ DB READY")


# ===================================================
# SAVE ITEMS (SAFE - NO BREAKS, NO UNIQUE ERRORS)
# ===================================================
def save_to_db(rows, level3_code, level4_code):

    conn = get_connection()
    cursor = conn.cursor()

    inserted = 0
    skipped = 0

    for r in rows:
        try:
            # 🔥 FIX CLAVE: evita duplicar mismo item exacto
            cursor.execute("""
                SELECT id FROM rsmeans_items
                WHERE level3_code = ?
                AND level4_code = ?
                AND description = ?
            """, (
                level3_code,
                level4_code,
                r["description"]
            ))

            exists = cursor.fetchone()

            if exists:
                skipped += 1
                continue

            cursor.execute("""
                INSERT INTO rsmeans_items (
                    level3_code,
                    level4_code,
                    description,
                    unit,
                    bare_total,
                    total_op
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                level3_code,
                level4_code,
                r["description"],
                r["unit"],
                r["bare_total"],
                r["total_op"]
            ))

            inserted += 1

        except Exception as e:
            print("❌ DB ERROR:", e)

    conn.commit()
    conn.close()

    print(f"💾 INSERTED: {inserted}")
    print(f"⏭️ SKIPPED: {skipped}")
    print(f"📊 TOTAL: {len(rows)}")


# ===================================================
# SAVE DIVISIONS (NO OVERWRITE, NO DELETE)
# ===================================================
def save_divisions(divisions):

    conn = get_connection()
    cursor = conn.cursor()

    for code, name in divisions:
        cursor.execute("""
            SELECT id FROM master_divisions WHERE code = ?
        """, (code,))

        if cursor.fetchone():
            continue

        cursor.execute("""
            INSERT INTO master_divisions (code, name)
            VALUES (?, ?)
        """, (code, name))

    conn.commit()
    conn.close()

    print(f"💾 DIVISIONS SAVED: {len(divisions)}")