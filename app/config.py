import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
MARCE_API_URL = os.getenv("MARCE_API_URL")

# RSMeans login. Browser-only, so it is NOT validated here (routing/eval don't
# need it) — the scraper checks it right before logging in.
RS_EMAIL = os.getenv("RS_EMAIL")
RS_PASSWORD = os.getenv("RS_PASSWORD")

if not DEEPSEEK_API_KEY:
    raise Exception("Missing DEEPSEEK_API_KEY")

if not MARCE_API_URL:
    raise Exception("Missing MARCE_API_URL")