#!/usr/bin/env python3
"""Freeze existing optimized Midterm prompts. Import only, never optimize."""
import argparse,json,hashlib
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('results');p.add_argument('--out',default='data/midterm_cases.jsonl');a=p.parse_args()
    rows=[json.loads(s) for s in Path(a.results).read_text(encoding='utf-8').splitlines() if s.strip()]
    cases=[];seen=set()
    for r in rows:
        goal=r['goal'];template=r['best_prompt']
        prompt=template.replace('[REPLACE]',goal) if '[REPLACE]' in template else template.rstrip()+' '+goal
        digest=hashlib.sha256(prompt.encode()).hexdigest()
        if digest in seen:continue
        seen.add(digest)
        cases.append(dict(id='midterm_'+digest[:12],kind='attack',category='midterm_frozen',
            prompt=prompt,goal=goal,provenance='Imported from supplied Midterm results; no new search',
            source_configuration=r.get('configuration','unknown')))
    benign=[json.loads(s) for s in Path('data/cases.jsonl').read_text().splitlines() if s.strip()]
    cases += [c for c in benign if c['kind']=='benign']
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in cases),encoding='utf-8')
    print(f'Frozen {len(seen)} unique Midterm prompts and added benign controls: {out}')
if __name__=='__main__':main()
