from datasets import load_dataset
from keywords import words
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
import re
import os

load_dotenv()
client = OpenAI()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_HOST"))

# dataset url: https://huggingface.co/datasets/wikimedia/structured-wikipedia
dataset = load_dataset("wikimedia/structured-wikipedia", "enwiki_namespace_0", split="train", streaming=True)

# Create historical filter by doing keyword search on abstract and name
def word_search(dataset):
    if dataset["abstract"] is not None:
        for word in words:
            if re.search(r'\b' + word + r'\b', dataset["abstract"].lower()):
                return True    
        for word in words:
            if re.search(r'\b' + word + r'\b', dataset["name"].lower()):
                return True
    return False

# embed abstracts and store in database
def store_vectors(names, abstracts):
    response = client.embeddings.create(input=abstracts, model="text-embedding-3-small")
    vectors = []
    for i in range(len(batch)):
        vector_dict = {"id": names[i], "values": response.data[i].embedding}
        vectors.append(vector_dict)
    index.upsert(vectors)

historical_dataset = dataset.filter(word_search)
batch = []
for row in historical_dataset:
    if len(batch) < 200:
        batch.append((row["name"], row["abstract"]))
    else:
        store_vectors([item[0] for item in batch], [item[1] for item in batch])
        batch = []
        batch.append((row["name"], row["abstract"]))
store_vectors([item[0] for item in batch], [item[1] for item in batch])