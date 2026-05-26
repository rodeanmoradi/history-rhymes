from newsapi import NewsApiClient
from dotenv import load_dotenv
from keywords import words
import os

load_dotenv()

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

index = int(input("Select index: "))

article = filtered_headlines[index]

print(article)