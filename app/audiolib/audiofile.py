"""Audio probing and decoding without an external ffmpeg program.

libsndfile (soundfile) is the fast path for WAV/FLAC/OGG/AIFF/MP3 and reports the PCM bit
depth; PyAV (bundled FFmpeg libraries) covers M4A/AAC and everything else, and is the
fallback when libsndfile refuses a file. Files are opened read-only and never modified.
"""
import math
from pathlib import Path

import numpy as np

SOUNDFILE_EXTENSIONS = {'.wav', '.flac', '.ogg', '.oga', '.aif', '.aiff', '.aifc', '.mp3', '.w64', '.caf', '.au', '.opus'}
BIT_DEPTHS = {'PCM_S8': 8, 'PCM_U8': 8, 'PCM_16': 16, 'PCM_24': 24, 'PCM_32': 32, 'FLOAT': 32, 'DOUBLE': 64,
              'ALAC_16': 16, 'ALAC_20': 20, 'ALAC_24': 24, 'ALAC_32': 32}
BLOCK = 1 << 16


class AudioError(Exception):
    pass


def _soundfile_probe(path):
    import soundfile
    info = soundfile.info(str(path))
    if info.frames <= 0 or info.samplerate <= 0: raise AudioError('Empty or unreadable audio stream')
    size = Path(path).stat().st_size
    duration = info.frames/info.samplerate
    return {'duration': duration, 'channels': info.channels, 'sample_rate': info.samplerate, 'frames': info.frames,
            'bit_depth': BIT_DEPTHS.get(info.subtype), 'codec': info.subtype, 'container': info.format,
            'bitrate': int(size*8/duration) if duration > 0 else None, 'embedded': {}}


def _av_probe(path):
    import av
    with av.open(str(path)) as container:
        if not container.streams.audio: raise AudioError('No audio stream')
        stream = container.streams.audio[0]
        context = stream.codec_context
        if stream.duration and stream.time_base: duration = float(stream.duration*stream.time_base)
        elif container.duration: duration = container.duration/1_000_000
        else: duration = 0.0
        rate = context.sample_rate or stream.rate or 0
        if rate <= 0: raise AudioError('Unknown sample rate')
        bits = getattr(context, 'bits_per_raw_sample', 0) or None
        if not bits and context.name.startswith('pcm_'):
            digits = ''.join(c for c in context.name.split('_')[1] if c.isdigit()); bits = int(digits) if digits else None
        embedded = {str(k).lower(): str(v)[:500] for k, v in dict(container.metadata).items()
                    if str(k).lower() in ('title', 'artist', 'album', 'genre', 'comment', 'description', 'date', 'track')}
        return {'duration': duration, 'channels': context.channels or len(stream.layout.channels), 'sample_rate': rate,
                'frames': int(duration*rate), 'bit_depth': bits, 'codec': context.name, 'container': container.format.name,
                'bitrate': (stream.bit_rate or container.bit_rate or None), 'embedded': embedded}


def probe(path):
    path = Path(path); errors = []
    order = (_soundfile_probe, _av_probe) if path.suffix.lower() in SOUNDFILE_EXTENSIONS else (_av_probe, _soundfile_probe)
    for function in order:
        try:
            info = function(path)
            if function is _soundfile_probe:
                try: info['embedded'] = _av_probe(path)['embedded']
                except Exception: pass
            return info
        except Exception as exc: errors.append(type(exc).__name__+': '+str(exc))
    raise AudioError('; '.join(errors))


def _soundfile_blocks(path, start_frame, frames):
    import soundfile
    with soundfile.SoundFile(str(path)) as handle:
        if start_frame: handle.seek(min(start_frame, handle.frames))
        remaining = frames if frames is not None else -1
        while remaining:
            count = BLOCK if remaining < 0 else min(BLOCK, remaining)
            block = handle.read(count, dtype='float32', always_2d=True)
            if not len(block): break
            if remaining > 0: remaining -= len(block)
            yield block, handle.samplerate


def _av_blocks(path, start_frame, frames):
    import av
    with av.open(str(path)) as container:
        stream = container.streams.audio[0]
        rate = stream.codec_context.sample_rate or stream.rate
        channels = stream.codec_context.channels or len(stream.layout.channels)
        resampler = av.AudioResampler(format='flt', layout=stream.layout.name, rate=rate)
        if start_frame > rate:      # coarse seek, then precise trimming with decoded timestamps
            container.seek(int((start_frame/rate-0.5)/stream.time_base), stream=stream, any_frame=False, backward=True)
        sought = start_frame > rate
        position, remaining = None, frames
        def decoded():
            for frame in container.decode(stream):
                yield frame
            yield None      # flush the resampler
        for frame in decoded():
            for out in resampler.resample(frame):
                block = out.to_ndarray().reshape(-1, channels)
                if position is None:
                    if not sought: position = 0
                    elif out.pts is not None: position = int(round(float(out.pts*out.time_base)*rate))
                    else: position = start_frame
                begin, position = position, position+len(block)
                if position <= start_frame: continue
                if begin < start_frame: block = block[start_frame-begin:]
                if remaining is not None:
                    block = block[:remaining]; remaining -= len(block)
                if len(block): yield np.ascontiguousarray(block, dtype=np.float32), rate
                if remaining == 0: return


