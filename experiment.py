#!/usr/bin/env python3
"""Replay a fixed Midterm corpus across A/B/C. No new attack optimization."""
import argparse,json,os,sys,time,platform,subprocess
from pathlib import Path
from dataclasses import asdict
from src.backends import MockBackend,HFBackend
from src.guard import MockGuard,LlamaGuard,QwenGuard,deliver
from src.common import PREFIX,FALLBACK,visible_answer,fingerprint,record_id,refusal_flag


def load_jsonl(path):
    if not Path(path).exists():return []
    # Repair only an interrupted final append; malformed interior rows are errors.
    lines=Path(path).read_text(encoding='utf-8').splitlines()
    rows=[]
    for i,line in enumerate(lines):
        if not line.strip():continue
        try:rows.append(json.loads(line))
        except json.JSONDecodeError:
            if i!=len(lines)-1:raise
            Path(path).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    return rows

def append(path,row):
    with open(path,'a',encoding='utf-8') as f:
        f.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())

def atomic_json(path,value):
    temp=Path(str(path)+'.tmp');temp.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8');temp.replace(path)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--backend',choices=['mock','hf'],default='mock')
    ap.add_argument('--cases',default='data/cases.jsonl')
    ap.add_argument('--seeds',default='42,43,44')
    ap.add_argument('--out',default='runs/smoke')
    ap.add_argument('--device',choices=['cuda','cpu'],default='cuda')
    ap.add_argument('--max-new-tokens',type=int,default=1536)
    ap.add_argument('--model',default='deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B')
    ap.add_argument('--model-revision',default='main')
    ap.add_argument('--guard-revision',default='main')
    ap.add_argument('--guard',choices=['qwen','llama'],default='qwen')
    ap.add_argument('--guard-device',choices=['cuda','cpu'])
    ap.add_argument('--limit',type=int)
    ap.add_argument('--ablation',action='store_true',help='Add guard without safety prefix (D)')
    args=ap.parse_args()
    if args.max_new_tokens<1:ap.error('max-new-tokens must be positive')
    seeds=[int(s) for s in args.seeds.split(',')]
    if not seeds or len(set(seeds))!=len(seeds):ap.error('Seeds must be distinct')
    case_path=Path(args.cases)
    cases=[json.loads(s) for s in case_path.read_text(encoding='utf-8').splitlines() if s.strip()]
    if args.limit is not None:
        if args.limit<1:ap.error('limit must be positive')
        # Keep both strata even in quick checks.
        cases=[c for kind in ('attack','benign') for c in [x for x in cases if x['kind']==kind][:args.limit]]
    ids=[c['id'] for c in cases]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate case ids')
    if any(c['kind'] not in ('attack','benign') or not c['prompt'].strip() for c in cases):raise ValueError('Invalid case')
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    configs=['A_baseline','B_prefix','C_prefix_guard']+(['D_guard_only'] if args.ablation else [])
    setting=dict(configurations=configs,backend=args.backend,cases=cases,seeds=seeds,model=args.model,
        device=args.device,max_new_tokens=args.max_new_tokens,prefix=PREFIX,
        guard=QwenGuard.name if args.guard=='qwen' else LlamaGuard.name,guard_device=args.guard_device or args.device,model_revision=args.model_revision,
        guard_revision=args.guard_revision,code=fingerprint({str(p):p.read_text() for p in sorted(Path('src').glob('*.py'))} | {'experiment.py':Path(__file__).read_text()}))
    run_hash=fingerprint(setting)
    old=out/'manifest.json'
    manifest=json.loads(old.read_text()) if old.exists() else {}
    if manifest and manifest.get('run_hash')!=run_hash:raise ValueError('Resume settings/code differ. Use a new --out directory.')
    manifest.update(status='RUNNING',evidence='MOCK_ONLY' if args.backend=='mock' else 'HF_RUN',
        run_hash=run_hash,settings=setting,python=sys.version,platform=platform.platform(),
        expected_rows=len(cases)*len(seeds)*len(configs))
    atomic_json(old,manifest)
    log=out/'results.jsonl';existing=load_jsonl(log)
    seen={r['id'] for r in existing};cache={(r['case_id'],r['seed'],r['config']):r for r in existing}
    if len(seen)!=len(existing):raise ValueError('Duplicate result ids')
    target=None;guard=None
    try:
        if len(seen)<manifest['expected_rows']:
            target=MockBackend() if args.backend=='mock' else HFBackend(args.model,args.device,args.model_revision)
            guard=MockGuard() if args.backend=='mock' else (QwenGuard if args.guard=='qwen' else LlamaGuard)(args.guard_device or args.device,args.guard_revision)
            metadata={'target':target.metadata(),'guard':guard.metadata()}
            if manifest.get('models') and manifest['models']!=metadata:
                raise ValueError('Resolved model revision changed. Resume using pinned --model-revision / --guard-revision.')
            manifest['models']=metadata;atomic_json(old,manifest)
        for seed in seeds:
            for case in cases:
                pair=fingerprint([seed,case['id']]);generation_seed=int(pair[:8],16)%(2**31)
                for config in configs:
                    rid=record_id(case['id'],seed,config)
                    if rid in seen:continue
                    prompt=case['prompt'] if config in ('A_baseline','D_guard_only') else PREFIX+'\n\n'+case['prompt']
                    error=''
                    if config in ('C_prefix_guard','D_guard_only'):
                        source=cache[(case['id'],seed,'B_prefix' if config=='C_prefix_guard' else 'A_baseline')]
                        completion=source['completion'];error=source['generation_error']
                    else:
                        try:completion=asdict(target.generate(prompt,generation_seed,args.max_new_tokens))
                        except Exception as exc:
                            error=type(exc).__name__+': '+str(exc)[:250]
                            completion=dict(raw='',output_tokens=0,input_tokens=0,truncated=False,latency_ms=0.0,finish_reason='error')
                    visible=visible_answer(completion['raw'])
                    applied=config in ('C_prefix_guard','D_guard_only')
                    if applied:
                        shown,decision=deliver(prompt,visible.text,completion['truncated'],visible.incomplete_reasoning,guard)
                        blocked=decision.action=='block';reason=decision.reason
                        guard_ms=decision.latency_ms;verdict=decision.classifier_output
                    else:
                        shown=visible.text;blocked=False;reason='guard_disabled';guard_ms=0.0;verdict=''
                    rec=dict(id=rid,case_id=case['id'],kind=case['kind'],category=case['category'],
                        goal_id=case.get('goal_id',case['id']),variant=case.get('variant','original'),split=case.get('split','unspecified'),
                        seed=seed,generation_seed=generation_seed,config=config,evidence=manifest['evidence'],
                        prompt=prompt,goal=case.get('goal',case['prompt']),completion=completion,
                        raw_answer=visible.text,delivered=shown,truncated=completion['truncated'],
                        incomplete_reasoning=visible.incomplete_reasoning,guard_applied=applied,
                        blocked=blocked,guard_reason=reason,guard_output=verdict,guard_ms=guard_ms,
                        total_ms=completion['latency_ms']+guard_ms,generation_error=error,
                        auto_non_refusal_flag=bool(shown) and not refusal_flag(shown),
                        source_record_id=source['id'] if applied else None)
                    append(log,rec);seen.add(rid);cache[(case['id'],seed,config)]=rec
                    print(f"{len(seen)}/{manifest['expected_rows']} {config} {case['id']} seed={seed}",flush=True)
        manifest['status']='SMOKE_COMPLETE' if args.backend=='mock' else 'GENERATION_COMPLETE_REVIEW_REQUIRED'
        manifest['actual_rows']=len(seen)
    except BaseException as exc:
        manifest['status']='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED'
        manifest['error']=type(exc).__name__+': '+str(exc)[:500]
        raise
    finally:
        atomic_json(old,manifest)
        try:
            (out/'environment.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
        except Exception:pass
    print(json.dumps({'out':str(out),'status':manifest['status'],'rows':len(seen)}))
if __name__=='__main__':main()
