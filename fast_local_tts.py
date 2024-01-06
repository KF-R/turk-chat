import io, wave
from balacoon_tts import TTS
import numpy as np
from pydub import AudioSegment
from huggingface_hub import hf_hub_download

MODEL = 'en_us_hifi92_light_cpu.addon'
model_path = hf_hub_download(repo_id="balacoon/tts", filename=MODEL)

tts = TTS(model_path)
supported_speakers = tts.get_speakers()
speaker = supported_speakers[-1]

def text_to_mp3(text: str, tts_filename: str = 'fltts_result') -> None:
    if not text.strip(): return

    samples = tts.synthesize(text, speaker)

    # Convert the numpy array to bytes
    raw_audio_data = samples.tobytes()

    # Create an AudioSegment instance from the raw audio data
    audio_segment = AudioSegment(
        data=raw_audio_data,
        sample_width=2,  # 2 bytes as it's 16-bit audio
        frame_rate=tts.get_sampling_rate(),
        channels=1
    )

    buffer = io.BytesIO()
    audio_segment.export(buffer, format="mp3")

    with open(tts_filename + '.mp3', "wb") as f:
        f.write(buffer.getvalue())

if __name__ == '__main__':
    text_to_mp3("In the quiet moonlight, a gentle breeze rustles through the leaves, whispering secrets of the ancient forest. The air is crisp and fresh, filled with the subtle scent of pine and earth. Somewhere in the distance, an owl hoots solemnly, its call echoing through the trees. Each sound, from the rustling leaves to the soft footfalls on the forest floor, creates a symphony of natural tranquility, inviting a moment of serene reflection.")
