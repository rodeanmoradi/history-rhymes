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

for row in historical_dataset:
    print(row["name"])

