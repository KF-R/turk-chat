VERSION = '0.5.2'
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS  # Import CORS
import json, requests, string, random
import shutil, glob, time
import sys, os
from werkzeug.utils import secure_filename

from openai import OpenAI
import whisper
sys.path.append(os.path.expanduser('~'))
from my_env import API_KEY_OPENAI, API_KEY_ELEVENLABS
from elevenlabs import generate, set_api_key, save

from turk_lib import print_log, convert_complete_number_string

# TTS setup
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/voices"
ELEVENLABS_HEADERS = {"xi-api-key": API_KEY_ELEVENLABS}
ELEVENLABS_VOICE_LIST = json.loads(requests.request("GET", ELEVENLABS_API_URL, headers=ELEVENLABS_HEADERS).text)['voices']
chosen_voice = None
set_api_key(API_KEY_ELEVENLABS)
SELECTED_VOICE_NAME = 'joanne'
DEFAULT_VOICE_NAME = 'joanne'

# Whisper transcription setup
LOCAL_SR = False
LOCAL_WHISPER_MODEL_NAME = 'base.en' # tiny.en,base.en,small.en,medium.en,large
local_whisper = whisper.load_model(LOCAL_WHISPER_MODEL_NAME)

WHISPER_API_MODEL_NAME = 'whisper-1'

# OpenAI API setup
OPENAI_MODEL_NAME = 'gpt-4-1106-preview' # gpt-4-1106-vision-preview
OPENAI_MAX_TOKENS = 128000
OPENAI_PROMPT_TOKEN_COST   = 0.01 / 1000 # USD
OPENAI_RESPONSE_TOKEN_COST = 0.03 / 1000 # USD
client = OpenAI(api_key=API_KEY_OPENAI)
DEFAULT_SYSTEM_PROMPT =  f"You are a sassy, wise-cracking and funny family assistant. You are known for your witty responses and your sharp, sardonic sense of humor. You have recently been upgraded to a \"droid\" with full speech capabilities (both recognition and generation).  Your text responses will be read aloud to the user by an integrated TTS engine and your input prompts come to you by way of a speech recognition system, so be alert for any non-sequiturs, inconsistencies, errors or other discrepancies that may occasionally occur with speech recognition.\n"

MESSAGE_LOG_FILENAME = 'messages.json'
ENGINE_LOG_FILENAME = os.path.splitext(os.path.basename(os.sys.argv[0]))[0] + '.log'

PLAYED_AUDIO_ARCHIVE = 'audio_out/'
if not os.path.exists(PLAYED_AUDIO_ARCHIVE):  os.makedirs(PLAYED_AUDIO_ARCHIVE)
RECORDED_AUDIO_ARCHIVE = 'audio_in/'
if not os.path.exists(RECORDED_AUDIO_ARCHIVE):  os.makedirs(RECORDED_AUDIO_ARCHIVE)
LOG_ARCHIVE = 'archive/'
if not os.path.exists(LOG_ARCHIVE):  os.makedirs(LOG_ARCHIVE)
SANDBOX_DIR = 'sandbox/'
if not os.path.exists(SANDBOX_DIR):  os.makedirs(SANDBOX_DIR)

messages=[]
response = ''

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def extract_codeblocks(text):
    strings = []
    replaced_text = text

    index = 0
    while True:
        start_index = replaced_text.find('```', index)
        if start_index == -1:
            break
        end_index = replaced_text.find('```', start_index + 3)
        if end_index == -1:
            break
        extracted_string = replaced_text[start_index + 3:end_index]
        strings.append(extracted_string)
        
        replacement_string = f"\n(See code-block number {(len(strings)):02d})\n"
        codeblock_filename = f"cb_{int(time.time()//60)}_{(len(strings)):02d}.txt"
        with open(os.path.join(SANDBOX_DIR,f"{codeblock_filename}"), 'w') as snippet:
            snippet.write(extracted_string)
        
        replaced_text = replaced_text[:start_index] + replacement_string + replaced_text[end_index + 3:]
        index = start_index + len(replacement_string)

    return strings, replaced_text

def message_filter(msg: str = ''):
    r = msg.replace('an AI language model, ','a droid ')
    codeblocks, cleaned_text = extract_codeblocks(r)
    if len(codeblocks)>0:
        r = cleaned_text + f"\n\nYou'll find the {len(codeblocks) if len(codeblocks) > 1 else ''} code block{'s' if len(codeblocks) > 1 else ''} that I've generated in the sandbox."
    r = r.replace('=',' equals ')
    return r

