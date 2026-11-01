import logging
import re
import threading
import time

from pydantic import BaseModel

from app.agents import create
from app.config import news_api_client
from app.keywords import words
from app.trace import Trace

CACHE_SECONDS = 60 * 60
CATEGORIES = ["general", "business", "science", "technology", "health"]
MAX_HEADLINES = 12

_cache = {"at": 0.0, "headlines": []}
_KEYWORDS = re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b")
log = logging.getLogger("uvicorn.error")
_lock = threading.Lock()

TRIAGE_PROMPT = """Below are today's news headlines. Pick up to {n} that would pair well with a lesson from history: stories
about power, conflict, money, migration, technology, disease, law or institutions, where some past event plausibly
followed the same pattern. Skip celebrity, sport, product reviews, games, horoscopes, weather and crime stories about
private individuals. Return the indices of your picks, best first.

{headlines}"""


class Picks(BaseModel):
    indices: list[int]


def clean_title(title):
    # NewsAPI titles end with " - Source Name"; the source is shown separately.
    return re.sub(r"\s+-\s+[^-]+$", "", title).strip()


def fetch_articles():
    client = news_api_client()
    seen = set()
    articles = []
    for category in CATEGORIES:
        response = client.get_top_headlines(category=category, language="en", page_size=100)
        for item in response["articles"]:
            title = clean_title(item["title"] or "")
            if not title or title == "[Removed]" or title in seen:
                continue
            seen.add(title)
            articles.append({
                "title": title,
                "source": item["source"]["name"],
                "url": item["url"],
                "published_at": item["publishedAt"],
            })
    return articles


def triage(articles):
    listing = "\n".join(f"{i}. {a['title']}" for i, a in enumerate(articles))
    response = create(
        Trace(), "triage_headlines",
        parse=True,
        max_tokens=2000,
        output_config={"effort": "low"},
        output_format=Picks,
        messages=[{"role": "user", "content": TRIAGE_PROMPT.format(n=MAX_HEADLINES, headlines=listing)}],
    )
    picks = [i for i in response.parsed_output.indices if 0 <= i < len(articles)]
    return [articles[i] for i in dict.fromkeys(picks)][:MAX_HEADLINES]


def top_headlines():
    """Today's headlines that are worth a history lesson, refreshed hourly."""
    with _lock:
        if time.time() - _cache["at"] < CACHE_SECONDS and _cache["headlines"]:
            return _cache["headlines"]
        articles = fetch_articles()
        fetched_at = time.time()
        try:
            headlines = triage(articles)
        except Exception:
            # Without the model, fall back to the archive's keyword list (cruder, but never empty-handed),
            # and try the model again in five minutes rather than an hour.
            log.exception("headline triage failed; using keyword filter")
            headlines = [a for a in articles if _KEYWORDS.search(a["title"].lower())][:MAX_HEADLINES]
            fetched_at -= CACHE_SECONDS - 5 * 60
        _cache.update(at=fetched_at, headlines=headlines)
        return headlines
