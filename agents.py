from config import anthropic_client, open_ai_client, index
from prompts import get_search_prompt, get_eval_prompt

def search(article):
    response = anthropic_client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": get_search_prompt(article),
            }
        ],
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}],
    )

    search_result = response.content[0].text

    return search_result

def query(article):
    response = open_ai_client.embeddings.create(input=article, model="text-embedding-3-small")
    query_result = index.query(vector=response.data[0].embedding, top_k=5, include_metadata=True)

    return query_result

def eval_search(search_result, query_result):
    eval_response = anthropic_client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": get_eval_prompt(search_result, query_result),
            }
        ]
    )

    eval_result = eval_response.content[0].text

    return eval_result

def pipeline(article):
    # Exit when topic found
    while True:
        search_result = search(article)
        query_result = query(article)

        eval_result = eval_search(search_result, query_result)
            