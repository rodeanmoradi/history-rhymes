from config import anthropic_client, open_ai_client, index
from prompts import get_search_prompt, get_eval_prompt

def search(article, description):
    response = anthropic_client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": get_search_prompt(article, description),
        }],
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}]
    )

    return response

def query(article, description):
    if description is None:
        response = open_ai_client.embeddings.create(input=article, model="text-embedding-3-small")
        result = index.query(vector=response.data[0].embedding, top_k=5, include_metadata=True)
    else:
        response = open_ai_client.embeddings.create(input=description, model="text-embedding-3-small")
        result = index.query(vector=response.data[0].embedding, top_k=5, include_metadata=True)

    return result

def search_eval(conversation_history):
    response = anthropic_client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        messages=conversation_history,
        tools=[{
            "name": "query",
            "description": "",
            "input_schema": {
                "type": "object",
                "properties": {
                    "article": {
                        "type": "string",
                        "description": "The title of the article selected by the user"
                    },
                    "description": {
                        "type": "string",
                        "description": "A very brief (up to ten words) description of the article's themes/concepts"
                    }
                }
            }
        },
        {
            "name": "web_search",
            "description": "",
            "input_schema": {
                "type": "object",
                "properties": {
                    "article": {
                        "type": "string",
                        "description": "The title of the article selected by the user"
                    },
                    "description": {
                        "type": "string",
                        "description": "A description (up to 25 words) of the deeper themes and concepts relevant to the article"
                    }
                }
            }  
        }]
    )

    return response

def get_tool():
    tools = {
        "web_search": search,
        "query": query
    }

    return tools

def pipeline(article):
    count = 0
    topic = None
    conversation_history = []
    while topic is None and count < 4:
        if count == 0:
            search_result = search(article, None)
            query_result = query(article, None)
            conversation_history = [{
                "role": "user",
                "content": get_eval_prompt(search_result, query_result),
            }]
            eval_response = search_eval(conversation_history)
            count += 1
        
        else:
            eval_response = search_eval(conversation_history)
            count += 1

        if eval_response.stop_reason == "tool_use":
            tool_results = []
            for item in eval_response.content:
                if item.type == "tool_use":
                    tools_dict = get_tool()
                    tool = tools_dict[item.name]
                    article = item.input["article"]
                    description = item.input["description"]
                    if item.name == "web_search":
                        search_result = tool(article, description)
                        tool_results.extend([{"type": "tool_result", "tool_use_id": f"{item.id}", "content": {"type": "text", "text": f"{search_result}"}}])
                    else: # query
                        query_result = tool(article, description)
                        tool_results.extend([{"type": "tool_result", "tool_use_id": f"{item.id}", "content": {"type": "text", "text": f"{query_result}"}}])
            conversation_history.extend(
                [
                    {"role": "assistant", "content": eval_response.content},
                    {"role": "user", "content": tool_results},  # All results in one message
                ]
            )
        else:
            topic = eval_response
    
    return eval_response