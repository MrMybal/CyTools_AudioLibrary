"""LAION-CLAP family through transformers.ClapModel (local folder, no network access)."""
import numpy as np

from .base import BaseAdapter


class Adapter(BaseAdapter):
    def load(self):
        import torch
        from transformers import ClapModel, ClapProcessor
        self.torch = torch
        self.processor = ClapProcessor.from_pretrained(str(self.model_dir))
        self.model = ClapModel.from_pretrained(str(self.model_dir)).to(self.device).eval()
        self.rate = int(self.descriptor.get('requiredSampleRate') or 48000)

    def batch_size(self, seconds): return 16 if self.device == 'cuda' else 4

    @staticmethod
    def _tensor(output):
        # transformers 4.x returns the projected tensor, 5.x a ModelOutput holding it
        return output if hasattr(output, 'shape') else output.pooler_output

    def embed_audio(self, waves):
        inputs = self.processor(audio=[np.asarray(w) for w in waves], sampling_rate=self.rate, return_tensors='pt')
        with self.torch.inference_mode():
            features = self._tensor(self.model.get_audio_features(**{k: v.to(self.device) for k, v in inputs.items()}))
        return features.float().cpu().numpy()

    def embed_text(self, texts):
        inputs = self.processor(text=list(texts), return_tensors='pt', padding=True, truncation=True)
        with self.torch.inference_mode():
            features = self._tensor(self.model.get_text_features(**{k: v.to(self.device) for k, v in inputs.items()}))
        return features.float().cpu().numpy()

    def unload(self):
        self.model = self.processor = None
