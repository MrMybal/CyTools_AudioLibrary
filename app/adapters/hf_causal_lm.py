"""Small local chat LLM through transformers (Qwen3 and compatible models), used for query understanding."""
from .base import BaseAdapter


class Adapter(BaseAdapter):
    def load(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
        dtype = torch.bfloat16 if self.device == 'cuda' and torch.cuda.is_bf16_supported() else (torch.float16 if self.device == 'cuda' else torch.float32)
        self.model = AutoModelForCausalLM.from_pretrained(str(self.model_dir), dtype=dtype).to(self.device).eval()

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
