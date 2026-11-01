from app.agents import find_parallel
from app.lesson import write_lesson
from app.trace import Trace


def run(headline, on_step=lambda message: None):
    """Headline in, illustrated lesson out. Returns the lesson plus everything needed to audit it."""
    trace = Trace()
    choice, evidence = find_parallel(headline, trace, on_step)
    on_step(f"Writing the lesson on {choice['parallel']}")
    lesson = write_lesson(headline, choice, evidence, trace)

    seen = set()
    web_sources = []
    for source in evidence.web_sources:
        if source["url"] not in seen:
            seen.add(source["url"])
            web_sources.append(source)

    return {
        "choice": choice,
        "lesson": lesson,
        "sources": {
            "archive": [{"title": t, "score": r["score"]} for t, r in evidence.archive.items()],
            "web": web_sources[:8],
        },
        "trace": trace.summary(),
    }
