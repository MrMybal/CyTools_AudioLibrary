"""Small local chat LLM through transformers (Qwen3 and compatible models), used for query understanding.

A model published as GGUF declares `ggufFile` in its descriptor: transformers then reads the tokenizer, the
chat template and the weights from that single file (the `gguf` package dequantises them). No second
runtime is needed, at the cost of the memory of an unquantised model.

Dequantising takes over half a minute, and the model is unloaded after a few idle minutes, so the first
GPU load also writes the dequantised model to `_dequantized/` next to the GGUF and later loads read that
copy instead (seconds). The copy records which GGUF it came from and is rebuilt when that file changes.
"""
import json
import shutil

from .base import BaseAdapter

CACHE = '_dequantized'


class Adapter(BaseAdapter):
    def load(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        dtype = torch.bfloat16 if self.device == 'cuda' and torch.cuda.is_bf16_supported() else (torch.float16 if self.device == 'cuda' else torch.float32)
        source, options, cache = self.model_dir, {}, None
        gguf = self.descriptor.get('ggufFile')
        if gguf:
            stat = (self.model_dir/gguf).stat()
            origin = {'ggufFile': gguf, 'size': stat.st_size, 'modified': stat.st_mtime_ns, 'dtype': str(dtype)}
            cache = self.model_dir/CACHE
            if self.cached_from(cache) == origin: source = cache                 # same GGUF, same precision: reuse
            else: options = {'gguf_file': gguf}
        self.tokenizer = AutoTokenizer.from_pretrained(str(source), **options)
        if not self.tokenizer.chat_template:
            raise RuntimeError('The model carries no chat template: it cannot be prompted the way it was trained.')
        self.model = AutoModelForCausalLM.from_pretrained(str(source), dtype=dtype, **options).to(self.device).eval()
        if options and self.device == 'cuda': self.write_cache(cache, origin)   # on CPU it would be float32: twice the disk

    @staticmethod
    def cached_from(cache):
        try: return json.loads((cache/'origin.json').read_text(encoding='utf-8'))
        except (OSError, ValueError): return None

    def write_cache(self, cache, origin):
        """Written beside, then swapped in, so an interrupted write never leaves a half copy that looks valid."""
        partial = cache.with_name(cache.name+'.partial')
        try:
            shutil.rmtree(partial, ignore_errors=True)
            self.model.save_pretrained(str(partial), safe_serialization=True)
            self.tokenizer.save_pretrained(str(partial))
            (partial/'origin.json').write_text(json.dumps(origin), encoding='utf-8')
            shutil.rmtree(cache, ignore_errors=True)
            partial.rename(cache)
        except OSError:
            shutil.rmtree(partial, ignore_errors=True)      # no space or no rights: the GGUF path keeps working, only slower

    def generate(self, messages, max_new_tokens=512):
        options = {'tokenize': False, 'add_generation_prompt': True}
        try: prompt = self.tokenizer.apply_chat_template(messages, enable_thinking=False, **options)   # Qwen3: direct answer
        except TypeError: prompt = self.tokenizer.apply_chat_template(messages, **options)
        inputs = self.tokenizer(prompt, return_tensors='pt').to(self.device)
        with self.torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=int(max_new_tokens), do_sample=False, temperature=None,
                                         top_p=None, top_k=None, pad_token_id=self.tokenizer.eos_token_id)
        return self.tokenizer.decode(output[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True).strip()

    def unload(self):
        self.model = self.tokenizer = None
