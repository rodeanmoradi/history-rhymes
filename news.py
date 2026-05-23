from newsapi import NewsApiClient
from dotenv import load_dotenv
import os

load_dotenv()

newsapi = NewsApiClient(api_key=os.getenv("NEWSAPI_API_KEY"))
top_headlines = newsapi.get_top_headlines(category='general', language='en', country='us')
print(top_headlines)