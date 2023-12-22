## turk-chat conversation agent

As written, it expects `my_env.py` in your home directory; its contents defining API keys as follows:
```
API_KEY_OPENAI = '<insert_your_OpenAI_API_key_here>'
API_KEY_ELEVENLABS = '<insert_your_ElevenLabs_API_key_here>'
```

Run `converse.py` to launch.

Requirements:
```
numpy
pygame
Requests
sounddevice
pydub
PyAudio
openai
openai whisper
elevenlabs
```

