import asyncio
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.scraper import start_browser
from app.db import init_db

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    print("🚀 STARTING SYSTEM")
    init_db()
    asyncio.create_task(start_browser())


@app.get("/")
def root():
    return {"status": "running"}