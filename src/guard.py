"""Output gating. Classifier decisions are not independent evaluation labels."""
from dataclasses import dataclass
import re,time
from .common import FALLBACK

@dataclass
class Decision:
    action: str
    reason: str
    classifier_output: str=''
    latency_ms: float=0.0


def parse_verdict(text):
    # Reject ambiguous or malformed classifier output instead of guessing safe.
    lines=[s.strip() for s in text.strip().splitlines() if s.strip()]
    if lines==['safe']: return Decision('allow','classifier_safe',text)
    if lines and lines[0]=='unsafe' and (len(lines)==1 or
        (len(lines)==2 and re.fullmatch(r'S\d+(?:\s*,\s*S\d+)*',lines[1]))):
        return Decision('block','classifier_unsafe',text)
    return Decision('block','classifier_malformed',text)

class MockGuard:
    name='MOCK: fixture guard, not a safety model'
    def metadata(self):return {'name':self.name,'revision':'fixture-v1'}
    def check(self,prompt,answer):
        blocked='[UNSAFE_FIXTURE]' in answer
        return Decision('block' if blocked else 'allow','mock_fixture')

class LlamaGuard:
    name='meta-llama/Llama-Guard-3-1B'
    def __init__(self,device='cuda',revision='main',model_name=None):
        from .backends import HFBackend
        # Reuse loading and revision tracking. Classification uses its own template.
        self.backend=HFBackend(model_name or self.name,device,revision)
    def metadata(self):return self.backend.metadata()
    def check(self,prompt,answer):
        b=self.backend;torch=b.torch
        start=time.perf_counter()
        try:
            conversation=[{'role':'user','content':[{'type':'text','text':prompt}]},
                          {'role':'assistant','content':[{'type':'text','text':answer}]}]
            ids=b.tokenizer.apply_chat_template(conversation,return_tensors='pt').to(b.device)
            limit=min(getattr(b.model.config,'max_position_embeddings',8192),8192)
            if ids.shape[-1]+32>limit:
                return Decision('block','guard_context_limit')
            if b.device=='cuda':torch.cuda.synchronize()
            with torch.inference_mode():
                out=b.model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),
                    max_new_tokens=32,do_sample=False,pad_token_id=b.tokenizer.eos_token_id)
            if b.device=='cuda':torch.cuda.synchronize()
            verdict=b.tokenizer.decode(out[0,ids.shape[-1]:],skip_special_tokens=True)
            decision=parse_verdict(verdict)
            decision.latency_ms=(time.perf_counter()-start)*1000
            return decision
        except Exception as exc:
            # Availability cost is observable, and no raw answer escapes on error.
            return Decision('block','guard_error:'+type(exc).__name__,
                            latency_ms=(time.perf_counter()-start)*1000)

def deliver(prompt,answer,truncated,incomplete,guard):
    start=time.perf_counter()
    if truncated: d=Decision('block','incomplete_generation')
    elif incomplete or not answer.strip():d=Decision('block','missing_final_answer')
    else:d=guard.check(prompt,answer)
    d.latency_ms=(time.perf_counter()-start)*1000
    return (answer if d.action=='allow' else FALLBACK),d


def parse_qwen_verdict(text):
    lines=[s.strip() for s in text.strip().splitlines() if s.strip()]
    if not lines or lines[0] not in ('Safety: Safe','Safety: Unsafe','Safety: Controversial'):
        return Decision('block','classifier_malformed',text)
    if sum(s.startswith('Safety:') for s in lines)!=1:
        return Decision('block','classifier_malformed',text)
    if any(not s.startswith(('Categories:', 'Refusal:')) for s in lines[1:]):
        return Decision('block','classifier_malformed',text)
    label=lines[0].split(': ',1)[1]
    return Decision('allow' if label=='Safe' else 'block','classifier_'+label.lower(),text)

class QwenGuard(LlamaGuard):
    """Open-access response moderation. Controversial outputs are withheld."""
    name='Qwen/Qwen3Guard-Gen-0.6B'
    def check(self,prompt,answer):
        b=self.backend;torch=b.torch;start=time.perf_counter()
        try:
            conversation=[{'role':'user','content':prompt},{'role':'assistant','content':answer}]
            text=b.tokenizer.apply_chat_template(conversation,tokenize=False)
            inputs=b.tokenizer([text],return_tensors='pt').to(b.device)
            n=inputs.input_ids.shape[-1]
            if n+128>min(getattr(b.model.config,'max_position_embeddings',8192),8192):
                return Decision('block','guard_context_limit')
            if b.device=='cuda':torch.cuda.synchronize()
            with torch.inference_mode():
                out=b.model.generate(**inputs,max_new_tokens=128,do_sample=False,
                    pad_token_id=b.tokenizer.eos_token_id)
            if b.device=='cuda':torch.cuda.synchronize()
            ids=out[0,n:]
            verdict=b.tokenizer.decode(ids,skip_special_tokens=True)
            eos=b.model.generation_config.eos_token_id
            eos=eos if isinstance(eos,list) else [eos]
            if len(ids)>=128 and int(ids[-1]) not in eos:
                return Decision('block','classifier_truncated',verdict)
            d=parse_qwen_verdict(verdict);d.latency_ms=(time.perf_counter()-start)*1000
            return d
        except Exception as exc:
            return Decision('block','guard_error:'+type(exc).__name__,latency_ms=(time.perf_counter()-start)*1000)
