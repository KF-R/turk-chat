from openai import OpenAI
from my_env import API_KEY_OPENAI
WHISPER_API_MODEL_NAME = 'whisper-1'  

whisper_client = OpenAI(api_key = API_KEY_OPENAI)

def api_transcribe(filename):
    audio_file = open(filename, "rb")
    transcript_text = str(whisper_client.audio.transcriptions.create(
        model=WHISPER_API_MODEL_NAME,
        file=audio_file,
        response_format="text" )).rstrip()
    return transcript_text, 0