"""Omni-Embed-Audio (JudeJiwoo/Omni-Embed-Audio): LoRA + 512-d projection heads on an Omni backbone.

Follows examples/encode_example.py of the pinned upstream source, with two differences:
the backbone and the checkpoint are loaded from local folders, and audio is passed as
decoded arrays so that segments of a long file can be embedded without temporary files.
"""
import sys
from types import SimpleNamespace

import numpy as np

from .base import BaseAdapter


class Adapter(BaseAdapter):
    def load(self):
        import torch
        source = self.sources/'Omni-Embed-Audio'
        if not (source/'AudioRetrieval').is_dir():
            raise RuntimeError('Omni-Embed-Audio engine source is missing: install it from the Installation tab')
        if str(source) not in sys.path: sys.path.insert(0, str(source))
        from AudioRetrieval.models.omni_embed_adapter import OmniEmbedAdapter, _BatchInputs
        from AudioRetrieval.training.oea.train_omniembed_lora import ProjectionHead, attach_lora
        backbone = self.model_dir/'backbone'
        checkpoint = self.model_dir/(self.descriptor.get('weightFile') or 'step_40.pt')
        if not (backbone/'config.json').is_file() or not checkpoint.is_file():
            raise RuntimeError('Omni-Embed-Audio files are incomplete in '+str(self.model_dir)+' (use Repair)')
        self.torch, self._inputs = torch, _BatchInputs
        self.adapter = OmniEmbedAdapter(repo_id=str(backbone), local_path=str(backbone), device=self.device,
                                        passage_prefix='passage:', query_prefix='query:')
        lora = SimpleNamespace(lora_rank=16, lora_alpha=32, lora_dropout=0.05,
                               lora_targets=['q_proj', 'k_proj', 'v_proj', 'o_proj', 'qkv', 'out_proj'])
        peft_model = attach_lora(self.adapter.get_underlying_model(), lora)
        self.adapter.set_underlying_model(peft_model)
        state = self._load_checkpoint(torch, checkpoint)
        result = peft_model.load_state_dict(state['lora_state_dict'], strict=False)
        if len(result.unexpected_keys) > 0: raise RuntimeError('LoRA weights do not match this backbone: '+str(result.unexpected_keys[:3]))
        hidden = peft_model.config.text_config.hidden_size
        dimension = int(self.descriptor.get('embeddingDimension') or 512)
        self.audio_head = ProjectionHead(hidden, dimension, 0.1).to(self.adapter.device).eval()
        self.text_head = ProjectionHead(hidden, dimension, 0.1).to(self.adapter.device).eval()
        self.audio_head.load_state_dict(state['audio_head']); self.text_head.load_state_dict(state['text_head'])
        del state

    @staticmethod
    def _load_checkpoint(torch, checkpoint):
        """Load an upstream training checkpoint on any OS.

        The released .pt files are full training checkpoints pickled on Linux: besides the tensors we need they hold
        the training configuration, including pathlib.PosixPath objects, which Python refuses to rebuild on Windows.
        Only while unpickling, inside this worker process, PosixPath is mapped to the inert PurePosixPath; the
        configuration entries are discarded right after. They come from the pinned official repository.
        """
        import pathlib
        original = pathlib.PosixPath
        try: return torch.load(str(checkpoint), map_location='cpu', weights_only=True, mmap=True)
        except Exception: pass
        try:
            pathlib.PosixPath = pathlib.PurePosixPath
            state = torch.load(str(checkpoint), map_location='cpu', weights_only=False, mmap=True)
        finally: pathlib.PosixPath = original
        return {key: state[key] for key in ('lora_state_dict', 'audio_head', 'text_head')}

    def batch_size(self, seconds): return max(1, int(40//max(1.0, seconds))) if self.device == 'cuda' else 1

    def embed_audio(self, waves):
        adapter = self.adapter
        conversations = adapter._build_audio_messages(['segment.wav']*len(waves), adapter.passage_prefix)
        texts = adapter._apply_chat_template(conversations)
        batch = adapter._prepare_batch(self._inputs(text=texts, audio_arrays=[np.asarray(w, dtype=np.float32) for w in waves]),
                                       text_kwargs={'truncation': True, 'padding': True, 'max_length': max(adapter.text_max_length, 32768)})
        raw = adapter._encode(batch)
        with self.torch.inference_mode():
            return self.audio_head(self.torch.from_numpy(raw).to(adapter.device)).float().cpu().numpy()

    def embed_text(self, texts):
        raw = self.adapter.encode_text(list(texts), batch_size=16)
        with self.torch.inference_mode():
            return self.text_head(self.torch.from_numpy(raw).to(self.adapter.device)).float().cpu().numpy()

    def unload(self):
        self.adapter = self.audio_head = self.text_head = None
