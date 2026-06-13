from fastapi import FastAPI
from app.scraper import start_browser

app = FastAPI()

@app.post("/ask")
async def ask(req: dict):
    rows = await start_browser(req["question"])
    return {"rows": rows}