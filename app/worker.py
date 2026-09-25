"""Engine worker: owns every loaded model, outside the UI/CLI/MCP process.

Started by audiolib.modelhost with the interpreter of an AI engine environment. Protocol:
one JSON request per stdin line, one JSON response per stdout line ({"id", "ok", ...}),
optional {"event": "progress"} lines in between. Library noise goes to stderr, which the
host stores in data/logs/model-worker.log. Closing stdin stops the worker and frees memory.
"""
import json
import os
import sys
import time
import traceback
from pathlib import Path

PROTOCOL = sys.stdout
sys.stdout = sys.stderr      # nothing but the protocol may reach the real stdout
APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
os.environ.setdefault('HF_HUB_OFFLINE', '1')        # inference never downloads: files come from the Installation tab
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')

import numpy as np

MODELS = {}
MIN_SECONDS = 1.0


def send(value):
    PROTOCOL.write(json.dumps(value, allow_nan=False)+'\n'); PROTOCOL.flush()


def vram():
    try:
        import torch
        return int(torch.cuda.memory_allocated()) if torch.cuda.is_available() else 0
    except Exception: return 0


def load(request):
    from adapters import load_adapter_class
    from adapters.base import resolve_device
    key = request['modelKey']
    if key in MODELS: return {'device': MODELS[key].device, 'alreadyLoaded': True, 'vramBytes': vram()}
    started, before = time.monotonic(), vram()
    device = resolve_device(request.get('device'))
    adapter = load_adapter_class(request['descriptor']['adapter'])(request['descriptor'], request['modelDir'], device, request['sources'])
    adapter.load()
    MODELS[key] = adapter
    return {'device': device, 'seconds': round(time.monotonic()-started, 2), 'vramBytes': max(0, vram()-before)}      # this model only


def unload(request):
    import gc
    keys = [request['modelKey']] if request.get('modelKey') else list(MODELS)
    for key in keys:
        adapter = MODELS.pop(key, None)
        if adapter: adapter.unload()
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available(): torch.cuda.empty_cache()
    except Exception: pass
    return {'unloaded': keys, 'vramBytes': vram()}


def windows(item, rate):
    """Decode each requested window as mono float32 at the model rate; pad very short sounds."""
    from audiolib.audiofile import decode
    segments = item['segments']
    out, i = [], 0
    while i < len(segments):        # decode long recordings span by span (<= 2 minutes in memory)
        j = i
        while j+1 < len(segments) and segments[j+1][2]-segments[i][1] <= 120: j += 1
        first, last = segments[i][1], max(s[2] for s in segments[i:j+1])
        audio, _ = decode(item['path'], start=first, stop=last, mono=True, sample_rate=rate)
        audio = audio[:, 0]
        for _, start, stop in segments[i:j+1]:
            a, b = int(round((start-first)*rate)), int(round((stop-first)*rate))
            wave = audio[a:max(a+1, b)]
            if len(wave) < int(MIN_SECONDS*rate): wave = np.pad(wave, (0, int(MIN_SECONDS*rate)-len(wave)))
            out.append(np.ascontiguousarray(wave, dtype=np.float32))
        i = j+1
    return out


def embed_audio(request):
    adapter = MODELS[request['modelKey']]
    rate = int(adapter.descriptor.get('requiredSampleRate') or 16000)
    maximum = adapter.descriptor.get('maximumAudioDuration')
    results, arrays = [], {}
    for item in request['items']:
        try:
            waves = windows(item, rate)
            if maximum: waves = [w[:int(maximum*rate)] for w in waves]
            vectors = [None]*len(waves)
            order = sorted(range(len(waves)), key=lambda i: len(waves[i]))
            position = 0
            while position < len(order):      # batch windows of identical length: no padding inside a model batch
                length = len(waves[order[position]]); size = adapter.batch_size(length/rate)
                group = [i for i in order[position:position+size] if len(waves[i]) == length]
                output = np.asarray(adapter.embed_audio([waves[i] for i in group]), dtype=np.float32)
                for i, vector in zip(group, output): vectors[i] = vector
                position += len(group)
            matrix = np.stack(vectors)
            segments = [list(s) for s in item['segments']]
            if len(segments) > 1:           # whole-clip vector = mean of the window vectors, stored as segment -1
                unit = matrix/np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-12)
                matrix = np.concatenate([unit.mean(axis=0, keepdims=True), matrix])
                segments = [[-1, segments[0][1], segments[-1][2]]]+segments
            arrays[item['id']] = matrix
            results.append({'id': item['id'], 'ok': True, 'segments': segments})
        except Exception as exc:
            traceback.print_exc()
            results.append({'id': item['id'], 'ok': False, 'error': (type(exc).__name__+': '+str(exc))[:500]})
            if 'out of memory' in str(exc).lower(): unload({}); raise
    np.savez(request['output'], **arrays)
    return {'results': results}


def embed_text(request):
    adapter = MODELS[request['modelKey']]
    vectors = np.asarray(adapter.embed_text(request['texts']), dtype=np.float32)
    return {'vectors': vectors.tolist()}


def embed_wave(request):
    """Audio query from a time selection of one file (Find sounds similar to selection)."""
    adapter = MODELS[request['modelKey']]
    rate = int(adapter.descriptor.get('requiredSampleRate') or 16000)
    wave = windows({'path': request['path'], 'segments': [[0, request['start'], request['stop']]]}, rate)[0]
    maximum = adapter.descriptor.get('maximumAudioDuration') or adapter.descriptor.get('preferredChunkDuration')
    if maximum: wave = wave[:int(maximum*rate)]
    return {'vectors': np.asarray(adapter.embed_audio([wave]), dtype=np.float32).tolist()}


def generate(request):
    return {'text': MODELS[request['modelKey']].generate(request['messages'], request.get('maxNewTokens', 512))}


def status(_):
    try: import torch
    except ImportError: return {'models': {k: a.device for k, a in MODELS.items()}, 'vramBytes': 0, 'torch': None, 'cuda': False, 'device': 'cpu', 'pid': os.getpid()}
    peak = int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else 0
    return {'models': {k: a.device for k, a in MODELS.items()}, 'vramBytes': vram(), 'peakVramBytes': peak, 'torch': torch.__version__,
            'cuda': torch.cuda.is_available(), 'device': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu',
            'pid': os.getpid()}


HANDLERS = {'load': load, 'unload': unload, 'embed_audio': embed_audio, 'embed_text': embed_text, 'embed_wave': embed_wave,
            'generate': generate, 'status': status}


def main():
    send({'event': 'ready', 'pid': os.getpid(), 'python': sys.version.split()[0]})
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        request = json.loads(line)
        if request.get('op') == 'shutdown':
            send({'id': request.get('id'), 'ok': True}); break
        try:
            send({'id': request.get('id'), 'ok': True, **HANDLERS[request['op']](request)})
        except Exception as exc:
            traceback.print_exc()
            code = 'InsufficientVRAM' if 'out of memory' in str(exc).lower() else type(exc).__name__
            send({'id': request.get('id'), 'ok': False, 'code': code, 'message': str(exc)[:2000]})


if __name__ == '__main__':
    main()
