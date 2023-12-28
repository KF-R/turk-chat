## turk-chat conversation agent

As written, it expects `my_env.py` in your home directory; its contents defining API keys as follows:
```
API_KEY_OPENAI = '<insert_your_OpenAI_API_key_here>'
API_KEY_ELEVENLABS = '<insert_your_ElevenLabs_API_key_here>'
```

`turk_flask.py` is a Python Flask application.  It'll launch a web hosting service at port 5000.
Visit `https://127.0.0.1:5000/` after launching and grant the browser microphone permission as necessary.

