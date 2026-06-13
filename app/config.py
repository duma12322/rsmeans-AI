import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
MARCE_API_URL = os.getenv("MARCE_API_URL")

if not DEEPSEEK_API_KEY:
    raise Exception("Missing DEEPSEEK_API_KEY")

if not MARCE_API_URL:
    raise Exception("Missing MARCE_API_URL")