from datasets import load_dataset
from keywords import words
from dotenv import load_dotenv
from openai import OpenAI
import re

load_dotenv()
client = OpenAI()

# https://huggingface.co/datasets/wikimedia/structured-wikipedia
dataset = load_dataset("wikimedia/structured-wikipedia", "enwiki_namespace_0", split="train", streaming=True)

# Create historical filter by doing keyword search on abstract and name; TODO: look into semantic filtering
def word_search(dataset):
    if dataset["abstract"] != None:
        for word in words:
            if re.search(r'\b' + word + r'\b', dataset["abstract"].lower()):
                return True    
    for word in words:
        if re.search(r'\b' + word + r'\b', dataset["name"].lower()):
            return True
    
    return False

historical_dataset = dataset.filter(word_search)

batch = []
for row in historical_dataset:
    if len(batch) < 500:
        batch.append(row["abstract"])
    else:
        response = client.embeddings.create(input=batch, model="text-embedding-3-small")
        # Save to vector, keep track of name
        batch = []
        batch.append(row["abstract"])
response = client.embeddings.create(input=batch, model="text-embedding-3-small")
# Save to vector db