def read_message_log(filename):
    try:
        with open(filename, 'r') as json_file:
            print_log('Message history loaded.')
            return json.load(json_file)
    except:
        print_log('No message history; system prompt has been re-initialised.')
        return [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
        
def write_message_log(filename):
    with open(filename, 'w') as json_file:
        json.dump(messages, json_file, indent=4)

def process_user_speech(filename):
    global transcript, messages

    def empty_string(s):
        stripped = s.replace(chr(46),'').strip()
        return ( s == stripped.translate( (str.maketrans('', '', string.punctuation))) )

    # Obtain transcript of user speech
    if LOCAL_SR:
        transcript = local_whisper.transcribe(filename, language = 'en')
        transcript_text = transcript['text'].rstrip()
    else:
        audio_file = open(filename, "rb")
        transcript_text = str(client.audio.transcriptions.create(
            model=WHISPER_API_MODEL_NAME,
            file=audio_file,
            response_format="text" )).rstrip()

    # chance_of_false_positive = transcript['segments'][0]['no_speech_prob']

    # Obtain AI response to tanscribed user speech
    if not empty_string(transcript_text):
        print_log(f"Heard: {transcript_text}")
        messages.append({'role': 'user', 'content': transcript_text})

        response_object = client.chat.completions.create(model = OPENAI_MODEL_NAME, messages=messages)
        response_text = response_object.choices[0].message.content
        messages.append({'role': 'assistant', 'content': response_text})

        prompt_tokens, response_tokens, total_tokens = response_object.usage.prompt_tokens, response_object.usage.completion_tokens, response_object.usage.total_tokens

        prompt_cost, response_cost = prompt_tokens * OPENAI_PROMPT_TOKEN_COST, response_tokens * OPENAI_RESPONSE_TOKEN_COST
        response_cost = f"Response cost:  ${(prompt_cost):.4f} +  ${(response_cost):.4f} = ${(prompt_cost + response_cost):.4f}"
        token_level = f"Token level: {total_tokens:,} / {OPENAI_MAX_TOKENS:,}  ({( total_tokens / OPENAI_MAX_TOKENS * 100):.2f}%)"
        print_log(f"{token_level}  |  {response_cost}")

        # Generate TTS conversion of AI response
        for voice in ELEVENLABS_VOICE_LIST:
            if SELECTED_VOICE_NAME.upper() in voice['name'].upper(): chosen_voice = voice
            
        if not chosen_voice: chosen_voice = random.choice(ELEVENLABS_VOICE_LIST)

        print_log(f"{chosen_voice['name'].capitalize()} responded with {response_tokens} tokens.")

        tts_audio = generate(
            text = convert_complete_number_string(message_filter(response_text)),
            voice = chosen_voice['name'],
            model = "eleven_turbo_v2"
            )
        
        save(tts_audio, filename.split('.')[0] + '.mp3')
        shutil.move(filename, RECORDED_AUDIO_ARCHIVE + filename)
        write_message_log(MESSAGE_LOG_FILENAME)


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global SELECTED_VOICE_NAME
    print_log('Audio submission received.')
    if 'audio' in request.files:
        audio = request.files['audio']
        original_filename = audio.filename

        base_name, ext = os.path.splitext(original_filename)
        truncated_name = base_name[:10]  # Keep only the first 10 characters of the filename prefix

        safe_filename = f"{truncated_name}{ext}"
        
        audio.save(safe_filename)

        desired_voice_name = request.form.get('name')
        if desired_voice_name:
            for voice in ELEVENLABS_VOICE_LIST:
                if desired_voice_name.upper() in voice['name'].upper(): 
                    SELECTED_VOICE_NAME = voice['name']

        else: SELECTED_VOICE_NAME = DEFAULT_VOICE_NAME    

        process_user_speech(safe_filename)

        return jsonify({'message': f'Successfully saved {safe_filename}'}), 200
    else:
        return jsonify({'message': 'No audio file part'}), 400

# Route to accept any filename with .mp3 extension
@app.route('/<filename>.mp3')
def response_file(filename):
    try:
        secure_filename_str = secure_filename(f"{filename}.mp3")

        shutil.move(secure_filename_str, PLAYED_AUDIO_ARCHIVE + secure_filename_str)
        return send_from_directory(PLAYED_AUDIO_ARCHIVE, secure_filename_str)

    except FileNotFoundError:
        # Log an error message or return a custom 404 error
        return "File not found", 404

@app.route('/<filename>.json')
def message_log_file(filename):
    try:
        secure_filename_str = secure_filename(f"{filename}.json")
        return send_from_directory('.', secure_filename_str)
    except FileNotFoundError:
        # Log an error message or return a custom 404 error
        return "File not found", 404

@app.route('/<filename>.log')
def engine_log_file(filename):
    try:
        secure_filename_str = secure_filename(f"{filename}.log")
        return send_from_directory('.', secure_filename_str)
    except FileNotFoundError:
        # Log an error message or return a custom 404 error
        return "File not found", 404

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('.', 'favicon.ico', mimetype='image/x-icon')

@app.route('/reset')
def reset():
    global messages
    archiveTime = int(time.time())
    try:
        shutil.move(MESSAGE_LOG_FILENAME, LOG_ARCHIVE + f"{archiveTime}_{MESSAGE_LOG_FILENAME}")
        shutil.move(ENGINE_LOG_FILENAME, LOG_ARCHIVE + f"{archiveTime}_{ENGINE_LOG_FILENAME}")
        messages=[{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
        return redirect('/')
    except:
        return redirect('/?note=empty_logs')

@app.route('/voices')
def voice_list():
    return [d['name'] for d in ELEVENLABS_VOICE_LIST]

@app.route('/version')
def get_version():
    return f"v{VERSION}"

if __name__ == '__main__':
    print_log(f"v{VERSION}: Initialising...")
    messages = read_message_log(MESSAGE_LOG_FILENAME)
    app.run(debug=True, host='0.0.0.0', ssl_context='adhoc')

