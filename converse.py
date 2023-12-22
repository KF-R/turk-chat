# turk-chat Conversation Agent
# (C) 2023 Kerry Fraser-Robinson

VERSION = '0.4.1'
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import time, pygame, threading
from queue import Queue, Empty
import shutil       # File system operation (file movement)
import json, glob   # JSON and file system operation (message log)

PLAYED_AUDIO_ARCHIVE = 'audio_out/'
if not os.path.exists(PLAYED_AUDIO_ARCHIVE):  os.makedirs(PLAYED_AUDIO_ARCHIVE)
RECORDED_AUDIO_ARCHIVE = 'audio_in/'
if not os.path.exists(RECORDED_AUDIO_ARCHIVE):  os.makedirs(RECORDED_AUDIO_ARCHIVE)

import numpy as np  # Visualisation processing
import wave         # Visualisation processing
from pydub import AudioSegment # mp3 support for visualisation

import subprocess

RESOLUTIONS = [
    (160, 120),    # QQVGA
    (320, 240),    # QVGA
    (640, 480),    # VGA
    (800, 600),    # SVGA
    (960, 720),    # Apple QuickTake
    (1024, 768),   # XGA
    (1152, 864),   # XGA+
    (1280, 960),   # SXGA
    (1400, 1050),  # SXGA+
    (1440, 1080),  # HDV 1080i
    (1600, 1200),  # UXGA
    (1920, 1440),  # QXGA
    (2048, 1536),  # QXGA+
    (3200, 2400) ] # QSXGA 

WINDOW_RESOLUTION, MINIMUM_RESOLUTION = RESOLUTIONS[3], RESOLUTIONS[0]
MAXIMUM_RESOLUTION = RESOLUTIONS[-1]
# PYGAME_DISPLAY_FLAGS = pygame.NOFRAME | pygame.DOUBLEBUF | pygame.HWSURFACE
PYGAME_DISPLAY_FLAGS = pygame.DOUBLEBUF | pygame.HWSURFACE
LIBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib') 
FPS = 90

# Prepare the font(s)
FONT_PATH = os.path.join(LIBDIR,"Code New Roman.otf")
font_cache = {}
MESSAGE_FONT_SIZE = 20
WORD_WRAP_LIMIT = 72
MESSAGE_TAIL_COUNT = 5

# Define the list of colour RGB tuples
COLOURS = [
    (0, 0, 0),          # Black
    (0, 0, 0xFF),       # Blue
    (0xFF, 0, 0),       # Red
    (0, 0xFF, 0xFF),    # Cyan
    (0, 0xFF, 0),       # Green
    (0xFF, 0, 0xFF),    # Magenta
    (0xFF, 0xFF, 0),    # Yellow
    (0xFF, 0xFF, 0xFF), # White 
    (0x32, 0x32, 0x32), # Dark grey
    (0x7F, 0x7F, 0x7F)] # Grey
