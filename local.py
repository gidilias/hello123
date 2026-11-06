"""Cross-platform local command entrypoint. No Colab dependency."""
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('mode',choices=['check','smoke','pilot','main','review','report']);p.add_argument('--device',choices=['cuda','cpu'],default='cuda');p.add_argument('--out');p.add_argument('--cases',default='data/heldout.jsonl');p.add_argument('--reviewer',default='reviewer1');p.add_argument('--guard',choices=['qwen','llama'],default='qwen');p.add_argument('--guard-device',choices=['cuda','cpu']);a=p.parse_args()
def run(*args):subprocess.run([sys.executable,*args],cwd=ROOT,check=True)
out=a.out or ('runs/'+a.mode)
if a.mode=='check':
 print('Python:',sys.version)
 try:
  import torch
  print('CUDA:',torch.cuda.is_available())
  if torch.cuda.is_available():print(torch.cuda.get_device_name(0),torch.cuda.get_device_properties(0).total_memory//2**20,'MiB VRAM')
 except ImportError:print('Install requirements.txt before real runs.')
 run('-m','unittest','discover','-s','tests','-v')
elif a.mode in ['smoke','pilot','main']:
 args=['experiment.py','--backend','mock' if a.mode=='smoke' else 'hf','--ablation','--device',a.device,'--out',out,'--cases','data/smoke_cases.jsonl' if a.mode=='smoke' else a.cases,'--seeds','42,43,44' if a.mode=='main' else '42']
 args+=['--guard',a.guard]
 if a.guard_device:args+=['--guard-device',a.guard_device]
 if a.mode=='pilot':args+=['--limit','2']
 run(*args)
elif a.mode=='review':
 if not a.out:p.error('--out must identify an existing run')
 run('scripts/review.py',out,'--reviewer',a.reviewer)
elif a.mode=='report':
 if not a.out:p.error('--out must identify an existing run')
 run('scripts/summarize.py',out,'--reviewer',a.reviewer)
 run('scripts/analyze_advanced.py',out,'--reviewer',a.reviewer)
 print('Open',str(ROOT/out/'dashboard.html'))
