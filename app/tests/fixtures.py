"""Synthetic fixtures: small audio files in every supported container, and a deterministic
embedding adapter that needs neither PyTorch nor weights. Tests built on these prove the
pipeline (scan, identity, waveform, worker protocol, stores, fusion, labels); they say
nothing about the quality of a real model, which is validated separately with real weights.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

APP = Path(__file__).resolve().parents[1]
RATE = 44100


def tone(frequency, seconds, rate=RATE, level=0.5):
    t = np.arange(int(seconds*rate))/rate
    return (level*np.sin(2*np.pi*frequency*t)).astype(np.float32)


def noise(seconds, rate=RATE, level=0.3, seed=1):
    return (level*np.random.default_rng(seed).standard_normal(int(seconds*rate))).astype(np.float32).clip(-1, 1)


def clicks(seconds, rate=RATE, every=0.25):
    audio = np.zeros(int(seconds*rate), np.float32)
    audio[::int(every*rate)] = 0.9
    return audio


def write_av(path, audio, rate, codec, container_format=None):
    import av
    with av.open(str(path), 'w', format=container_format) as container:
        stream = container.add_stream(codec, rate=rate)
        stream.layout = 'mono'
        frame_size = stream.codec_context.frame_size or 1024
        sample_format = stream.codec_context.format.name
        resampler = av.AudioResampler(format=sample_format, layout='mono', rate=rate)
        for begin in range(0, len(audio), frame_size):
            chunk = audio[begin:begin+frame_size]
            frame = av.AudioFrame.from_ndarray(chunk.reshape(1, -1), format='flt', layout='mono'); frame.sample_rate = rate; frame.pts = begin
            for out in resampler.resample(frame):
                for packet in stream.encode(out): container.mux(packet)
        for packet in stream.encode(None): container.mux(packet)


def build_library(folder):
    """Create a folder tree of known sounds; returns {relative path: kind}."""
    import soundfile
    folder = Path(folder); (folder/'Tones'/'Low').mkdir(parents=True, exist_ok=True); (folder/'Noise éàü').mkdir(exist_ok=True); (folder/'Long').mkdir(exist_ok=True)
    files = {}
    def save(relative, audio, rate=RATE, **options):
        soundfile.write(str(folder/relative), audio, rate, **options); files[relative] = True
    save('Tones/Low/low_tone_110.wav', tone(110, 1.5), subtype='PCM_16')
    save('Tones/Low/low_tone_90_24bit.wav', tone(90, 2.0), subtype='PCM_24')
    save('Tones/high_tone_4000.flac', tone(4000, 1.2), rate=48000)
    save('Tones/high_tone_5000_stereo.wav', np.stack([tone(5000, 1.0), tone(5200, 1.0)], axis=1), subtype='FLOAT')
    save('Noise éàü/white noise burst.ogg', noise(1.0))
    save('Noise éàü/clicks.aiff', clicks(2.0), subtype='PCM_16')
    save('Noise éàü/noise_copy_a.wav', noise(0.8, seed=5)); save('Noise éàü/noise_copy_b.wav', noise(0.8, seed=5))     # exact duplicates
    write_av(folder/'Tones/mid_tone_1000.mp3', tone(1000, 1.5), 44100, 'mp3'); files['Tones/mid_tone_1000.mp3'] = True
    write_av(folder/'Tones/mid_tone_800.m4a', tone(800, 1.5), 44100, 'aac'); files['Tones/mid_tone_800.m4a'] = True
    long = np.concatenate([tone(110, 14.0, level=0.3), noise(4.0, seed=9), tone(110, 14.0, level=0.3)])      # noise event at 14..18 s
    save('Long/long_recording_with_noise_at_14s.wav', long)
    (folder/'notes.txt').write_text('not audio', 'utf-8')
    return files


ADAPTER = '''
"""Deterministic test adapter: embeddings are hashed bags of words. Audio is described by simple
signal measures (dominant frequency, flatness, impulsiveness) mapped to the same words."""
import hashlib
import numpy as np
from adapters.base import BaseAdapter

DIM = %(dim)d
SALT = %(salt)r
DELAY = %(delay)r

def word_vector(word):
    seed = int.from_bytes(hashlib.sha256((SALT+word).encode()).digest()[:8], 'little')
    return np.random.default_rng(seed).standard_normal(DIM)

def words_of(wave, rate):
    spectrum = np.abs(np.fft.rfft(wave*np.hanning(len(wave))))+1e-9
    freqs = np.fft.rfftfreq(len(wave), 1/rate)
    flatness = np.exp(np.mean(np.log(spectrum)))/np.mean(spectrum)
    crest = np.abs(wave).max()/(np.sqrt(np.mean(wave**2))+1e-9)
    if flatness > 0.2: return ['noise'] + (['click'] if crest > 8 else [])
    if crest > 8: return ['click']
    peak = freqs[int(np.argmax(spectrum))]
    return ['tone', 'low' if peak < 300 else ('high' if peak > 2500 else 'mid')]

class Adapter(BaseAdapter):
    def load(self): self.rate = int(self.descriptor.get('requiredSampleRate') or 16000)
    def embed_audio(self, waves):
        import time; time.sleep(DELAY*len(waves))
        return np.stack([sum(word_vector(w) for w in words_of(np.asarray(wave, dtype=np.float64), self.rate)) for wave in waves])
    def embed_text(self, texts):
        out = []
        for text in texts:
            tokens = [t for t in ''.join(c if c.isalnum() else ' ' for c in text.lower()).split() if t in ('noise', 'click', 'tone', 'low', 'high', 'mid')]
            out.append(sum((word_vector(t) for t in tokens), np.zeros(DIM)) if tokens else word_vector('unknown'))
        return np.stack(out)
    def generate(self, messages, max_new_tokens=512):
        import json
        text = messages[-1]['content'].lower()
        return json.dumps({'events': ['low tone'] if 'grave' in text or 'low' in text else ['noise'], 'properties': [], 'environment': [],
                           'exclude': ['noise'] if 'sans bruit' in text else [], 'temporal': [], 'queries': ['low tone' if 'grave' in text or 'low' in text else 'noise']})
'''


def register_test_models(folder, registry_module):
    """Two embedding models with different dimensions and one LLM, all on the 'base' engine (no PyTorch)."""
    folder = Path(folder); keys = []
    for name, dimension, salt, kind in (('test-embed-a', 24, 'a', 'AudioTextEmbedding'), ('test-embed-b', 40, 'b', 'AudioTextEmbedding'), ('test-llm', 0, 'l', 'LLM'),
                                        ('test-embed-slow', 16, 's', 'AudioTextEmbedding')):
        model_dir = folder/name; model_dir.mkdir(parents=True, exist_ok=True)
        adapter = model_dir/'adapter.py'; adapter.write_text(ADAPTER % {'dim': max(8, dimension), 'salt': salt, 'delay': 0.25 if name.endswith('slow') else 0.0}, 'utf-8')
        (model_dir/'weights.json').write_text(json.dumps({'salt': salt}), 'utf-8')
        data = {'modelId': name, 'version': 'v1', 'displayName': name, 'modelType': kind, 'adapter': 'file:'+str(adapter), 'localPath': str(model_dir),
                'engine': 'base', 'capabilities': ['QueryUnderstanding', 'StructuredOutput'] if kind == 'LLM' else ['AudioEmbedding', 'TextEmbedding', 'ZeroShotTagging'],
                'similarityRange': [0.0, 1.0]}
        if kind != 'LLM': data.update(embeddingDimension=dimension, requiredSampleRate=16000, preferredChunkDuration=4.0)
        keys.append(registry_module.register_custom(data).key)
    return keys
