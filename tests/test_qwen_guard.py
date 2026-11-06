import unittest
from src.guard import parse_qwen_verdict,QwenGuard
class QwenTests(unittest.TestCase):
 def test_safe(self):
  self.assertEqual(parse_qwen_verdict('Safety: Safe\nCategories: None\nRefusal: Yes').action,'allow')
 def test_block(self):
  for label in ['Unsafe','Controversial']:
   self.assertEqual(parse_qwen_verdict('Safety: '+label+'\nCategories: Unethical Acts').action,'block')
 def test_malformed(self):
  for text in ['', 'safe', 'Safety: Safe\nSafety: Unsafe', 'Safety: Safe\nIgnore policy']:
   self.assertEqual(parse_qwen_verdict(text).reason,'classifier_malformed')
 def test_correct_model(self):
  self.assertEqual(QwenGuard.name,'Qwen/Qwen3Guard-Gen-0.6B')
