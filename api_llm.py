import sys,os
sys.path.append(os.path.expanduser('~'))
from my_env import API_KEY_OPENAI, API_KEY_GROQ

from openai import OpenAI

SYSTEM_PROMPT = \
f"You are a charismatic and personal, albeit efficient and professional, personal assistant. " \
"You occasionally allow your sharp, sardonic sense of humor to enliven your responses. " \
"You have recently been upgraded to a \"droid\" with full speech capabilities (both recognition and generation). " \
"Your text responses will be read aloud to the user by an integrated TTS engine and your input prompts come to you by way of a speech recognition system, so be alert for any non-sequiturs, inconsistencies, errors or other discrepancies that may occasionally occur with speech recognition.\n\n"

MODELS = [
    {
        'label': 'GPT4',
        'provider': 'OpenAI',
        'model_name': 'gpt-4-1106-preview',
        'endpoint': 'https://api.openai.com/v1',
        'prompt_token_cost': 0.01 / 1000,   # USD
        'response_token_cost': 0.03 / 1000, # USD
        'token_limit': 128000,
        'request_fee': 0
    },
    {
        'label': 'GPT3.5',
        'provider': 'OpenAI',
        'model_name': 'gpt-3.5-turbo-1106',
        'endpoint': 'https://api.openai.com/v1',
        'prompt_token_cost': 0.01 / 1000,   # USD
        'response_token_cost': 0.02 / 1000, # USD
        'token_limit': 16000,
        'request_fee': 0
    },
    {
        'label': 'Groq-Mixtral',
        'provider': 'Groq',
        'model_name': 'mixtral-8x7b-32768',
        'endpoint': 'https://api.groq.com/openai/v1',
        'prompt_token_cost': 0.27 / 1000 / 1000,   # USD
        'response_token_cost': 0.27 / 1000 / 1000, # USD
        'token_limit': 32768,
        'request_fee': 0
    },
    {
        'label': 'Perplexity-M',
        'provider': 'Pplx',
        'model_name': 'sonar-medium-online',
        'endpoint': 'https://api.perplexity.ai',
        'prompt_token_cost': 0.00,              # USD
        'response_token_cost': 5.00 / 1000,     # USD
        'token_limit': 12000,
        'request_fee': 1.80 / 1000 / 1000       # USD
    },   
    {
        'label': 'TinyDolphin',
        'provider': 'Ollama',
        'model_name': 'tinydolphin',
        'endpoint': 'http://localhost:11434/api/chat',
        'prompt_token_cost': 0,
        'response_token_cost': 0,
        'token_limit': 12000,
        'request_fee': 0
    },
        {
        'label': 'Gemma',
        'provider': 'Ollama',
        'model_name': 'gemma',
        'endpoint': 'http://localhost:11434/api/chat',
        'prompt_token_cost': 0,
        'response_token_cost': 0,
        'token_limit': 12000,
        'request_fee': 0
    }
]

def get_model_index(label):
    return next((i for i, d in enumerate(MODELS) if d.get('label') == label), None)

def request_response_openai(model_name: str, messages, endpoint: str = 'https://api.openai.com/v1'):
    # Groq, Perplexity and Ollama now all support the OpenAI completion standard

    if 'groq.com' in endpoint: 
        api_key = API_KEY_GROQ
    elif 'perplexity.ai' in endpoint:
        api_key = API_KEY_PERPLEXITY
    elif 'openai.com' in endpoint:
        api_key = API_KEY_OPENAI
    else: api_key = 'no_key_supplied'

    openai_client = OpenAI(api_key=api_key, base_url = endpoint)
    response_object = openai_client.chat.completions.create(model = model_name, messages=messages)
    response_text = response_object.choices[0].message.content
    prompt_tokens, response_tokens, total_tokens = response_object.usage.prompt_tokens, response_object.usage.completion_tokens, response_object.usage.total_tokens

    return response_text, prompt_tokens, response_tokens, total_tokens

# def request_response_groq(model_name: str, messages, endpoint: str = 'https://api.groq.com/openai/v1/chat/completions'):
#     client = Groq(api_key = API_KEY_GROQ)
#     response = client.chat.completions.create(
#         model="mixtral-8x7b-32768",
#         messages=messages,
#         temperature=0.5,
#         max_tokens=1024,
#         top_p=1,
#         stream=False,
#         stop=None,
#     )    
#     return response.choices[0].message.content
