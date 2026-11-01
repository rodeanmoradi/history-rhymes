"""Embed Wikipedia history articles into the Pinecone index, one dataset shard at a time.

The dataset has 86 parquet shards. Finished shards are recorded in data/index_progress.json, so an interrupted run
picks up where it stopped. Upserts are keyed by article title, so re-running a half-finished shard is harmless.

    python -m scripts.build_index --status       # which shards are already in the index (cheap: 1 embedding each)
    python -m scripts.build_index                # index every shard not marked done
    python -m scripts.build_index --shards 40-45
"""
import argparse
import itertools
import json
import time

from datasets import load_dataset
from huggingface_hub import list_repo_files

from app.config import DATA_DIR, EMBED_MODEL, index, open_ai_client
from app.keywords import keyword_filter

REPO = "wikimedia/structured-wikipedia"
PROGRESS = DATA_DIR / "index_progress.json"
BATCH = 200
MAX_TOKENS = 8191
MAX_METADATA_BYTES = 30_000  # Pinecone's limit is 40 KB per vector


def shard_files():
    files = [f for f in list_repo_files(REPO, repo_type="dataset") if f.startswith("enwiki/data/") and f.endswith(".parquet")]
    return sorted(files, key=lambda f: int(f.rsplit("_", 1)[1].split(".")[0]))


def load_shard(path):
    return load_dataset(REPO, data_files=path, split="train", streaming=True).filter(keyword_filter)


def load_progress():
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text())
    return {"done": []}


def save_progress(progress):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROGRESS.write_text(json.dumps(progress, indent=2))


def vector_id(name):
    # Kept identical to the original indexing run so existing vectors are overwritten, not duplicated.
    return name.encode("ascii", errors="ignore").decode("ascii")


def fit_metadata(abstract):
    data = abstract.encode("utf-8")
    if len(data) <= MAX_METADATA_BYTES:
        return abstract
    return data[:MAX_METADATA_BYTES].decode("utf-8", errors="ignore")


def with_retries(fn, attempts=5):
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as e:
            if attempt == attempts - 1:
                raise
            wait = 2 ** attempt * 5
            print(f"    {e.__class__.__name__}: {e}; retrying in {wait}s")
            time.sleep(wait)


def upsert_batch(rows, enc):
    rows = [r for r in rows if vector_id(r["name"])]
    texts = []
    for r in rows:
        tokens = enc.encode(r["abstract"])
        texts.append(enc.decode(tokens[:MAX_TOKENS]) if len(tokens) > MAX_TOKENS else r["abstract"])
    response = with_retries(lambda: open_ai_client().embeddings.create(input=texts, model=EMBED_MODEL))
    vectors = [
        {"id": vector_id(r["name"]), "values": item.embedding, "metadata": {"abstract": fit_metadata(r["abstract"])}}
        for r, item in zip(rows, response.data)
    ]
    with_retries(lambda: index().upsert(vectors=vectors))
    return response.usage.total_tokens


def build_shard(path, enc):
    total_rows = total_tokens = 0
    batch = []
    for row in load_shard(path):
        batch.append(row)
        if len(batch) == BATCH:
            total_tokens += upsert_batch(batch, enc)
            total_rows += len(batch)
            batch = []
            if total_rows % 5000 == 0:
                print(f"    {total_rows} articles")
    if batch:
        total_tokens += upsert_batch(batch, enc)
        total_rows += len(batch)
    return total_rows, total_tokens


def in_index(path):
    """A shard counts as started if its first matching article is the top hit for its own abstract."""
    first = next(iter(load_shard(path)), None)
    if first is None:
        return True
    vector = open_ai_client().embeddings.create(input=first["abstract"][:20_000], model=EMBED_MODEL).data[0].embedding
    match = index().query(vector=vector, top_k=1).matches
    return bool(match) and match[0].id == vector_id(first["name"])


def parse_range(spec, n):
    if not spec:
        return range(n)
    start, _, end = spec.partition("-")
    return range(int(start), int(end or start) + 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--status", action="store_true", help="check which shards are already in the index")
    parser.add_argument("--shards", help="shard range to index, e.g. 40-45 (default: all)")
    args = parser.parse_args()

    files = shard_files()
    progress = load_progress()

    if args.status:
        for i in parse_range(args.shards, len(files)):
            started = in_index(files[i])
            print(f"shard {i:>2}: {'in index' if started else 'missing'}{' (marked done)' if i in progress['done'] else ''}")
        return

    import tiktoken
    enc = tiktoken.encoding_for_model(EMBED_MODEL)
    for i in parse_range(args.shards, len(files)):
        if i in progress["done"]:
            continue
        print(f"shard {i}: {files[i]}")
        start = time.monotonic()
        rows, tokens = build_shard(files[i], enc)
        progress["done"] = sorted(set(progress["done"]) | {i})
        save_progress(progress)
        print(f"shard {i}: {rows} articles, {tokens:,} tokens, {time.monotonic() - start:.0f}s")


if __name__ == "__main__":
    main()
