import time

from app.config import EMBED_MODEL, index, open_ai_client

TOP_K = 5


def embed(texts, trace=None, step="embed"):
    start = time.monotonic()
    response = open_ai_client().embeddings.create(input=texts, model=EMBED_MODEL)
    if trace is not None:
        trace.add_embedding(step, EMBED_MODEL, response.usage.total_tokens, time.monotonic() - start)
    return [item.embedding for item in response.data]


def search_archive(text, top_k=TOP_K, trace=None):
    """Semantic search over the Wikipedia history index. Returns [{title, abstract, score}]."""
    vector = embed([text], trace, step="search_archive")[0]
    retrieval = index().query(vector=vector, top_k=top_k, include_metadata=True)
    return [
        {"title": match.id, "abstract": match.metadata["abstract"], "score": round(match.score, 4)}
        for match in retrieval.matches
    ]


def preview(abstract, words=120):
    # The agent only needs enough of each abstract to judge relevance; full text goes to the lesson writer.
    tokens = abstract.split()
    if len(tokens) <= words:
        return abstract
    return " ".join(tokens[:words]) + " …"


def format_results(results):
    if not results:
        return "No matching articles."
    return "\n\n".join(
        f"[{i}] {r['title']} (similarity {r['score']:.2f})\n{preview(r['abstract'])}"
        for i, r in enumerate(results, 1)
    )
