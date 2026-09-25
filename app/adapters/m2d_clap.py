"""M2D-CLAP (nttcslab/m2d) through the project's own portable runtime, pinned in runtime/sources/m2d.

Works for every M2D-CLAP checkpoint folder whose name follows the upstream convention
(m2d_clap_vit_base-80x1001p16x16p16kpBpTI-2025, the 2024 GTE variant, a fine-tuned copy...).
The text tower is rebuilt from a local configuration and filled from the checkpoint, so no
file is fetched from the network at inference time.
"""
import sys
from pathlib import Path

import numpy as np

from .base import BaseAdapter


class Adapter(BaseAdapter):
    def load(self):
        import torch
        examples = self.sources/'m2d'/'examples'
        if not (examples/'portable_m2d.py').is_file():
            raise RuntimeError('M2D engine source is missing: install the AI engine from the Installation tab')
        if str(examples) not in sys.path: sys.path.insert(0, str(examples))
        import portable_m2d
        weight = self.descriptor.get('weightFile')
        candidates = [self.model_dir/weight] if weight else sorted(self.model_dir.rglob('checkpoint-*.pth'))+sorted(self.model_dir.rglob('*.pth'))
        candidates = [c for c in candidates if c.is_file()]
        if not candidates: raise RuntimeError('No M2D checkpoint (.pth) found in '+str(self.model_dir))
        # Upstream (Example_4_CLAP2025): checkpoints with a semantic audio projector need flat patch features.
        flat = self.descriptor.get('flatFeatures')
        self.model = portable_m2d.PortableM2D(str(candidates[0]), flat_features=bool(flat))
        if flat is None and hasattr(getattr(self.model.backbone, 'audio_proj', None), 'dont_average'):
            self.model = portable_m2d.PortableM2D(str(candidates[0]), flat_features=True)
        kind = portable_m2d.parse_clap_type(candidates[0].parent.name)
        text_dir = self._text_encoder_dir(kind)
        included = getattr(self.model.cfg, 'text_encoder_weight', None)
        if included and text_dir is not None:
            self.model.text_encoder = self._text_tower(portable_m2d, candidates[0], text_dir)
        elif text_dir is not None:
            self.model.text_encoder = self._pretrained_tower(portable_m2d, kind, text_dir)
        self.model = self.model.to(self.device).eval()
        if hasattr(self.model, 'text_encoder'): self.model.text_encoder = self.model.text_encoder.to(self.device).eval()
        self.torch = torch

    def _text_encoder_dir(self, kind):
        names = {'A': 'thenlper/gte-base', 'B': 'google-bert/bert-base-uncased', 'M': 'google-bert/bert-large-uncased',
                 'Q': 'FacebookAI/roberta-large', 'R': 'FacebookAI/roberta-base'}
        if kind not in names: raise RuntimeError('Text encoder type %r of this checkpoint is not supported by this adapter' % kind)
        folder = self.model_dir/'support'/names[kind]
        if not (folder/'config.json').is_file(): raise RuntimeError('Text encoder files are missing: '+str(folder)+' (use Repair)')
        return folder

    def _text_tower(self, portable, checkpoint, folder):
        """BERT-style tower with the architecture of `folder` and the weights stored in the checkpoint ('TI' models)."""
        import torch
        from transformers import AutoConfig, AutoModel, AutoTokenizer

        class Tower(torch.nn.Module):
            def __init__(tower):
                super().__init__()
                tower.tokenizer = AutoTokenizer.from_pretrained(str(folder))
                tower.text_encoder = AutoModel.from_config(AutoConfig.from_pretrained(str(folder)))
            forward = portable.BertXEncoder.forward
        tower = Tower()
        weights = torch.load(str(checkpoint), map_location='cpu', weights_only=False)
        weights = weights['model'] if 'model' in weights else weights
        weights = portable.extract_weight(weights, 'text_encoder.')
        result = tower.load_state_dict(weights, strict=False)
        missing = [k for k in result.missing_keys if 'position_ids' not in k]
        unexpected = [k for k in result.unexpected_keys if 'position_ids' not in k]
        if missing or unexpected:
            raise RuntimeError(f'Text tower does not match the checkpoint (missing {missing[:3]}, unexpected {unexpected[:3]})')
        return tower

    def _pretrained_tower(self, portable, kind, folder):
        if kind == 'A':
            tower = portable.GTETextEncoder(clip_weight=str(folder))
        else: tower = portable.BertXEncoder(clip_weight=str(folder))
        return tower

    def batch_size(self, seconds): return 16 if self.device == 'cuda' else 4

    def embed_audio(self, waves):
        with self.torch.inference_mode():
            batch = self.torch.from_numpy(np.stack(waves)).to(self.device)
            return self.model.encode_clap_audio(batch).float().cpu().numpy()

    def embed_text(self, texts):
        with self.torch.inference_mode():
            return self.model.encode_clap_text(list(texts), truncate=True).float().cpu().numpy()

    def unload(self):
        self.model = None
