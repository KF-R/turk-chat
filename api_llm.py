# Example code for Groq API
import sys,os
sys.path.append(os.path.expanduser('~'))
from groq import Groq
from my_env import API_KEY_OPENAI, API_KEY_ELEVENLABS, API_KEY_GROQ

system_message = 'You are a helpful assistant known for adding witty comments to every response.'
user_prompt = 'Can you explain calculus, please?'

client = Groq(api_key = API_KEY_GROQ)
completion = client.chat.completions.create(
    model="mixtral-8x7b-32768",
    messages=[
        {
            "role": "system",
            "content": f"{system_message}"
        },
        {
            "role": "user",
            "content": f"{user_prompt}"
        }
    ],
    temperature=0.5,
    max_tokens=1024,
    top_p=1,
    stream=True,
    stop=None,
)

for chunk in completion:
    print(chunk.choices[0].delta.content or "", end="")
