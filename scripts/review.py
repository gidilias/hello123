#!/usr/bin/env python3
"""Blinded, complete-answer review. Review files never alter model evidence."""
import argparse,csv,json,random,hashlib,html,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def main():
    p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('--reviewer',default='reviewer1');a=p.parse_args()
    folder=Path(a.run);records=[json.loads(s) for s in (folder/'results.jsonl').read_text().splitlines() if s.strip()]
    rows=[];mapping={}
    for r in records:
        for surface in ('raw','delivered'):
            ticket=hashlib.sha256((a.reviewer+r['id']+surface).encode()).hexdigest()[:20]
            mapping[ticket]={'id':r['id'],'surface':surface}
            rows.append(dict(ticket=ticket,kind=r['kind'],goal=r['goal'],
                answer=r['raw_answer'] if surface=='raw' else r['delivered'],
                truncated=str(r['truncated'] if surface=='raw' or not r['blocked'] else False),
                label='',safety='',notes=''))
    random.Random(719).shuffle(rows)
    dest=folder/a.reviewer;dest.mkdir(exist_ok=True)
    file=dest/'annotations.csv'
    if file.exists():raise SystemExit('Review exists. Choose another --reviewer; existing work is preserved.')
    with file.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['ticket','kind','goal','answer','truncated','label','safety','notes']);writer.writeheader();writer.writerows(rows)
    (dest/'mapping.json').write_text(json.dumps(mapping,indent=2))
    cards=[]
    for r in rows:
        cards.append('<article><h2>'+html.escape(r['ticket'])+'</h2><p>'+html.escape(r['kind']+' | '+r['goal'])+'</p><pre>'+html.escape(r['answer'])+'</pre><p>Truncated: '+r['truncated']+'</p></article>')
    (dest/'review.html').write_text('<!doctype html><meta charset="utf-8"><title>Blinded response review</title><style>body{font:17px system-ui;max-width:1000px;margin:40px auto}article{border-bottom:1px solid #aaa;padding:20px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Complete responses</h1><p>Enter labels in annotations.csv. Keep mapping.json hidden until review is complete. Labels: success, failure, ambiguous. Safety: safe, unsafe, ambiguous.</p>'+''.join(cards),encoding='utf-8')
    print(file)
if __name__=='__main__':main()
