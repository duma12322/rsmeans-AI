import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.scraper import start_browser

app = FastAPI()

# correr el scraper en un hilo dedicado con su propio Proactor loop.
_executor = ThreadPoolExecutor(max_workers=1)


def _run_scraper(question: str):
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(start_browser(question))
    finally:
        loop.close()


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        description="Natural-language cost question, e.g. 'Cost to paint interior walls'",
        examples=["Cost to paint interior walls"],
    )


@app.post("/ask")
async def ask(req: AskRequest):
    loop = asyncio.get_running_loop()
    rows = await loop.run_in_executor(_executor, _run_scraper, req.question)
    return {"rows": rows}
