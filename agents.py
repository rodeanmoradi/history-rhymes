from config import anthropic_client
from prompts import get_search_prompt, get_eval_prompt

def search(article):
    search_response = anthropic_client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": get_search_prompt(article),
            }
        ],
        tools=[{"type": "web_search_20260209", "name": "web_search"}],
    )

    search_result = search_response.content[0].text

    return search_result

def eval_search(search_result, results):
    eval_response = anthropic_client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": get_eval_prompt(search_result, results),
            }
        ]
    )

    eval_result = eval_response.content[0].text

    return eval_result

    