"""Cached waveform pyramid: min/max peaks at several resolutions, memory-mapped on display.

Level 0 holds one (min, max) pair per BASE samples; each following level is FACTOR times
coarser, down to a few hundred pairs. Drawing any zoom range reads at most a few thousand
pairs from the best level, so a one hour file is as fast as a one second file. Below BASE
samples per pixel the viewer switches to the decoded samples of the selected file.
"""
import json
import struct
from pathlib import Path

import numpy as np

MAGIC = b'CYWF1\n'
BASE = 256
FACTOR = 4
MIN_PAIRS = 256


class PyramidBuilder:
    """Streaming builder: feed decoded blocks, then write(path)."""
    def __init__(self, sample_rate, channels):
        self.sample_rate, self.channels = sample_rate, channels
        self.frames = 0
        self.low, self.high = [], []
        self.rest = np.zeros((0,), np.float32), np.zeros((0,), np.float32)

    def feed(self, block):
        # The envelope across channels keeps out-of-phase stereo content visible.
        low, high = block.min(axis=1), block.max(axis=1)
        self.frames += len(block)
        if len(self.rest[0]): low, high = np.concatenate([self.rest[0], low]), np.concatenate([self.rest[1], high])
        full = (len(low)//BASE)*BASE
        if full:
            self.low.append(low[:full].reshape(-1, BASE).min(axis=1)); self.high.append(high[:full].reshape(-1, BASE).max(axis=1))
        self.rest = low[full:], high[full:]

    def write(self, path):
        if len(self.rest[0]):
            self.low.append(np.array([self.rest[0].min()])); self.high.append(np.array([self.rest[1].max()]))
        low = np.concatenate(self.low) if self.low else np.zeros(1, np.float32)
        high = np.concatenate(self.high) if self.high else np.zeros(1, np.float32)
        levels = []
        while True:
            pairs = np.empty((len(low), 2), np.int16)
            pairs[:, 0] = np.clip(np.round(low*32767), -32768, 32767); pairs[:, 1] = np.clip(np.round(high*32767), -32768, 32767)
            levels.append(pairs)
            if len(low) <= MIN_PAIRS: break
            pad = (-len(low)) % FACTOR
            if pad: low, high = np.concatenate([low, np.full(pad, low[-1])]), np.concatenate([high, np.full(pad, high[-1])])
            low, high = low.reshape(-1, FACTOR).min(axis=1), high.reshape(-1, FACTOR).max(axis=1)
        header = json.dumps({'sampleRate': self.sample_rate, 'channels': self.channels, 'frames': self.frames, 'base': BASE,
                             'factor': FACTOR, 'levels': [len(level) for level in levels]}).encode('utf-8')
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        with temporary.open('wb') as handle:
            handle.write(MAGIC); handle.write(struct.pack('<I', len(header))); handle.write(header)
            for level in levels: handle.write(level.tobytes())
        temporary.replace(path)
        return {'levels': len(levels), 'pairs': int(len(levels[0])), 'bytes': path.stat().st_size}


class Pyramid:
    def __init__(self, path):
        self.path = Path(path)
        with self.path.open('rb') as handle:
            if handle.read(len(MAGIC)) != MAGIC: raise ValueError('Not a waveform cache file')
            size = struct.unpack('<I', handle.read(4))[0]
            self.header = json.loads(handle.read(size)); self.offset = len(MAGIC)+4+size
        self.sample_rate, self.frames = self.header['sampleRate'], self.header['frames']
        self.duration = self.frames/self.sample_rate if self.sample_rate else 0.0
        data = np.memmap(self.path, dtype=np.int16, mode='r', offset=self.offset)
        self.levels, position = [], 0
        for count in self.header['levels']:
            self.levels.append(data[position:position+count*2].reshape(-1, 2)); position += count*2

    def samples_per_pair(self, level): return self.header['base']*self.header['factor']**level

    def read(self, start, stop, columns):
        """(low, high) float arrays of length <= columns for the time range [start, stop] seconds."""
        columns = max(1, int(columns))
        first, last = max(0.0, start)*self.sample_rate, min(self.duration, stop)*self.sample_rate
        if last <= first: return np.zeros(0, np.float32), np.zeros(0, np.float32)
        wanted = (last-first)/columns
        level = 0
        while level+1 < len(self.levels) and self.samples_per_pair(level+1) <= wanted: level += 1
        step = self.samples_per_pair(level)
        a, b = int(first//step), min(len(self.levels[level]), int(np.ceil(last/step)))
        pairs = np.asarray(self.levels[level][a:max(a+1, b)], dtype=np.float32)/32767.0
        if len(pairs) > columns:        # reduce to one pair per pixel column
            edges = np.linspace(0, len(pairs), columns+1).astype(int)
            low = np.minimum.reduceat(pairs[:, 0], edges[:-1]); high = np.maximum.reduceat(pairs[:, 1], edges[:-1])
            return low, high
        return pairs[:, 0].copy(), pairs[:, 1].copy()


def waveform_path(library, audio_id):
    return library.waveforms/audio_id[:2]/(audio_id+'.cywf')
