from datasets import load_dataset
from keywords import keyword_filter
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
import os

load_dotenv()
client = OpenAI()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(host=os.getenv("PINECONE_HOST"))

def store_vectors(batch, names, abstracts):
    response = client.embeddings.create(input=abstracts, model="text-embedding-3-small")
    vectors = []
    for i in range(len(batch)):
        # Ensure empty strings are excluded
        if names[i].encode('ascii', errors='ignore').decode('ascii') == "":
            continue
        vector_dict = {"id": names[i].encode('ascii', errors='ignore').decode('ascii'), "values": response.data[i].embedding}
        vectors.append(vector_dict)
    index.upsert(vectors=vectors)

dataset = load_dataset("wikimedia/structured-wikipedia", "enwiki_namespace_0", split="train", streaming=True)
historical_dataset = dataset.filter(keyword_filter)

batch = []
for row in historical_dataset:
    if len(batch) < 400:
        batch.append((row["name"], row["abstract"][:20000]))
    else:
        store_vectors(batch, [item[0] for item in batch], [item[1] for item in batch])
        batch = []
        batch.append((row["name"], row["abstract"][:20000]))
store_vectors(batch, [item[0] for item in batch], [item[1] for item in batch])