import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import pipeline, store
from app.config import MAX_LESSONS_PER_DAY, ROOT
from app.news import top_headlines

log = logging.getLogger("uvicorn.error")
STATIC = ROOT / "static"
workers = ThreadPoolExecutor(max_workers=2)


@asynccontextmanager
async def lifespan(app):
    for id in store.interrupted():
        store.fail(id, "Interrupted by a server restart.")
    yield
    workers.shutdown(wait=False, cancel_futures=True)


app = FastAPI(title="History Rhymes", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class LessonRequest(BaseModel):
    headline: str = Field(min_length=10, max_length=300)
    source: str | None = None
    url: str | None = None


def build(id, headline):
    try:
        result = pipeline.run(headline, on_step=lambda message: store.add_step(id, message))
        store.finish(id, result)
    except Exception as e:
        log.exception("lesson %s failed", id)
        store.fail(id, str(e) or e.__class__.__name__)


@app.get("/api/headlines")
def headlines():
    try:
        return top_headlines()
    except Exception as e:
        log.exception("headline fetch failed")
        raise HTTPException(502, f"Couldn't fetch today's headlines: {e}")


@app.post("/api/lessons")
def start_lesson(request: LessonRequest):
    headline = " ".join(request.headline.split())
    url = request.url if request.url and request.url.startswith(("http://", "https://")) else None
    id = store.lesson_id(headline)
    existing = store.get(id)
    if existing and existing["status"] != "failed":
        return {"id": id}

    if store.created_today() >= MAX_LESSONS_PER_DAY:
        raise HTTPException(429, "That's all the lessons for today. Try one of the recent ones.")
    if existing:
        store.requeue(id)
    else:
        store.create(id, headline, request.source, url)
    workers.submit(build, id, headline)
    return {"id": id}


@app.get("/api/lessons")
def recent_lessons(limit: int = 10):
    return store.recent(min(limit, 50))


@app.get("/api/lessons/{id}")
def get_lesson(id: str):
    record = store.get(id)
    if record is None:
        raise HTTPException(404, "No such lesson.")
    return record


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/l/{id}")
def lesson_page(id: str):
    return FileResponse(STATIC / "lesson.html")


@app.get("/about")
def about():
    return FileResponse(STATIC / "about.html")
