import io
import logging

logger = logging.getLogger(__name__)

_text_gen = None
_tts = None

def text_generate(prompt: str, model_name: str = 'gpt2', max_new_tokens: int = 128):
    """Generate text from a prompt using Hugging Face pipelines (lazy import).

    Returns generated text on success or raises ImportError if transformers not installed.
    """
    global _text_gen
    try:
        from transformers import pipeline
    except Exception as e:
        logger.exception('transformers not available')
        raise ImportError('transformers package is required for text generation') from e

    if _text_gen is None:
        _text_gen = pipeline('text-generation', model=model_name)
    out = _text_gen(prompt, max_new_tokens=max_new_tokens, do_sample=True, top_p=0.95)
    return out[0].get('generated_text')


def synthesize_speech(text: str, tts_model: str = 'tts_models/en/ljspeech/tacotron2-DDC'):
    """Synthesize speech using Coqui TTS (lazy import).

    Returns raw WAV bytes. Raises ImportError if TTS not available.
    """
    global _tts
    try:
        from TTS.api import TTS
        import soundfile as sf
        import numpy as np
    except Exception as e:
        logger.exception('TTS dependencies not available')
        raise ImportError('Coqui TTS and soundfile packages are required for TTS') from e

    if _tts is None:
        _tts = TTS(tts_model)

    # TTS.tts returns a numpy array of audio samples
    wav = _tts.tts(text)
    sample_rate = _tts.synthesizer.output_sample_rate if hasattr(_tts, 'synthesizer') else 22050

    buf = io.BytesIO()
    sf.write(buf, wav.astype(np.float32), sample_rate, format='WAV')
    buf.seek(0)
    return buf.read()
# models/tts_and_text.py
import io
import soundfile as sf
from transformers import pipeline
from TTS.api import TTS

# text generation (small example)
_text_gen = None
def text_generate(prompt, model_name="gpt2"):
    global _text_gen
    if _text_gen is None:
        _text_gen = pipeline("text-generation", model=model_name)
    out = _text_gen(prompt, max_new_tokens=128, do_sample=True, top_p=0.95)
    return out[0]['generated_text']

# TTS using Coqui TTS (will download prebuilt model on first run)
_tts = None
def synthesize_speech(text, tts_model="tts_models/en/ljspeech/tacotron2-DDC"):
    global _tts
    if _tts is None:
        _tts = TTS(tts_model)  # choose a model id from Coqui
    wav = _tts.tts(text)
    # return raw bytes (WAV)
    buf = io.BytesIO()
    sf.write(buf, wav, _tts.synthesizer.output_sample_rate, format='WAV')
    return buf.getvalue()