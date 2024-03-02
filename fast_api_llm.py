# Example code for Groq API

from groq import Groq

client = Groq()
completion = client.chat.completions.create(
    model="mixtral-8x7b-32768",
    messages=[
        {
            "role": "system",
            "content": "{system_message}"
        },
        {
            "role": "user",
            "content": "{user_prompt}"
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
