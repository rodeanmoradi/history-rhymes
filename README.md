# History Rhymes

Pick a news headline; get a two-minute, stick-figure-illustrated lesson on the historical event that most closely
followed the same pattern, including where the comparison breaks down.

Under the hood it is an **agentic RAG pipeline**: a dense-retrieval archive of Wikipedia history articles and a
web-research sub-agent produce candidates, and a Claude agent decides whether they are good enough or whether to
re-query with a rewritten, mechanism-level description before choosing.

## How it works

```
NewsAPI ──► headline triage (Claude, structured output) ──► front page
                                                              │ user picks a headline
                                                              ▼
            ┌──────────── parallel ────────────┐
            │                                  │
   search_archive(headline)            research_web(headline)
   OpenAI embedding → Pinecone          Claude + web_search server tool
   (~740k Wikipedia abstracts)          (3 candidates, cited URLs)
            │                                  │
            └──────────────┬───────────────────┘
                           ▼
              chooser agent (Claude, tools + structured output)
              may call search_archive / research_web again with a
              rewritten "mechanism" query — at most 2 rounds
                           │  Choice {parallel, archive_title, why, where_it_breaks, runners_up}
                           ▼
              lesson writer (Claude, structured output)
              sections + scene specs + then/now + caveats, validated & retried
                           │
                           ▼
              SQLite cache ──► FastAPI ──► browser renders scenes as SVG stick figures (static/sketch.js)
```

| Piece | File |
| --- | --- |
| Retrieval (embed + Pinecone query) | `app/retrieval.py` |
| Web-research sub-agent, chooser agent loop | `app/agents.py` |
| Lesson schema, scene vocabulary, output validation | `app/lesson.py` |
| Prompts | `app/prompts.py` |
| Per-call token / latency / cost tracing | `app/trace.py` |
| Headline fetch + triage | `app/news.py` |
| API + background jobs + SQLite cache | `app/server.py`, `app/store.py` |
| Stick-figure renderer | `static/sketch.js` |
| Resumable index builder | `scripts/build_index.py` |

### Design notes

- **Constrained generation for the illustrations.** The model never draws. It fills a small typed vocabulary
  (13 poses, 9 hats, 27 props, 5 positions) through structured outputs, and a deterministic renderer draws it with a
  seeded hand-drawn wobble. That keeps a consistent house style, makes every drawing reproducible, and costs nothing
  per image.
- **Query rewriting as an agent action.** Embedding the raw headline retrieves articles that share its *words*; the
  agent can instead query with the underlying mechanism ("creditor forcing austerity on a debtor"). The eval in
  `eval/` measures how much that matters.
- **Output validation.** Schema-valid structured output can still be degenerate (we observed one-section lessons with
  `"x"` in every other field), so lessons are checked and regenerated once before failing.
- **Observability.** Every model and embedding call is traced (tokens, cache hits, web searches, latency, cost); each
  lesson page shows the totals under "How this lesson was made". In the first test runs a lesson took about 70 s and cost $0.19–0.25.
- **Refusal handling.** Calls use server-side refusal fallback (`fallbacks: "default"`) and check `stop_reason`
  before reading content.

## Running it

Requires Python 3.12 and keys for Anthropic, OpenAI, Pinecone and NewsAPI in `.env`:

```
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
PINECONE_API_KEY=...
PINECONE_HOST=...
NEWSAPI_API_KEY=...
MAX_LESSONS_PER_DAY=50   # optional spend guard
```

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.server:app --reload        # http://localhost:8000
python cli.py "Some headline"          # terminal version, prints the lesson JSON
```

Docker:

```bash
docker build -t history-rhymes .
docker run -p 8000:8000 --env-file .env -v hr-data:/srv/data history-rhymes
```

NewsAPI's free plan is for development only; a public deployment needs a paid plan or another news source.

## The index

`scripts/build_index.py` streams `wikimedia/structured-wikipedia` (English, 86 parquet shards), keeps articles whose
title or abstract matches the keyword list in `app/keywords.py`, embeds the abstracts with `text-embedding-3-small`
and upserts them to Pinecone. Progress is recorded per shard, so an interrupted run resumes.

```bash
pip install -r requirements-index.txt
python -m scripts.build_index --status   # which shards are already indexed
python -m scripts.build_index            # index the rest
```

**Known gap:** the current index (~742k vectors) was built by an earlier run that stopped partway, so many major
articles (e.g. *Battle of Hastings*, *Cuban Missile Crisis*) are missing, and the keyword filter also admits noise
(films, albums, video games, disambiguation pages). The web-research path covers for this today.

## Evaluation

See `eval/`. (In progress.)
