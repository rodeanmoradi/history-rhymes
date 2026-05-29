from config import open_ai_client, anthropic_client, news_api_client, index
from keywords import words

top_headlines = news_api_client.get_top_headlines(category='general', language='en', country='us')

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
response = open_ai_client.embeddings.create(input=article, model="text-embedding-3-small")
results = index.query(vector=response.data[0].embedding, top_k=10)

for match in results.matches:
    print(match.id)

# Pass similar articles to Claude, get most intriguing, generate lesson about topic

#message = anthropic_client.messages.create(
#  model="claude-opus-4-8",
#  max_tokens=1024,
#  messages=[{
#    "role": "user",
#    "content": ""
#  }]
#)