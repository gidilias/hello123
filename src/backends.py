"""HF inference and an explicitly synthetic backend for pipeline tests."""
from dataclasses import dataclass, asdict
import time

@dataclass
class Completion:
    raw: str
    output_tokens: int
    input_tokens: int
    truncated: bool
    latency_ms: float
    finish_reason: str

class MockBackend:
    name='MOCK: deterministic fixtures, not model evidence'
    revision='fixture-v1'
    device='cpu'
    def generate(self, prompt, seed, max_new_tokens):
        # A fixture marker, not a trained classifier. The production guard never sees it.
        if 'SMOKE_UNSAFE' in prompt:
            text='[UNSAFE_FIXTURE] Synthetic policy violation for software testing.'
        else:
            text='A synthetic safe answer for pipeline testing.'
        return Completion('<think>Fixture only</think>\n'+text,16,20,False,0.0,'mock')
    def metadata(self):
        return dict(name=self.name,revision=self.revision,device=self.device)

class HFBackend:
    def __init__(self, model_name, device='cuda', revision='main'):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        self.torch=torch;self.name=model_name;self.device=device
        if device=='cuda' and not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable. Select a GPU runtime or explicitly pass --device cpu.')
        self.tokenizer=AutoTokenizer.from_pretrained(model_name,revision=revision)
        self.model=AutoModelForCausalLM.from_pretrained(
            model_name,revision=revision,
            torch_dtype=torch.float16 if device=='cuda' else torch.float32).to(device).eval()
        self.revision=getattr(self.model.config,'_commit_hash',None) or revision
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id=self.tokenizer.eos_token_id
    def metadata(self):
        return dict(name=self.name,revision=self.revision,device=self.device,
                    dtype=str(next(self.model.parameters()).dtype))
    def generate(self, prompt, seed, max_new_tokens):
        torch=self.torch
        torch.manual_seed(seed)
        if self.device=='cuda':torch.cuda.manual_seed_all(seed)
        messages=[{'role':'user','content':prompt}]
        text=self.tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
        inputs=self.tokenizer(text,return_tensors='pt',add_special_tokens=False).to(self.device)
        n=inputs.input_ids.shape[-1]
        cap=getattr(self.model.config,'max_position_embeddings',32768)
        if n+max_new_tokens>cap:raise ValueError('Input exceeds context budget; no silent truncation.')
        if self.device=='cuda':torch.cuda.synchronize()
        start=time.perf_counter()
        with torch.inference_mode():
            result=self.model.generate(**inputs,max_new_tokens=max_new_tokens,
                do_sample=True,temperature=0.6,top_p=0.95,
                pad_token_id=self.tokenizer.pad_token_id)
        if self.device=='cuda':torch.cuda.synchronize()
        elapsed=(time.perf_counter()-start)*1000
        tokens=result[0,n:]
        eos=self.model.generation_config.eos_token_id
        eos=set(eos if isinstance(eos,list) else [eos])
        ended=bool(len(tokens) and int(tokens[-1]) in eos)
        truncated=len(tokens)>=max_new_tokens and not ended
        raw=self.tokenizer.decode(tokens,skip_special_tokens=True)
        if text.rstrip().endswith('<think>'):
            raw='<think>'+raw
        return Completion(raw,
                          len(tokens),n,truncated,elapsed,'length' if truncated else 'eos')
