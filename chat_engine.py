# turk-chat Chat Engine
# Speech recognition engine using ring buffer, level detection and Whisper
# Chat reponses are prepared by OpenAI API and converted to ElevenLabs TTS MP3 files.
# (C) 2023 Kerry Fraser-Robinson

import sounddevice
import pyaudio
import wave
import numpy as np
import time
from openai import OpenAI
import whisper, json
import sys, os
sys.path.append(os.path.expanduser('~'))
from my_env import API_KEY_OPENAI, API_KEY_ELEVENLABS
from elevenlabs import generate, set_api_key, save
import requests
import string           # Test for empty strings from user
import random           # Select a voice if not specified
import shutil           # File operations (moving to archive)
import glob             # File operations (check if any mp3's exist)
import signal

from turk_lib import print_log, convert_complete_number_string

# TTS setup
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/voices"
ELEVENLABS_HEADERS = {"xi-api-key": API_KEY_ELEVENLABS}
ELEVENLABS_VOICE_LIST = json.loads(requests.request("GET", ELEVENLABS_API_URL, headers=ELEVENLABS_HEADERS).text)['voices']
chosen_voice = None
set_api_key(API_KEY_ELEVENLABS)
SELECTED_VOICE_NAME = 'joanne'

# Constants for microphone setup
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 48000
CHUNK = 2048
DEVICE_INDEX = 8
SPEECH_END_DELAY = 2    # Delay in seconds
# THRESHOLD = 1200        # Audio detection
THRESHOLD = 900

LISTENING = True
RECORD_STARTUP_LATENCY = 4 # How much of the ring buffer to use from before speech was detected (avoids clipping at the beginning)
RECORDED_AUDIO_ARCHIVE = 'audio_in/'

# Whisper API transcription setup
LOCAL_SR = True
LOCAL_WHISPER_MODEL_NAME = 'base.en' # tiny.en,base.en,small.en,medium.en,large
local_whisper = whisper.load_model(LOCAL_WHISPER_MODEL_NAME)

WHISPER_API_MODEL_NAME = 'whisper-1'

# Non-whisper OpenAI API setup
OPENAI_MODEL_NAME = 'gpt-4-1106-preview' # gpt-4-1106-vision-preview
OPENAI_MAX_TOKENS = 128000
OPENAI_PROMPT_TOKEN_COST   = 0.01 / 1000 # USD
OPENAI_RESPONSE_TOKEN_COST = 0.03 / 1000 # USD
client = OpenAI(api_key=API_KEY_OPENAI)
DEFAULT_SYSTEM_PROMPT =  f"You are a sassy, wise-cracking and funny family assistant. You are known for your witty responses and your sharp, sardonic sense of humor. You have recently been upgraded to a \"droid\" with full speech capabilities (both recognition and generation).  Your text responses will be read aloud to the user by an integrated TTS engine and your input prompts come to you by way of a speech recognition system, so be alert for any non-sequiturs, inconsistencies, errors or other discrepancies that may occasionally occur with speech recognition.\n"

