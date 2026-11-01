import os
from functools import lru_cache
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from newsapi import NewsApiClient
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "app.db"

MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
EMBED_MODEL = "text-embedding-3-small"

# Effort per pipeline stage. Opus 5.5 defaults to medium, so set each one explicitly.
SEARCH_EFFORT = "low"
AGENT_EFFORT = "medium"
LESSON_EFFORT = "high"

# Server-side refusal fallback: a declined request is re-run on Anthropic's recommended model.
BETAS = ["server-side-fallback-2026-07-01"]
FALLBACKS = {"fallbacks": "default"}

MAX_LESSONS_PER_DAY = int(os.getenv("MAX_LESSONS_PER_DAY", "50"))

# USD per million tokens, used for the cost shown on each lesson and in eval reports.
PRICES = {
    "claude-opus-5-5": {"in": 4.00, "out": 20.00},
    "claude-opus-5": {"in": 5.00, "out": 25.00},
    "claude-opus-4-8": {"in": 5.00, "out": 25.00},
    "claude-sonnet-5-5": {"in": 2.00, "out": 10.00},
    "claude-haiku-5-5": {"in": 0.10, "out": 0.50},
    EMBED_MODEL: {"in": 0.02, "out": 0.0},
}
WEB_SEARCH_PRICE = 0.01  # per search


@lru_cache
def anthropic_client():
    return anthropic.Anthropic()


@lru_cache
def open_ai_client():
    return OpenAI()


@lru_cache
def news_api_client():
    return NewsApiClient(api_key=os.getenv("NEWSAPI_API_KEY"))


@lru_cache
def index():
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    return pc.Index(host=os.getenv("PINECONE_HOST"))
