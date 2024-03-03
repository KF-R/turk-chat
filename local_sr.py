from faster_whisper import WhisperModel

# model_size = "large-v3"
# model_size = "medium.en"
# model_size = "small.en" 
# model_size = "tiny.en" 

# model_size = "distil-large-v2"
model_size = "distil-medium.en"

# Running on CPU with INT8
model = WhisperModel(model_size, device="cpu", compute_type="int8")

def fast_transcribe(filename):
    segments, info = model.transcribe(filename, beam_size=5, vad_filter=True)

    transcription = ""
    no_speech_prob = 0
    segment_count = 0

    for segment in segments:
        transcription += segment.text.strip()
        no_speech_prob += segment.no_speech_prob
        segment_count += 1
        # transcription += f"\"{segment.text.strip()}\" ({(segment.no_speech_prob * 100):.2f}% chance of no speech)"
        # transcription += ("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))

    # Average probability that transcription engine identified no speech across all segments:
    if segment_count > 0:
        no_speech_prob = no_speech_prob / segment_count 
    else: no_speech_prob = 1

    return transcription, no_speech_prob

if __name__ == '__main__':
    name = input('Go\n')
    transcribed_result = fast_transcribe('test.wav')[0]
    print('\n' + transcribed_result)

