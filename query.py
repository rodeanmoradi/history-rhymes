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

# Embed and query TODO: EVAL
response = open_ai_client.embeddings.create(input=article, model="text-embedding-3-small")
results = index.query(vector=response.data[0].embedding, top_k=5)

# Pass similar articles to Claude, get most intriguing, generate lesson about topic
prompt = f"""You are a highly knowledgeable historian, journalist, and educator. Pick the article from the following list that 
    provides the most intriguing, perhaps unobvious, and intellectually rewarding historical parallel to the selected news headline. 
    Once you have done so, you must generate a lesson regarding this article's topic using your research. This lesson should be 
    written in a format that is engaging and keeps the reader entertained. It should not take more than one minute to read through. 
    Articles: {results.matches[0].id}, {results.matches[1].id}, {results.matches[2].id}, {results.matches[3].id}, 
    {results.matches[4].id}, Selected Headline: {article}"""
message = anthropic_client.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": prompt
    }]
)

print(message.content[0].text)