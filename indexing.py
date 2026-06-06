from datasets import load_dataset
from keywords import keyword_filter
from config import open_ai_client, enc, index

def upsert_vectors(batch, names, abstracts):
    response = open_ai_client.embeddings.create(input=abstracts, model="text-embedding-3-small")
    vectors = []
    for i in range(len(batch)):
        # Ensure empty strings are excluded
        if names[i].encode('ascii', errors='ignore').decode('ascii') == "":
            continue
        vector_dict = {"id": names[i].encode('ascii', errors='ignore').decode('ascii'), "values": response.data[i].embedding, 
                       "metadata": {"abstract": abstracts[i]}}
        vectors.append(vector_dict)
    index.upsert(vectors=vectors)

def fill_batch(batch, row):
    # Append name and abstract, ensuring abstract does not exceed 8192 tokens
    tokens = enc.encode(row["abstract"])
    if len(tokens) >= 8192:
        batch.append((row["name"], enc.decode(tokens[:8192])))
    else:
        batch.append((row["name"], row["abstract"]))

def fill_index(historical_dataset):
    batch = []
    for row in historical_dataset:
        if len(batch) < 200:
            fill_batch(batch, row)
        else:
            upsert_vectors(batch, [item[0] for item in batch], [item[1] for item in batch])
            batch = []
            fill_batch(batch, row)
    upsert_vectors(batch, [item[0] for item in batch], [item[1] for item in batch])


dataset = load_dataset("wikimedia/structured-wikipedia", "enwiki_namespace_0", split="train", streaming=True)
historical_dataset = dataset.filter(keyword_filter)

fill_index(historical_dataset)