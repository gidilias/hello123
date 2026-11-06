import unittest,json,tempfile,subprocess,sys
from pathlib import Path
from scripts.analyze_advanced import bootstrap
class AdvancedTests(unittest.TestCase):
 def test_corpus_groups_do_not_cross_splits(self):
  rows=[json.loads(x) for x in Path('data/expanded.jsonl').read_text().splitlines()]
  self.assertEqual(len(rows),256);self.assertEqual(len({r['id'] for r in rows}),256)
  groups={}
  for r in rows:groups.setdefault(r['goal_id'],set()).add(r['split'])
  self.assertEqual(len(groups),40);self.assertTrue(all(len(v)==1 for v in groups.values()))
 def test_cluster_interval(self):
  self.assertEqual(bootstrap([-1,-1,-1])['ci95'],[-1,-1])
  self.assertIsNone(bootstrap([])['ci95'])
 def test_ablation_preserves_shared_completions(self):
  with tempfile.TemporaryDirectory() as t:
   subprocess.run([sys.executable,'experiment.py','--backend','mock','--cases','data/smoke_cases.jsonl','--seeds','42','--ablation','--out',t],check=True,capture_output=True)
   rows=[json.loads(x) for x in (Path(t)/'results.jsonl').read_text().splitlines()]
   self.assertEqual(len(rows),8)
   for c in {r['case_id'] for r in rows}:
    group={r['config']:r for r in rows if r['case_id']==c}
    self.assertEqual(group['A_baseline']['completion'],group['D_guard_only']['completion'])
    self.assertEqual(group['B_prefix']['completion'],group['C_prefix_guard']['completion'])
    self.assertEqual(group['A_baseline']['prompt'],group['D_guard_only']['prompt'])
