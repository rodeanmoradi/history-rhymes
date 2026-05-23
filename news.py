from newsapi import NewsApiClient
from dotenv import load_dotenv
import os

load_dotenv()

newsapi = NewsApiClient(api_key=os.getenv("NEWSAPI_API_KEY"))
top_headlines = newsapi.get_top_headlines(category='general', language='en', country='us')

for i in range(len(top_headlines["articles"])):
    print(f'Index: {i}, Title: {top_headlines["articles"][i]["title"]}')