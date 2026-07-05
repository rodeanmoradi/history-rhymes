from config import anthropic_client, open_ai_client, index
from prompts import get_search_prompt, get_eval_prompt

def search(article, description):
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": get_search_prompt(article, description),
        }],
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 3, "allowed_callers": ["direct"]}]
    )

    result = [block.text for block in response.content if block.type == "text"]

    return result

def query(article, description):
    if description is None:
        response = open_ai_client.embeddings.create(input=article, model="text-embedding-3-small")
        retrieval = index.query(vector=response.data[0].embedding, top_k=5, include_metadata=True)
    else:
        response = open_ai_client.embeddings.create(input=description, model="text-embedding-3-small")
        retrieval = index.query(vector=response.data[0].embedding, top_k=5, include_metadata=True)

    result = {item.id: item.metadata["abstract"] for item in retrieval.matches}

    return result

def search_eval(messages):
    # TODO: Make descriptions for tools
    tools = [{
        "name": "query",
        "description": """
            Searches a curated vector index of historical Wikipedia articles by semantic similarity. Provide a description phrased as 
            the themes and concepts you want matches for — the description is what gets embedded and searched, so abstract thematic 
            phrasing (e.g. "naval blockade forcing economic collapse") surfaces better parallels than literal headline text. Returns the 
            top 5 matching articles as titles with abstracts. Reuse it with a reformulated 
            description if earlier results were too literal or off-theme. Limited to what exists in the index.
        """,
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
            },
            "required": ["article", "description"]
        }
    },
    {
        "name": "web_search",
        "description": """
            Conducts open-ended live web research to find three historical parallels to the article, with short summaries of each. Slower 
            and more expensive than query. Returns the three candidate parallels as text.
        """,
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
            },
            "required": ["article", "description"]
        }  
    }]
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        messages=messages,
        tools=tools
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
    messages = []
    topic = None
    while topic is None and count < 3:
        if count == 0:
            search_result = search(article, None)
            query_result = query(article, None)
            messages = [{"role": "user", "content": get_eval_prompt(search_result, query_result),}]
            eval_response = search_eval(messages)
            count += 1
        
        else:
            eval_response = search_eval(messages)
            count += 1

        if eval_response.stop_reason == "tool_use":
            tool_results = []
            for block in eval_response.content:
                if block.type == "tool_use":
                    tools_dict = get_tool()
                    tool = tools_dict[block.name]
                    tool_article = block.input["article"]
                    description = block.input["description"]
                    result = tool(tool_article, description)
                    tool_results.extend([{"type": "tool_result", "tool_use_id": f"{block.id}", "content": [{"type": "text", "text": f"{result}"}]}])

            messages.extend(
                [{"role": "assistant", "content": eval_response.content},{"role": "user", "content": tool_results},])
        else:
            topic = eval_response.content[0].text

            return topic

    return "The pipeline failed to find a topic"