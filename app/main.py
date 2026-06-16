from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.scraper import start_browser

app = FastAPI()


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        description="Natural-language cost question, e.g. 'Cost to paint interior walls'",
        examples=["Cost to paint interior walls"],
    )


@app.post("/ask")
async def ask(req: AskRequest):
    rows = await start_browser(req.question)
    return {"rows": rows}