def blocks(path, start=0.0, stop=None):
    """Yield (float32 block [frames, channels], sample_rate); start/stop in seconds."""
    path = Path(path)
    info = probe(path)
    rate = info['sample_rate']
    start_frame = max(0, int(round(start*rate)))
    frames = None if stop is None else max(0, int(round(stop*rate))-start_frame)
    if frames == 0: return
    order = (_soundfile_blocks, _av_blocks) if path.suffix.lower() in SOUNDFILE_EXTENSIONS else (_av_blocks, _soundfile_blocks)
    error = None
    for function in order:
        produced = False
        try:
            for item in function(path, start_frame, frames):
                produced = True
                yield item
            return
        except Exception as exc:
            if produced: raise AudioError(str(exc)) from exc
            error = exc
    raise AudioError(str(error))


def decode(path, start=0.0, stop=None, mono=False, sample_rate=None):
    """Whole (or partial) decode to float32 [frames, channels]; optional mono mix and resampling."""
    parts, rate = [], None
    for block, rate in blocks(path, start, stop): parts.append(block)
    if not parts: raise AudioError('No audio decoded')
    audio = np.concatenate(parts)
    if mono and audio.shape[1] > 1: audio = audio.mean(axis=1, keepdims=True)
    if sample_rate and sample_rate != rate: audio, rate = resample(audio, rate, sample_rate), sample_rate
    return audio, rate


def resample(audio, source_rate, target_rate):
    if source_rate == target_rate: return audio
    from scipy.signal import resample_poly
    divisor = math.gcd(int(source_rate), int(target_rate))
    return resample_poly(audio, int(target_rate)//divisor, int(source_rate)//divisor, axis=0).astype(np.float32)


# ---------------------------------------------------------------------------
# Loudness: ITU-R BS.1770-4 integrated loudness with absolute and relative gating.
# ---------------------------------------------------------------------------
def _k_weighting(rate):
    def shelf(fc, gain, q):
        a = 10**(gain/40); w = 2*math.pi*fc/rate; alpha = math.sin(w)/(2*q); c = math.cos(w); s = 2*math.sqrt(a)*alpha
        b = np.array([a*((a+1)+(a-1)*c+s), -2*a*((a-1)+(a+1)*c), a*((a+1)+(a-1)*c-s)])
        d = np.array([(a+1)-(a-1)*c+s, 2*((a-1)-(a+1)*c), (a+1)-(a-1)*c-s])
        return b/d[0], d/d[0]
    def highpass(fc, q):
        w = 2*math.pi*fc/rate; alpha = math.sin(w)/(2*q); c = math.cos(w)
        b = np.array([(1+c)/2, -(1+c), (1+c)/2]); d = np.array([1+alpha, -2*c, 1-alpha])
        return b/d[0], d/d[0]
    return shelf(1681.974450955533, 3.999843853973347, 0.7071752369554196), highpass(38.13547087602444, 0.5003270373238773)


class LoudnessMeter:
    """Streaming meter: feed blocks, read peak, RMS and gated LUFS at the end."""
    WEIGHTS = (1.0, 1.0, 1.0, 0.0, 1.41, 1.41)

    def __init__(self, rate, channels, gated=True):
        from scipy.signal import lfilter_zi
        self.rate, self.channels, self.gated = rate, channels, gated and rate >= 8000
        self.peak, self.square_sum, self.count = 0.0, 0.0, 0
        self.hop = max(1, int(round(rate*0.1))); self.pending = np.zeros((0, channels), np.float64); self.hops = []
        if self.gated:
            self.filters = _k_weighting(rate)
            self.state = [[np.zeros((2, channels)) for _ in self.filters]]

    def feed(self, block):
        if not len(block): return
        self.peak = max(self.peak, float(np.abs(block).max()))
        self.square_sum += float(np.square(block, dtype=np.float64).sum()); self.count += block.size
        if not self.gated: return
        from scipy.signal import lfilter
        signal = block.astype(np.float64)
        for index, (b, a) in enumerate(self.filters):
            signal, self.state[0][index] = lfilter(b, a, signal, axis=0, zi=self.state[0][index])
        data = np.concatenate([self.pending, signal]) if len(self.pending) else signal
        full = (len(data)//self.hop)*self.hop
        if full:
            self.hops.append(np.square(data[:full]).reshape(-1, self.hop, self.channels).mean(axis=1))
        self.pending = data[full:]

    def result(self):
        to_db = lambda value: 20*math.log10(value) if value > 1e-10 else -200.0
        output = {'peak_db': to_db(self.peak), 'rms_db': to_db(math.sqrt(self.square_sum/self.count)) if self.count else -200.0, 'lufs': None}
        if not self.gated or not self.hops: return output
        hops = np.concatenate(self.hops)
        if len(hops) < 4: return output
        weights = np.array([self.WEIGHTS[i] if i < len(self.WEIGHTS) else 1.0 for i in range(self.channels)])
        if self.channels == 1: weights = np.array([1.0])
        window = (hops[:-3]+hops[1:-2]+hops[2:-1]+hops[3:])/4          # 400 ms blocks, 75 % overlap
        power = (window*weights).sum(axis=1)
        loudness = -0.691+10*np.log10(np.maximum(power, 1e-12))
        keep = loudness > -70
        if not keep.any(): return output
        relative = -0.691+10*math.log10(power[keep].mean())-10
        keep &= loudness > relative
        if keep.any(): output['lufs'] = float(-0.691+10*math.log10(power[keep].mean()))
        return output
