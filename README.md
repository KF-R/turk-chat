## turk-chat conversation agent
<sub>_If you're looking for the older async pygame version: https://github.com/KF-R/turk-chat-pygame_</sub>
<hr/>
<img src="https://github.com/KF-R/turk-chat/assets/6677966/986e1630-8c98-4249-a9cd-55e48cec148b" width="262px" align="right"/>

### Features:
* Ultra-lightweight; only a Python Flask server and vanilla JS.
* Integrated ring buffer, sound activity detection algorithm and real-time animated speech visualization.
* Automatic speech detection with termination detection; no push-to-talk or activation (listens, responds, listens... )
* Speech is recorded, transcribed by either the OpenAI Whisper API or CTranslate2-based fast Whisper:
  - https://github.com/SYSTRAN/faster-whisper
* Transcribed speech, along with full chat history, is submitted to OpenAI API for a chat response.
* Response is filtered for numbers, years, code blocks etc. in order to provide more naturalistic TTS.
* Filtered response is read via ElevenLabs Text-To-Speech API or fast local TTS engine using:
  - https://balacoon.com/freeware/tts/package
* Spoken response is visualized by way of a real-time waveform animation.
* After the spoken response is complete, listening is resumed in order to facilitate fluid on-going conversation.
* Integrated web access tools; **turk-chat** can grab current headlines, read wikipedia, summarise web pages etc.
* Toggle between basic and advanced LLM back ends (e.g. GPT-3.5 vs GPT-4)
* Obligatory Larsson scanner using KITT and Cylon modes for a bit of additional visual feedback.
* Simplified UI mode added (with KITT head-unit visualizer).

### Usage:
* Install requirements
* Set up API keys (See below and/or `my_env.py.example`)
* Launch `turk_flask.py`, which is a Python Flask application.  
* Visit localhost port 5000 in your browser (e.g. `https://127.0.0.1:5000/`)
* Approve the ad-hoc SSL certificate to authorise the page.
* Click the `Start Listening` button.  The first time you do this, you'll be asked to grant permissions to your microphone.
* Start talking.  Be patient with the response.
* After your chat agent has finished speaking its response, it will automatically resume listening.
* The `Voice` drop-down list is populated with the voice names from your ElevenLabs voice library.  
* You can change the responding voice without affecting the on-going conversation
* Use the `model` switch to toggle between basic (e.g. GPT-3.5) and advanced (e.g. GPT-4) models.
* To stop listening, click the `Stop Listening` button or refresh the page.
* To clear/archive the chat message and engine logs, click the `Reset` button. 
* Archived conversations will be stored in the `archive` directory.
* Code blocks generated by your chat partner will be stored in the `sandbox` directory.
* Previously recorded .wav files are kept in `audio_in`
* Previously generated .mp3 files are kept in `audio_out`
<hr/>

_**API keys:**_

As written, it expects `'my_env.py'` in your home directory; its contents defining API keys as follows:
  
```
API_KEY_OPENAI = '<insert_your_OpenAI_API_key_here>'
API_KEY_ELEVENLABS = '<insert_your_ElevenLabs_API_key_here>'
```


<p/>
<hr/>
v0.4.x <br/>

<img src="https://github.com/KF-R/turk-chat/assets/6677966/1896d8b8-7108-4cd2-a76b-edb28bdca90a" width="115px"/>

