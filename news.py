from newsapi import NewsApiClient
from dotenv import load_dotenv
from keywords import words
from openai import OpenAI
from pinecone import Pinecone
import anthropic
import os

load_dotenv()
client = OpenAI()
client = anthropic.Anthropic()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(host=os.getenv("PINECONE_HOST"))

newsapi = NewsApiClient(api_key=os.getenv("NEWSAPI_API_KEY"))
top_headlines = newsapi.get_top_headlines(category='general', language='en', country='us')

filtered_headlines = []
for item in top_headlines["articles"]:
    for word in words:
        if word in item["title"]:
            filtered_headlines.append(item["title"])
            break

for i in range(len(filtered_headlines)):
    print(f'Index: {i}, Title: {filtered_headlines[i]}')

# User input to select article
idx = int(input("Select index: "))
article = filtered_headlines[idx]

# Embed and query
response = client.embeddings.create(input=article, model="text-embedding-3-small")
results = index.query(vector=response.data[0].embedding, top_k=5)

for match in results.matches:
    print(match.id)

# Pass similar articles to Claude, get most intriguing, generate lesson about topic

#message = client.messages.create(
#  model="claude-opus-4-8",
#  max_tokens=1024,
#  messages=[{
#    "role": "user",
#    "content": ""
#  }]
#)