#!/usr/bin/env python3
import argparse,csv,json,sys,html
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.metrics import summarize

def read_annotations(run,reviewer):
    root=run/reviewer
    if not (root/'annotations.csv').exists():return {}
    mapping=json.loads((root/'mapping.json').read_text());out={}
    with (root/'annotations.csv').open(newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            m=mapping[r['ticket']]
            if r['label'] not in ('','success','failure','ambiguous'):raise ValueError('Invalid task label: '+r['ticket'])
            if r['safety'] not in ('','safe','unsafe','ambiguous'):raise ValueError('Invalid safety label: '+r['ticket'])
            key=(m['id'],m['surface'])
            if key in out:raise ValueError('Duplicate annotation')
            out[key]=r
    return out

def rate(p):
    return 'Not evaluated' if p['value'] is None else f"{p['k']}/{p['n']} ({100*p['value']:.1f}%)"

def task_rate(obj):
    if obj['reviewed']==0:return 'Not evaluated'
    return rate(obj['confirmed'])+(' [lower bound]' if obj['unresolved'] else '')

def main():
    p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('--reviewer',default='reviewer1');a=p.parse_args()
    run=Path(a.run);manifest=json.loads((run/'manifest.json').read_text())
    rows=[json.loads(s) for s in (run/'results.jsonl').read_text().splitlines() if s.strip()]
    ann=read_annotations(run,a.reviewer);result=summarize(rows,ann)
    result['evidence']=manifest['evidence'];result['run_status']=manifest['status']
    result['reviewer']=a.reviewer;result['run_hash']=manifest['run_hash']
    result['all_delivered_resolved']=bool(rows) and all(ann.get((r['id'],'delivered'),{}).get('label') in ('success','failure') for r in rows)
    (run/'summary.json').write_text(json.dumps(result,indent=2))
    lines=['# '+manifest['evidence']+' / '+manifest['status'],
        '', 'Confirmed rates are lower bounds when any outcomes remain unresolved.',
        'Wilson intervals describe per-output proportions; repeated seeds share goals.', '',
        '|Configuration|Attack confirmed|Unresolved attacks|Benign task success|Benign blocked|Mean total ms|',
        '|---|---|---|---|---|---|']
    for cfg in ('A_baseline','B_prefix','C_prefix_guard','D_guard_only'):
        s=result[cfg];lat=s['mean_latency_ms']
        lines.append('|'+ '|'.join([cfg,task_rate(s['attack']),str(s['attack']['unresolved']),
            task_rate(s['utility']),rate(s['benign_block_rate']),f'{lat:.1f}' if lat is not None else 'N/A'])+'|')
    (run/'comparison.md').write_text('\n'.join(lines)+'\n')
    # Read-only offline dashboard. Raw records stay in restricted local evidence.
    content=['<!doctype html><meta charset="utf-8"><title>BreakPoint AI</title><style>body{font:17px system-ui;margin:40px;max-width:1400px}table{border-collapse:collapse;width:100%}td,th{padding:12px;border-bottom:1px solid #ccc;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer;padding:14px;background:#eef3f7}article{margin:20px 0}</style>',
        '<h1>BreakPoint AI / Assignment 3</h1><p>'+html.escape(manifest['evidence']+' / '+manifest['status'])+'</p>',
        '<p>Safety checks can make mistakes. Missing labels are unresolved. This is an offline research dashboard.</p>',
        '<pre>'+html.escape('\n'.join(lines))+'</pre>']
    for r in rows:
        content.append('<article><details><summary>'+html.escape(r['config']+' / '+r['case_id']+' / '+r['guard_reason'])+'</summary><h3>Request</h3><pre>'+html.escape(r['prompt'])+'</pre><h3>Original visible answer</h3><pre>'+html.escape(r['raw_answer'])+'</pre><h3>Delivered answer</h3><pre>'+html.escape(r['delivered'])+'</pre></details></article>')
    (run/'dashboard.html').write_text(''.join(content),encoding='utf-8')
    print('\n'.join(lines))
if __name__=='__main__':main()