messages=[{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
response = ''
SANDBOX_DIR = 'sandbox/'

print_log('Initialising Chat Engine...')

# Initialize PyAudio
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    dev = p.get_device_info_by_index(i)
    DEVICE_INDEX = i
    if 'nano' in dev['name'].lower(): break # Found Nano
print_log(f"Device {DEVICE_INDEX}: {dev['name']}, Channels: {CHANNELS}/{dev['maxInputChannels']}")

# Open stream
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, input_device_index=DEVICE_INDEX, frames_per_buffer=CHUNK)

# Ring buffer setup
buffer_duration = 10  # Duration in seconds
buffer_size = int(RATE / CHUNK * buffer_duration)
ring_buffer = np.zeros((buffer_size, CHUNK * CHANNELS), dtype=np.int16)
write_index = 0
is_above_threshold = False
start_time = None
end_time = None

# Speech detection setup
SPEECH_END_COUNT = int(SPEECH_END_DELAY * RATE / CHUNK)  # Number of continuous below-threshold chunks to end speech
below_threshold_count = 0  # Counter for continuous below-threshold chunks

def extract_codeblocks(text):
    strings = []
    # replacement_template = 'snippet_{}.txt'  # template for numbered replacement strings
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
        # replacement_string = replacement_template.format(len(strings) - 1)
        replacement_string = f"see code block {len(strings)-1}"
        ## filename for snippet is cb_time.time()//60_ (len(strings) - 1)
        codeblock_filename = f"cb_{int(time.time()//60)}_{(len(strings)-1):02d}.txt"
        with open(os.path.join(SANDBOX_DIR,f"{codeblock_filename}"), 'w') as snippet:
            snippet.write(extracted_string)
        replaced_text = replaced_text[:start_index] + replacement_string + replaced_text[end_index + 3:]
        index = start_index + len(replacement_string)

    return strings, replaced_text

def message_filter(msg: str = ''):
    r = msg.replace('an AI language model, ','a droid ')
    codeblocks, cleaned_text = extract_codeblocks(r)
    # print_log(f"Count: {len(codeblocks)} \n\n {'*'*80} \n {cleaned_text}")
    if len(codeblocks)>0:
        r = cleaned_text + f"\n\nYou'll find the {len(codeblocks) if len(codeblocks) > 1 else ''} code block{'s' if len(codeblocks) > 1 else ''} that I've extracted in the sandbox."
    return r

# Shutdown signal handler
def signal_handler(sig, frame):
    """Handle signals and perform a graceful shutdown."""
    global LISTENING
    if sig == signal.SIGINT:
        print_log('CTRL-C pressed. Shutting down gracefully...')
    elif sig == signal.SIGTERM:
        print_log('SIGTERM received. Shutting down gracefully...')
    LISTENING = False

def is_loud(data):
    """Check if the audio chunk is above the threshold."""
    return np.mean(np.abs(data)) > THRESHOLD

def extract_audio(ring_buffer, start_index, end_index, buffer_size):
    """Extract audio from the ring buffer handling wrap-around."""
    if end_index >= start_index:
        return ring_buffer[start_index:end_index].flatten()
    else:
        # Handle wrap-around in the ring buffer
        part1 = ring_buffer[start_index:].flatten()
        part2 = ring_buffer[:end_index].flatten()
        return np.concatenate((part1, part2))

def write_message_log(filename):
    with open(filename, 'w') as json_file:
        json.dump(messages, json_file, indent=4)

def process_user_speech(filename):
    global transcript, messages, chosen_voice

    def empty_string(s):
        stripped = s.replace(chr(46),'').strip()
        return ( s == stripped.translate( (str.maketrans('', '', string.punctuation))) )

    # Obtain transcript of user speech
    if LOCAL_SR:
        transcript = local_whisper.transcribe(filename, language = 'en')
    else:
        audio_file = open(filename, "rb")
        transcript = client.audio.transcriptions.create(
            model=WHISPER_API_MODEL_NAME,
            file=audio_file,
            langague = 'en', 
            response_format="text" )

    # chance_of_false_positive = transcript['segments'][0]['no_speech_prob']

    # Obtain AI response to tanscribed user speech
    if not empty_string(transcript['text']):
        print_log(f"Heard: {transcript['text']}")
        messages.append({'role': 'user', 'content': transcript['text']})

        response_object = client.chat.completions.create(model = OPENAI_MODEL_NAME, messages=messages)
        response_text = response_object.choices[0].message.content
        messages.append({'role': 'assistant', 'content': response_text})

        prompt_tokens, response_tokens, total_tokens = response_object.usage.prompt_tokens, response_object.usage.completion_tokens, response_object.usage.total_tokens

        prompt_cost, response_cost = prompt_tokens * OPENAI_PROMPT_TOKEN_COST, response_tokens * OPENAI_RESPONSE_TOKEN_COST
        print_log(f"Response cost:  ${(prompt_cost):.4f} + ${(response_cost):.4f} = ${(prompt_cost + response_cost):.4f}")

        # Generate TTS conversion of AI response
        if not chosen_voice: 
            for voice in ELEVENLABS_VOICE_LIST:
                if SELECTED_VOICE_NAME.upper() in voice['name'].upper(): chosen_voice = voice
            
            if not chosen_voice: chosen_voice = random.choice(ELEVENLABS_VOICE_LIST)

        print_log(f"{chosen_voice['name'].capitalize()} responded with {response_tokens} tokens.")

        tts_audio = generate(
            text = convert_complete_number_string(message_filter(response_text)),
            voice = chosen_voice['name'],
            model = "eleven_turbo_v2"
            # model = "eleven_monolingual_v1",
            )
        
        save(tts_audio, filename.split('.')[0] + '.mp3')
        shutil.move(filename, RECORDED_AUDIO_ARCHIVE + filename)
        write_message_log(chosen_voice['name'].lower() + '.json')

def run_listen_loop():
    global ring_buffer, write_index, below_threshold_count, start_index, is_above_threshold, LISTENING
    print_log('Listening...')
    while LISTENING:
        # Read data from stream
        if glob.glob('*.mp3'): # Either told not to listen or there's a response (mp3) being read out right now
            # We're not actually listening right now; silence can go in the buffer
            audio_chunk = np.zeros(CHUNK * 2, dtype=np.int16)
        else:
            try:
                # Non-blocking read to avoid input overflow error
                audio_chunk = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
            except IOError as e:
                if e.errno != pyaudio.paInputOverflowed:
                    raise  # Reraising unexpected errors
                audio_chunk = np.zeros(CHUNK, dtype=np.int16)  # If overflow, replace with silence

        ring_buffer[write_index % buffer_size] = audio_chunk
        current_index = write_index % buffer_size
        write_index += 1

        # Check volume
        if is_loud(audio_chunk):
            if not is_above_threshold:
                print_log(f"Audio detected.")
                start_time = time.time()
                start_index = current_index
                is_above_threshold = True
            below_threshold_count = 0  # Reset the counter on loud audio
        else:
            if is_above_threshold:
                below_threshold_count += 1
                if below_threshold_count > SPEECH_END_COUNT:
                    end_index = current_index
                    is_above_threshold = False
                    end_time = time.time()
                    # Extract audio from ring buffer
                    audio_data = extract_audio(ring_buffer, start_index - RECORD_STARTUP_LATENCY, end_index, buffer_size)
                    # Write audio to file
                    filename = f"{int(start_time)}.wav"
                    wf = wave.open(filename, 'wb')
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(p.get_sample_size(FORMAT))
                    wf.setframerate(RATE)
                    wf.writeframes(audio_data.tobytes())
                    wf.close()
                    print_log(f"Audio written to {filename}")
                    process_user_speech(filename)
                    # Reset the start_index for new audio
                    start_index = current_index

    # Stop stream
    stream.stop_stream()
    stream.close()

    # Close PyAudio
    p.terminate()

    print_log('Shutdown complete.')

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    message_files = glob.glob('*.json')
    if message_files:
        try:
            with open(message_files[0], 'r') as file:
                messages = json.load(file)
        except json.JSONDecodeError:
            print_log("Error: The file does not contain valid JSON.")
        except FileNotFoundError:
            print_log(f"Error: The file '{message_files[0]}' was not found.")
        except Exception as e:
            print_log(f"Error: An unexpected error occurred: {e}")
        assistant_name = message_files[0].split('.')[0].capitalize()
        print_log(f"Assistant: {assistant_name}")
    run_listen_loop()
