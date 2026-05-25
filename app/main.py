import asyncio
import sys
import sqlite3

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.scraper import start_browser
from app.db import (
    init_db,
    DB_PATH
)

# ---------------------------------------------------
# WINDOWS FIX
# ---------------------------------------------------
if sys.platform == "win32":

    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )

# ---------------------------------------------------
# FASTAPI
# ---------------------------------------------------
app = FastAPI()

# ---------------------------------------------------
# CORS
# ---------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------
# SCRAPER TASK
# ---------------------------------------------------
scraper_task = None

# ---------------------------------------------------
# STARTUP
# ---------------------------------------------------
@app.on_event("startup")
async def startup():

    print("\n🚀 STARTING SYSTEM")

    init_db()

    print("✅ API READY")
    print("🌐 http://127.0.0.1:8000")
    print("📦 http://127.0.0.1:8000/items")
    print("📘 DOCS http://127.0.0.1:8000/docs")
    print("▶ START SCRAPER: POST /start-scraper")

# ---------------------------------------------------
# ROOT
# ---------------------------------------------------
@app.get("/")
def root():

    return {
        "status": "running",
        "api": "rsmeans"
    }

# ---------------------------------------------------
# GET ALL ITEMS
# ---------------------------------------------------
@app.get("/items")
def get_items():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM rsmeans_items
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]

# ---------------------------------------------------
# GET LEVEL 3
# ---------------------------------------------------
@app.get("/items/level3/{code}")
def get_level3(code: str):

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM rsmeans_items
        WHERE level3_code = ?
        ORDER BY id DESC
    """, (code,))

    rows = cursor.fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]

# ---------------------------------------------------
# GET LEVEL 4
# ---------------------------------------------------
@app.get("/items/level4/{code}")
def get_level4(code: str):

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM rsmeans_items
        WHERE level4_code = ?
        ORDER BY id DESC
    """, (code,))

    rows = cursor.fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]

# ---------------------------------------------------
# STATS
# ---------------------------------------------------
@app.get("/stats")
def stats():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM rsmeans_items
    """)

    total = cursor.fetchone()[0]

    conn.close()

    return {
        "total_rows": total
    }

# ---------------------------------------------------
# START SCRAPER
# ---------------------------------------------------
@app.post("/start-scraper")
async def start_scraper_api():

    global scraper_task

    if scraper_task and not scraper_task.done():

        return {
            "status": "already_running"
        }

    scraper_task = asyncio.create_task(
        start_browser()
    )

    return {
        "status": "scraper_started"
    }

# ---------------------------------------------------
# STOP SCRAPER
# ---------------------------------------------------
@app.post("/stop-scraper")
async def stop_scraper_api():

    global scraper_task

    if not scraper_task:

        return {
            "status": "not_running"
        }

    scraper_task.cancel()

    scraper_task = None

    return {
        "status": "scraper_stopped"
    }