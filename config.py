from dotenv import load_dotenv
from openai import OpenAI
from newsapi import NewsApiClient
from pinecone import Pinecone
import anthropic
import os
import tiktoken

# TODO: def init_clients() and other improvements
load_dotenv()
open_ai_client = OpenAI()
anthropic_client = anthropic.Anthropic()
news_api_client = NewsApiClient(api_key=os.getenv("NEWSAPI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(host=os.getenv("PINECONE_HOST"))
enc = tiktoken.encoding_for_model("text-embedding-3-small")