BLACK, BLUE, RED, CYAN, GREEN, MAGENTA, YELLOW, WHITE, DARK_GREY, GREY = list(COLOURS)
STATUS_IMAGES = []
for status_image_name in ['working', 'listening', 'hearing', 'talking']: STATUS_IMAGES.append(pygame.image.load(f"{LIBDIR}/status_{status_image_name}.png"))
SIMG_WORKING, SIMG_LISTENING, SIMG_HEARING, SIMG_TALKING = list(STATUS_IMAGES)
PANEL_WIDTH, PANEL_HEIGHT = 240, 120
PANEL_POSITION = (WINDOW_RESOLUTION[0] // 2) - (PANEL_WIDTH // 2), WINDOW_RESOLUTION[1] - PANEL_HEIGHT - 64
PANEL_BG, PANEL_FG = BLACK, YELLOW

# Initialise Pygame
try:
    RESCALE_RESOLUTION = (int(sys.argv[1]), (int(sys.argv[1]) // 4) * 3)
    if RESCALE_RESOLUTION[0] < MINIMUM_RESOLUTION[0]: RESCALE_RESOLUTION = MINIMUM_RESOLUTION
except: RESCALE_RESOLUTION = WINDOW_RESOLUTION

pygame.init()
window = pygame.display.set_mode(WINDOW_RESOLUTION, PYGAME_DISPLAY_FLAGS)
pygame.display.set_caption("Conversation Agent")
clock = pygame.time.Clock()
fps = 0
font = pygame.font.Font(None, 36)
original_surface = pygame.Surface(RESCALE_RESOLUTION)

amplitude = 0
previously_played = None
messages = []
assistant_name = 'assistant'
text_scroll_offset = 0

CHAT_LOG = 'chat_engine.log'
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
try:
    previous_log_mtime = os.path.getmtime(CHAT_LOG)
except:
    now = time.localtime()
    month_name = MONTHS[now.tm_mon - 1]  # tm_mon ranges from 1 to 12
    with open(CHAT_LOG, 'w') as file:
        file.write(f"New session at {now.tm_year}-{month_name}-{now.tm_mday:02d}:{now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d}")
    previous_log_mtime = time.time()

LISTENING_CONFIRMED = False

# Task queue
task_queue = Queue()

# Flag to indicate if the application is running
is_running = True

def run_in_thread(target_func, args=(), callback=None):
    """ Runs a task in a separate thread """

    def thread_target():
        if not is_running:
            return  # Exit early if the application is no longer running
        result = target_func(*args)
        if callback and is_running:
            pygame.event.post(pygame.event.Event(pygame.USEREVENT, {'callback': callback, 'result': result}))

    threading.Thread(target=thread_target).start()

def enqueue_task(task, args=(), callback=None):
    task_queue.put((task, args, callback))

def process_tasks():
    try:
        task, args, callback = task_queue.get_nowait()
        run_in_thread(task, args, callback)
    except Empty:
        pass

def on_task_complete(result):
    """ Callback function for when the task is complete """
    global status_line
    status_line = result

def notice(notice_type: str = 'STATUS', content: str = ''): print(f"[{datetime.datetime.now().strftime('%b-%d %H:%M')}] {notice_type}:  {content}")

def print_at(canvas, text_x: int, text_y: int, text_string: str, font_size: int = 16, fg_colour: tuple = (0, 0, 0), bg_colour: tuple = (255, 255, 255), padding: int = 4, padding_colour: tuple = (255, 255, 255)):
    global font_cache  # The font cache ensures fonts are read from storage once only
    font_key = (FONT_PATH, font_size)
    font_cache.setdefault(font_key, pygame.font.Font(FONT_PATH, font_size))
    font = font_cache[font_key]

    lines = text_string.split('\n')
    for i, line in enumerate(lines):
        text = font.render(str(line), True, fg_colour, bg_colour)
        text_rect = text.get_rect()
        text_rect.topleft = (text_x, text_y + i * (font_size + padding))

        if padding: 
            pygame.draw.rect(canvas, padding_colour, pygame.Rect(text_rect.topleft[0] - padding, text_rect.topleft[1] - padding, text_rect.width + (padding * 2), text_rect.height + (padding * 2)))

        canvas.blit(text, text_rect)

    return text_rect # return box coordinates

def display_image(canvas, image, x, y, rescale_factor: float = 1.0):
    if rescale_factor != 1.0:
        scaled_width = int(image.get_width() * rescale_factor)
        scaled_height = int(image.get_height() * rescale_factor)
        image = pygame.transform.scale(image, (scaled_width, scaled_height))
    canvas.blit(image, image.get_rect().move(x, y))

def play_sound_with_visualization(filename):
    global original_surface, status_line, amplitude
    
    # Determine if the file is WAV or MP3
    file_extension = os.path.splitext(filename)[1].lower()
    
    # Load the audio file differently based on its format
    if file_extension == '.mp3':
        audio = AudioSegment.from_mp3(filename)
        audio = audio.set_channels(1)
        wav_data = audio.raw_data
        frame_rate = audio.frame_rate
        n_channels = audio.channels
        n_frames = len(audio)
    elif file_extension == '.wav':
        wav = wave.open(filename, 'rb')
        n_frames = wav.getnframes()
        frame_rate = wav.getframerate()
        n_channels = wav.getnchannels()
        wav_data = wav.readframes(n_frames)
        wav.close()
    else:
        return "Unsupported file format"

    # Start the mixer and play the file
    pygame.mixer.init()
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()

    # Process audio data for visualization
    wav_array = np.frombuffer(wav_data, dtype=np.int16)
    wav_array = wav_array.reshape(-1, n_channels)
    wav_array = wav_array[:, 0]  # Use first channel for visualization
    wav_array = np.interp(wav_array, (wav_array.min(), wav_array.max()), (20, 220))

    # Visualization loop
    while pygame.mixer.music.get_busy():
        play_time = pygame.mixer.music.get_pos() / 1000
        current_frame =  int(play_time * frame_rate)
        try:
            amplitude = min(30, int(wav_array[current_frame] - 120)) * 3
        except:
            break

    amplitude = 0
    return (filename)

def playback_complete(filename):
    global status_line
    if filename:
        shutil.move(filename, PLAYED_AUDIO_ARCHIVE + filename)
        completion_timestamp = time.time()
        total_time_taken = completion_timestamp - int(filename.split('.')[0])
        status_line = f"Response time: {total_time_taken:.6f} seconds. "
    
def calculate_gradient(start_colour, end_colour, step, total_steps):
    """
    Calculate the colour at a specific step in a gradient between two colours.
    """
    r = start_colour[0] + (end_colour[0] - start_colour[0]) * step / total_steps
    g = start_colour[1] + (end_colour[1] - start_colour[1]) * step / total_steps
    b = start_colour[2] + (end_colour[2] - start_colour[2]) * step / total_steps
    return (int(r), int(g), int(b))

def draw_gradient_circle(surface, start_colour, end_colour, center, radius, *args, **kwargs):
    """
    Draw a circle with a gradient fill.
    """
    for i in range(radius, 0, -1):
        colour = calculate_gradient(start_colour, end_colour, radius - i, radius)
        pygame.draw.circle(surface, colour, center, i, *args, **kwargs)

def render():
    global window
    if(RESCALE_RESOLUTION != WINDOW_RESOLUTION): 
        rescaled_surface = pygame.transform.smoothscale(original_surface, RESCALE_RESOLUTION)
    else: rescaled_surface = original_surface

    # Blit the rescaled surface onto the window
    window.blit(rescaled_surface, (0, 0))

    # Update the display
    pygame.display.flip()

def get_latest_audio_file(directory = os.path.dirname(os.path.abspath(__file__)), mp3_only: bool = True):
    # List all files in the directory
    files = os.listdir(directory)

    # Filter out files that are not .wav
    audio_files = [f for f in files if (f.endswith('.wav') and not mp3_only) or f.endswith('.mp3')]

    if not audio_files:
        return None  # No wav files found

    # Sort the files by creation time
    audio_files.sort(key=lambda f: os.path.getctime(os.path.join(directory, f)), reverse=True)

    # Return the most recently added file
    return audio_files[0]

def wrap_text(text: str, width: int = 40) -> str:
    """
    Format the given text to a specified width, breaking lines at preferred points,
    and handling long words with hyphenation if necessary, while preserving existing newlines.

    :param text: The text to be formatted.
    :param width: The desired width of each line.
    :return: Formatted text with line breaks.
    """
    lines = text.split('\n')  # Split the text into lines to preserve existing newlines
    formatted_text = ""

    for line in lines:
        words = line.split()
        current_line = ""
        
        for word in words:
            # Check if the current line plus the new word exceeds the width
            if len(current_line) + len(word) + 1 > width:
                # Handle long words that need to be hyphenated
                if len(word) > width + 2:
                    # Split the word
                    part1 = word[:width - len(current_line) - 1] + "-"
                    part2 = word[width - len(current_line) - 1:]
                    formatted_text += current_line + part1 + "\n"
                    current_line = part2 + " "
                else:
                    # Add the current line to the formatted text and start a new line
                    formatted_text += current_line.rstrip() + "\n"
                    current_line = word + " "
            else:
                current_line += word + " "
        
        # Add the last line of the current paragraph to the formatted text
        formatted_text += current_line.rstrip() + "\n"

    return formatted_text.rstrip()  # Remove any trailing newlines

def read_message_log(filename: str) -> str:
    """ Also updates `messages` global """
    global messages
    messages = []
    try:
        with open(filename, 'r') as file:
            message_log = json.load(file)
            
            for record in message_log:
                role = record.get('role')
                content = record.get('content', '')
                messages.append({'role': role, 'content': content})

    except json.JSONDecodeError:
        return "Error: The file does not contain valid JSON."
    except FileNotFoundError:
        return f"Error: The file '{filename}' was not found."
    except Exception as e:
        return f"Error: An unexpected error occurred: {e}"

    return "\n".join(f"{record['role']}: {record['content']}" for record in messages)

def bounding_rect(rect1, rect2):
    return pygame.Rect(min(rect1.left, rect2.left), min(rect1.top, rect2.top),
                       max(rect1.right, rect2.right) - min(rect1.left, rect2.left),
                       max(rect1.bottom, rect2.bottom) - min(rect1.top, rect2.top))

def display_message_tail(canvas, text_x: int, text_y: int, bg_colour: tuple = (255, 255, 255), padding: int = 4, padding_colour: tuple = (255, 255, 255)):
    # TODO: For performance, use a dedicated pygame surface to draw message box onto once and then blit the surface onto original_surface (cache)
    next_line_y = text_y
    for i, line in enumerate(messages[0-MESSAGE_TAIL_COUNT:]): # we only need to fetch the last n messages;
        # Role:
        if line['role'] == 'system':
            role_colour = RED
            role = 'SYSTEM: '
        elif line['role'] == 'assistant':
            role_colour = YELLOW
            role = assistant_name.capitalize() + ': '
        else: 
            role_colour = WHITE
            role = '>> '
        role_box = print_at(canvas, text_x, next_line_y, role, font_size=MESSAGE_FONT_SIZE, fg_colour=role_colour, bg_colour=bg_colour, padding=padding, padding_colour=padding_colour)

        # Content
        content_box = print_at(canvas, role_box.right, next_line_y, wrap_text(line['content'], WORD_WRAP_LIMIT - len(role)), font_size=MESSAGE_FONT_SIZE, fg_colour=GREY if line['role']=='user' else CYAN, bg_colour=bg_colour, padding=padding, padding_colour=padding_colour)
        next_line_y = content_box.bottom + padding

    return bounding_rect(role_box, content_box)

if __name__ == "__main__":

    # Launch chat engine
    chat_engine_process = subprocess.Popen(['python', 'chat_engine.py'])

    # Main loop
    running = True
    status_line = ''
    message_file = glob.glob('*.json')
    if message_file:
        message_log = read_message_log(message_file[0]) # Also refreshes `messages` global
        assistant_name = message_file[0].split('.')[0]

    while running:

        # Event handling including keypresses
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    break
                
                elif event.key == pygame.K_UP and RESCALE_RESOLUTION[0] < MAXIMUM_RESOLUTION[0]:
                    RESCALE_RESOLUTION = RESOLUTIONS[RESOLUTIONS.index(RESCALE_RESOLUTION) + 1]
                    window = pygame.display.set_mode(RESCALE_RESOLUTION, PYGAME_DISPLAY_FLAGS)

                elif event.key == pygame.K_DOWN and RESCALE_RESOLUTION[0] > MINIMUM_RESOLUTION[0]:
                    RESCALE_RESOLUTION = RESOLUTIONS[RESOLUTIONS.index(RESCALE_RESOLUTION) - 1]                    
                    window = pygame.display.set_mode(RESCALE_RESOLUTION, PYGAME_DISPLAY_FLAGS)

                elif event.key == pygame.K_SPACE:
                    status_line = 'Repeating...'
                    if previously_played: 
                        enqueue_task(play_sound_with_visualization, (PLAYED_AUDIO_ARCHIVE + previously_played,), playback_complete )
                    else: status_line = 'No speech prepared.'

            elif event.type == pygame.USEREVENT:
                if 'callback' in event.dict:
                    event.dict['callback'](event.dict['result'])

        original_surface.fill(DARK_GREY)
        fps = clock.get_fps()

        # Window elements:
        if status_line: print_at(original_surface, 8, WINDOW_RESOLUTION[1] - 8 - 28, f" {status_line} ", 28, YELLOW, GREY, 8, BLACK)
        
        if messages:
            message_box = display_message_tail(original_surface, 4, 4 - text_scroll_offset, DARK_GREY, 4, DARK_GREY)
            if message_box.bottom > PANEL_POSITION[1] - MESSAGE_FONT_SIZE:
                text_scroll_offset += 1

        try:
            if os.path.getmtime(CHAT_LOG) != previous_log_mtime:
                with open(CHAT_LOG, 'r') as file:
                    lines = file.readlines()
                    last_line = lines[-1].rstrip('\n') if lines else 'Empty log'
                    print(last_line)
                    previous_log_mtime = os.path.getmtime(CHAT_LOG)
                    if 'Listening...' in last_line: LISTENING_CONFIRMED = True
        except:
            # print("Can't find chat_engine.log.")
            pass

        # Show status icon
        corner_offset = SIMG_WORKING.get_width() + 50
        corner_offset = (280, 260)
        if LISTENING_CONFIRMED:
            if glob.glob('*.wav'):
                display_image(original_surface, SIMG_WORKING, WINDOW_RESOLUTION[0] - corner_offset[0], WINDOW_RESOLUTION[1] - corner_offset[1])
            elif glob.glob('*.mp3'):
                display_image(original_surface, SIMG_TALKING, WINDOW_RESOLUTION[0] - corner_offset[0], WINDOW_RESOLUTION[1] - corner_offset[1])
            elif 'Audio detected' in last_line:
                display_image(original_surface, SIMG_HEARING, WINDOW_RESOLUTION[0] - corner_offset[0], WINDOW_RESOLUTION[1] - corner_offset[1])
            else:
                display_image(original_surface, SIMG_LISTENING, WINDOW_RESOLUTION[0] - corner_offset[0], WINDOW_RESOLUTION[1] - corner_offset[1])
        

        # Update visualisation
        pygame.draw.rect(original_surface, BLACK, ((PANEL_POSITION[0], PANEL_POSITION[1]), (PANEL_WIDTH, PANEL_HEIGHT) ), 0)
        if amplitude > 0:
            # pygame.draw.circle(original_surface, RED, (PANEL_POSITION[0] + PANEL_WIDTH // 2, PANEL_POSITION[1] + PANEL_HEIGHT), amplitude, amplitude // 2, draw_top_left=True, draw_top_right=True, draw_bottom_left=False, draw_bottom_right=False)
            draw_gradient_circle(original_surface, RED, BLACK, (PANEL_POSITION[0] + PANEL_WIDTH // 2, PANEL_POSITION[1] + PANEL_HEIGHT), amplitude, amplitude // 2, draw_top_left=True, draw_top_right=True, draw_bottom_left=False, draw_bottom_right=False)

        # Render scaled frame
        print_at(original_surface, WINDOW_RESOLUTION[0] - 64, WINDOW_RESOLUTION[1] - 16, f" {fps:05.2f} ", 16, BLACK, GREY, 4, BLACK)
        render()

        # Process any pending tasks
        process_tasks()
        
        next_output_filename  = get_latest_audio_file()
        if next_output_filename and next_output_filename != previously_played:
            # print(f"Last recorded file: {next_output_filename}")
            previously_played = next_output_filename

            try:
                message_log = read_message_log(message_file[0]) # Refresh `messages`
            except:
                pass

            status_line = 'Talking'
            enqueue_task(play_sound_with_visualization, (next_output_filename,), playback_complete )

        clock.tick(FPS)

    # Try to terminate the subprocess gracefully
    chat_engine_process.terminate()

    try:
        # Wait for a specified timeout for the subprocess to exit
        chat_engine_process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        # If the process does not terminate in time, force kill it
        print("Subprocess did not terminate in time. Forcibly killing it.")
        chat_engine_process.kill()

    # Check the return code to determine how the process was terminated
    if chat_engine_process.returncode and chat_engine_process.returncode < 0:
        print("Chat engine was killed.")
    else:
        print("Chat engine terminated gracefully.")

    is_running = False
    pygame.quit()

    print('Shutdown complete.')