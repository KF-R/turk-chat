from faster_whisper import WhisperModel

# model_size = "large-v3"
# model_size = "medium.en"
model_size = "small.en" 
# model_size = "tiny.en" 

# Running on CPU with INT8
model = WhisperModel(model_size, device="cpu", compute_type="int8")

def fast_transcribe(filename):
    segments, info = model.transcribe(filename, beam_size=5)

    transcription = ""

    for segment in segments:
        transcription += segment.text.strip()
        # transcription += f"\"{segment.text.strip()}\" ({(segment.no_speech_prob * 100):.2f}% chance of no speech)"
        # transcription += ("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))

    # TODO: return average probability over all segments rather than last one 
    return transcription, segment.no_speech_prob

if __name__ == '__main__':
    name = input('Go\n')
    transcribed_result = fast_transcribe('test.wav')[0]
    print('\n' + transcribed_result)

