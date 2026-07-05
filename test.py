from config import open_ai_client, anthropic_client, news_api_client, index
from keywords import words
from agents import pipeline
import re

top_headlines = news_api_client.get_top_headlines(category='general', language='en', country='us')

filtered_headlines = []
for item in top_headlines["articles"]:
    for word in words:
        if re.search(r'\b' + word + r'\b', item["title"].lower()):
            filtered_headlines.append(item["title"])
            break

for i in range(len(filtered_headlines)):
    print(f'Index: {i}, Title: {filtered_headlines[i]}')

# User input to select article
idx = int(input("Select index: "))
article = filtered_headlines[idx]

output = pipeline(article)

print(output)
