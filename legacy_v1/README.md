# BreakPoint AI / Assignment 3

A standalone continuation of the supplied DeepSeek / AutoDAN Midterm. This extension replays fixed prompts and adds Llama Guard 3-1B output gating. Keep the existing AutoDAN optimizer in your original repository. Copy this folder beside it or run it independently. The complete GitHub source was not available, so this is not a verified patch of that repository.

## Evidence status

No new GPU experiment has been executed. The supplied PDFs describe a historical 16-record pilot with provisional AI-assisted labels. The supplied Colab notebook contains an interrupted HF attempt without completed result records. `evidence/smoke/` contains synthetic software checks only. The report and presentation are drafts with new empirical results pending. Real measurements and independent review are required before submission.

## Start without GPU

Python 3.10+. The smoke, review and summary scripts use only the standard library.

```bash
python -m unittest discover -s tests -v
python experiment.py --backend mock --cases data/smoke_cases.jsonl --seeds 42 --out runs/smoke
python scripts/review.py runs/smoke
python scripts/summarize.py runs/smoke
```

Open `runs/smoke/dashboard.html`. Mock outputs do not establish model safety.

## Real experiment

Use `Run_Assignment3.ipynb` in a Colab GPU runtime, or install locally:

```bash
python -m pip install -r requirements.txt
```

First request access and accept the license at https://huggingface.co/meta-llama/Llama-Guard-3-1B . Authenticate with `huggingface_hub.login()` or private `HF_TOKEN`. Never save tokens in notebooks or Git. The code never substitutes mock when a real model fails to load.

```bash
python experiment.py --backend hf --seeds 42 --limit 1 --out runs/gpu_check
python experiment.py --backend hf --seeds 42,43,44 --out runs/main
python scripts/review.py runs/main --reviewer reviewer1
python scripts/review.py runs/main --reviewer reviewer2
```

The default 24 cases comprise 8 attack-category examples and 16 benign controls. Three seeds produce 216 A/B/C records, using 144 target generations and up to 72 guard checks. B/C reuse exactly the same target completion to isolate the output gate, including abstention on incomplete answers. The short GPU check tests infrastructure, not scientific performance. Latency excludes model loading/downloads but includes cold inference because no warmup exclusion is applied.

## Reuse actual Midterm optimized prompts (recommended)

```bash
python scripts/import_midterm.py /path/to/midterm/results.jsonl --out data/midterm_cases.jsonl
python experiment.py --backend hf --cases data/midterm_cases.jsonl --seeds 42,43,44 --out runs/midterm_replay
```

The importer reads `goal`, `best_prompt`, `configuration` from the pasted Midterm schema, renders placeholders, deduplicates identical prompts and adds benign controls. Different prompts from the two old configurations remain separate cases. It does not optimize new attacks. Default examples cover the same categories but are not the old optimized prompts. Import actual records before claiming robustness to the Midterm attacks.

## Resume and reproducibility

Repeat the same command with the same `--out`. Every result is appended, flushed and synced. Manifest fingerprints reject changed code, corpus or settings. Only a broken final append is repaired. Use one process per output directory. Generation failures remain explicit records, not successful responses or silent retries. A deliberate retry requires a new output directory and documented protocol.

The manifest records full cases, prefix, sampling settings, seeds, resolved model revisions, device, dtype and code fingerprint. `environment.txt` records installed packages. Pin resolved SHAs with `--model-revision SHA --guard-revision SHA` in a fresh directory and retain the exact code/environment for reproduction. Floating model revision changes reject resume. Hardware/library changes can affect outputs despite seeds. CUDA is required by default; CPU requires explicit `--device cpu` and may be very slow.

The target uses temperature 0.6, top_p 0.95 and max_new_tokens=1536. The Midterm cap was 768. All new A/B/C runs use the same cap. Historical vs new rates are not a controlled before/after comparison. The prefix remains in the user message as in the supplied code. The guard sees the complete augmented prompt and visible final answer. Unsafe/malformed classifications, errors, guard context overflow and incomplete/missing final answers block delivery. Model context overflow never silently truncates input.

## Review and final materials

Follow `docs/ANNOTATION.md`. Review every answer, including automatic refusals, using full text in `review.html`. Edit `annotations.csv` without changing ticket IDs. Reviewers see goal, response, kind and truncation, but not config or guard decision. Hide `mapping.json` until review ends. Two reviewers work independently. Keep both original CSVs and adjudicate disagreements in a third review folder (copy one folder, update its CSV using the same tickets). Some answers can remain ambiguous.

```bash
python scripts/summarize.py runs/main --reviewer reviewer1
python scripts/build_report.py --run runs/main --out deliverables/Assignment3_Report.pdf
```

Summary outputs: JSON, comparison table and offline dashboard. Missing/ambiguous labels remain unresolved. Confirmed rates are lower bounds until all outcomes resolve. Output-gate FPR/recall use independent safety labels for raw C answers and include classifier and availability decisions. Benign block rate instead uses all benign trials as its denominator. Resolved paired B/C transitions are recorded. Wilson intervals are descriptive per-output intervals: repeated seeds share goals, so stronger inference needs per-goal analysis.

## Contents

- `deliverables/Assignment3_Report_Draft.pdf`: three-page English methodology/report draft.
- Editable slides: https://chatgpt.com/space/page_0d49fa072ac881a4b7f0477bf1732565
- `docs/SLIDES.json`: slide text and English presenter notes.
- `docs/DEFENSE_RU.md`: Russian startup and defense notes.
- `docs/AI_USE_DECLARATION.md`: contribution disclosure.
- `Run_Assignment3.ipynb`: Colab workflow, no saved outputs.
- `src/`, `scripts/`, `tests/`: implementation, review, reporting and verification.

The offline dashboard explains gating via records and reason codes. It does not explain the internal causes of model generation. Raw research responses should not appear in the ordinary user interface.

## References

AutoDAN: https://arxiv.org/abs/2310.04451
DeepSeek: https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
Guard/license: https://huggingface.co/meta-llama/Llama-Guard-3-1B
Historical evidence: student-supplied Midterm report and slides, October 2026.
