from openai import OpenAI
from config import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

response = client.responses.create(
    model="gpt-4.1",
    tools=[{
        "type": "web_search_preview",
        "search_context_size": "low",
    }],
    input="What movie won best picture in 2025?",
    stream=True,
)

for event in response:
   if event.type == "response.output_text.delta":
      print(event.delta, end="", flush=True)