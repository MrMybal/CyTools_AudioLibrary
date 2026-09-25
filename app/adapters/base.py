"""Adapter contract executed inside the engine worker process only.

An adapter turns a model descriptor into callable capabilities. The application selects
adapters through descriptor['adapter'] and talks to them through capabilities; adding a
model means adding a descriptor (and, for a new architecture, one adapter file).

Custom adapter: a Python file exposing `class Adapter(BaseAdapter)`, referenced from the
descriptor as "adapter": "file:D:/path/adapter.py". It runs with the privileges of the
worker process, so only register adapter files you trust.
"""
from pathlib import Path


class BaseAdapter:
    #: waveforms handed to embed_audio are mono float32 at descriptor['requiredSampleRate']
    def __init__(self, descriptor, model_dir, device, sources):
        self.descriptor, self.model_dir, self.device, self.sources = descriptor, Path(model_dir), device, Path(sources)

    def load(self):
        raise NotImplementedError

    def embed_audio(self, waves):
        """list of 1-D float32 arrays of equal length -> float array [len(waves), embeddingDimension]."""
        raise NotImplementedError('This model does not provide AudioEmbedding')

    def embed_text(self, texts):
        raise NotImplementedError('This model does not provide TextEmbedding')

    def generate(self, messages, max_new_tokens=512):
        raise NotImplementedError('This model does not provide text generation')

    def caption(self, wave, prompt=''):
        raise NotImplementedError('This model does not provide Captioning')

    def batch_size(self, seconds):
        return 8

    def unload(self):
        pass


def resolve_device(requested):
    requested = (requested or 'auto').lower()
    if requested == 'cpu': return 'cpu'
    try:
        import torch
        available = torch.cuda.is_available()
    except ImportError: available = False      # engine without PyTorch (custom or test adapters)
    if available: return 'cuda'
    if requested == 'gpu': raise RuntimeError('GPU requested but CUDA is not available in this engine environment')
    return 'cpu'
