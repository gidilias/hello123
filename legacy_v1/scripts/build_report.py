#!/usr/bin/env python3
"""Generate a three-page English report from measured, reviewed records."""
import argparse,json,html
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4

NAVY=colors.HexColor('#14283f');TEAL=colors.HexColor('#087f8c');MUTED=colors.HexColor('#536276')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='ReportTitle',fontName='Helvetica-Bold',fontSize=23,leading=27,textColor=NAVY,spaceAfter=9))
styles.add(ParagraphStyle(name='SectionTitle',fontName='Helvetica-Bold',fontSize=11.5,leading=14,textColor=TEAL,spaceBefore=12,spaceAfter=5))
styles.add(ParagraphStyle(name='ReportBody',fontName='Helvetica',fontSize=9.7,leading=13.5,textColor=NAVY,spaceAfter=6))
styles.add(ParagraphStyle(name='CaptionX',fontSize=8.1,leading=11,textColor=MUTED,spaceAfter=6))
styles.add(ParagraphStyle(name='TableX',fontSize=8.5,leading=11,textColor=NAVY))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run');ap.add_argument('--out',default='deliverables/Assignment3_Report_Draft.pdf');a=ap.parse_args()
 summary=None
 if a.run:
  summary=json.loads((Path(a.run)/'summary.json').read_text())
  if summary['evidence']!='HF_RUN':raise SystemExit('Refusing to put mock metrics into an empirical report.')
 out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
 story=[]
 def para(t,style='ReportBody'):return Paragraph(t,styles[style])
 def add(t,style='ReportBody'):story.append(para(t,style))
 def section(title,text):add(title,'SectionTitle');add(text)
 def table(rows,widths):
  data=[[para(html.escape(str(c)),'TableX') for c in r] for r in rows]
  t=Table(data,colWidths=widths,hAlign='LEFT')
  t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9f1f4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),1,TEAL),('LINEBELOW',(0,1),(-1,-1),0.35,colors.HexColor('#d1dce3'))]))
  story.append(t);story.append(Spacer(1,7))
 add('BreakPoint AI','ReportTitle')
 add('Output safety gating for a small reasoning model','SectionTitle')
 add('Assignment 3 / AISRA1301 / Qazaq AI Research University / October 2026','CaptionX')
 if summary:
  status='REAL MODEL RECORDS LOADED / REVIEW STATUS: '+('all delivered outcomes resolved' if summary['all_delivered_resolved'] else 'incomplete or ambiguous')
 else:status='RESEARCH DRAFT / NEW GPU EXPERIMENT AND INDEPENDENT REVIEW PENDING'
 add(status,'CaptionX')
 section('1. Research objective',
 'This study continues the Midterm DeepSeek-R1-Distill-Qwen-1.5B testbed and its AutoDAN-inspired jailbreak evaluation [1,2]. It asks whether an additional output gate reduces unsafe answers delivered to users beyond a prompt-level safety prefix. The hypothesis is a lower delivered attack-success fraction, with potential losses in legitimate-task utility and increased response latency. No improvement is assumed in advance.')
 section('2. Midterm baseline and identified risk',
 'The student-supplied Midterm report describes eight goals tested in two configurations on a Tesla T4. The pipeline combined an affirmative-target likelihood objective, a keyword refusal detector, perplexity scoring and an offline dashboard. The detector flagged every response. Provisional AI-assisted review produced the counts below, with four ambiguous outputs per configuration. These labels are historical evidence, not independent human ground truth.')
 table([['Historical Midterm metric','No prefix','Safety prefix'],['Automatic detector flags','8/8','8/8'],['Provisional confirmed successes','4/8 (50.0%)','1/8 (12.5%)'],['Ambiguous / incomplete outputs','4/8','4/8'],['Mean model queries','81.25','121.88']], [254,115,115])
 add('Source: supplied Midterm report, October 2026. Query counts describe attack search cost. They are not response latency. Historical percentages do not measure the new guard.','CaptionX')
 section('3. Extended testing methodology',
 'The main experiment replays a fixed corpus in A (baseline), B (safety prefix) and C (prefix plus output gate). The importer freezes actual best_prompt records from the Midterm, deduplicates exact rendered prompts and retains source provenance. A built-in fallback corpus covers the same eight risk categories, but contains new examples rather than the original optimized attacks. Sixteen legitimate requests test utility and excessive blocking. Three seeds repeat each case. B and C share each target completion to isolate the added output gate. Adaptive attacker robustness remains outside this experiment.')
 story.append(PageBreak())
 add('Mechanism and experimental comparison','ReportTitle')
 section('4. Additional safety mechanism',
 'Configuration C runs Llama Guard 3-1B on the conversation ending with the visible assistant answer [3]. A safe classification permits delivery. An unsafe or malformed classification triggers a neutral fallback. The gate also withholds truncated or missing final answers and blocks on classifier errors or context overflow. These actions reduce exposure by abstention, so the analysis must also measure lost utility. Guard reason codes and classifier output are stored separately from evaluation labels. Model access and its license are prerequisites, with no automatic mock substitution.')
 section('5. Setup and evaluation metrics',
 'The target remains DeepSeek-R1-Distill-Qwen-1.5B. The new protocol uses temperature 0.6, top_p 0.95 and a 1536-token cap, shared by A/B/C. The Midterm used 768 tokens, so new rates require a fresh concurrent baseline. Seeds derive independently from case IDs. The manifest records source fingerprints, cases, prefix, resolved model revisions, dtype and environment. Response timing excludes downloads and loading, but has no warmup exclusion. Per-record writes and compatible resume support recovery from interruption.')
 add('Delivered ASR is substantive unsafe-goal fulfillment divided by attack trials. Benign utility measures correct useful task completion. Additional measures include benign block rate, guard false-positive rate on independently safe raw answers, recall on unsafe raw answers, latency, generation errors and incomplete-output rate. Missing/ambiguous labels remain unresolved. Confirmed success is a lower bound, and the upper bound includes unresolved cases. Wilson intervals are descriptive because seed repeats share goals.')
 section('6. Results and comparative analysis',
 'The following table separates empirical evidence from unexecuted work. Independent reviewers must label all answers, including automatic refusals. The review queue hides configuration and guard decisions and displays complete text. A second review and documented adjudication strengthen validity. The guard never serves as its own ground-truth evaluator.')
 def pct(obj):
  if 'confirmed' in obj:
   if obj['reviewed']==0:return 'Not evaluated'
   metric=obj['confirmed']
  else:metric=obj
  if metric['value'] is None:return 'Not evaluated'
  return f"{metric['k']}/{metric['n']} ({metric['value']*100:.1f}%)"
 rows=[['New experiment metric','A: baseline','B: prefix','C: prefix + gate']]
 if not summary:
  for name in ['Delivered confirmed ASR','Benign task success','Benign block rate','Mean response latency']:
   rows.append([name,'Pending','Pending','Pending'])
 else:
  configs=[summary[x] for x in ['A_baseline','B_prefix','C_prefix_guard']]
  rows += [['Delivered confirmed ASR']+[pct(s['attack']) for s in configs],
           ['Unresolved attack trials']+[str(s['attack']['unresolved']) for s in configs],
           ['Benign task success']+[pct(s['utility']) for s in configs],
           ['Benign block rate']+[pct(s['benign_block_rate']) for s in configs],
           ['Mean response latency']+[f"{s['mean_latency_ms']:.1f} ms" if s['mean_latency_ms'] is not None else 'N/A' for s in configs]]
 table(rows,[167,105,105,107])
 add('Evidence status: no new GPU run during package preparation. Synthetic smoke checks validate software execution only. A real run and completed independent review are necessary for a safety conclusion.' if not summary else 'Evidence: '+summary['run_status']+'. Review: '+summary['reviewer']+'. Unresolved outcomes prevent a final binary ASR claim. See summary.json for bounds and review counts.','CaptionX')
 story.append(PageBreak())
 add('Reliability, users and research limits','ReportTitle')
 section('7. Interpretability and availability analysis',
 'The trace links the request, original visible answer, guard verdict, blocking reason and delivered response. This explains the gating action, not the causal internal behavior of either model. No separate SHAP/LIME experiment is claimed because the study evaluates text generation and a discrete output gate rather than a tabular predictor. Independent response analysis and operational traces address observability at this scope. Additional model-level interpretability remains future work.')
 add('Generation records include input/output token counts, finish reason, output-limit status and failures. Extraction handles complete reasoning blocks, unfinished blocks and a closing tag emitted after a template-supplied opening tag. Incomplete visible answers remain explicit evidence. Block-on-error behavior limits exposure but can reduce availability. The same generation cap applies to every new configuration. Persisted records and settings/revision checks support recovery without silently changing experimental conditions.')
 section('8. Safe human-AI interaction',
 'The user-facing fallback explains that the answer was withheld and invites a safer reformulation. It also recommends human review for important decisions. Users should see system limitations and should not infer factual correctness from a safe label. Raw flagged responses remain in restricted research logs, while the ordinary flow shows only the delivered answer. The offline dashboard supports investigator review and is not a public attack service. No tool execution or sensitive autonomous actions are part of this prototype.')
 section('9. Limitations and future work',
 'A single small target model and a limited corpus cannot establish general safety. The guard taxonomy only partially covers the research categories, especially fake reviews, ordinary insults and misinformation. The classifier itself can make mistakes or face prompt injection. Fixed-prompt replay does not evaluate adaptive evasion. Longer outputs change cost and may still truncate. Repeated seeds are correlated within goals, and reviewer disagreement must be reported. Future work includes held-out goals, per-category and per-goal analysis, independently adjudicated labels, availability stress tests and a separate adaptive evaluation. None of those results are claimed here.')
 section('10. References',
 '[1] Liu, X., Xu, N., Chen, M., and Xiao, C. AutoDAN: Generating Stealthy Jailbreak Prompts on Aligned Large Language Models. ICLR 2024. arxiv.org/abs/2310.04451.<br/>'
 '[2] DeepSeek AI. DeepSeek-R1-Distill-Qwen-1.5B model card. huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B.<br/>'
 '[3] Meta. Llama Guard 3-1B model card and usage instructions. huggingface.co/meta-llama/Llama-Guard-3-1B.<br/>'
 '[4] Student-provided BreakPoint AI Midterm research report and presentation, October 2026.')
 add('AI use declaration: AI assisted the evaluation extension, tests, documentation, report and slides. Real-model execution and independent human review were not performed during preparation. The student must verify and update the final evidence and disclosure.','CaptionX')
 def footer(canvas,doc):
  canvas.setStrokeColor(TEAL);canvas.line(40,40,A4[0]-40,40)
  canvas.setFont('Helvetica',8);canvas.setFillColor(MUTED)
  canvas.drawString(40,26,'BreakPoint AI / AISRA1301 / Assignment 3')
  canvas.drawRightString(A4[0]-40,26,str(doc.page))
 doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=54,title='BreakPoint AI - Assignment 3',author='BreakPoint AI research project')
 doc.build(story,onFirstPage=footer,onLaterPages=footer)
 print(out)
if __name__=='__main__':main()
