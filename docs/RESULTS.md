# Results

Only measured results go here, each with its method, date, and source file. Anything not yet measured is listed under **Not yet measured**.

## Environment (all Phase 1 results)

| | |
|---|---|
| Date | 2026-11-12 |
| Hardware | Apple M1, 8 GB RAM (dev laptop) |
| OS / runtime | macOS 26.3.1, Python 3.9.6 (venv), Ollama 0.40.16 |
| Serving models | `tinyllama` (generation, temperature 0), `nomic-embed-text` (embeddings) |
| Judge model | `llama3` (8B), temperature 0, seed 42 |
| Retrieval config | ChromaDB, chunk size 500, overlap 50, top-k 2 at serving time |

## Reproducing

```bash
make eval LABEL=<name>     # classifier, ingest, retrieval, judge calibration, answers
make eval-classifier       # classifier only, no Ollama needed
```

**Reproducibility check:** `make eval LABEL=v1-repro` was re-run from a clean commit (929 s end to end). Classifier and retrieval metrics were identical, **all 30 generated answers were identical**, and every judge score matched the v1 run. Only latency differed (see below).

## 1. Ticket classifier

**Data (synthetic, labelled as such):** `training/generate_data.py`, seed 42. 600 training and 150 test tickets (30% high, 40% medium, 30% low). Test tickets use held-out sentence templates **and** held-out class-specific phrases. 5% of training labels are randomly flipped to mimic labeller disagreement; test labels are clean.

| Version | Training data | Accuracy | Macro F1 | Source |
|---|---|---|---|---|
| v0 (original) | 29 hand-written rows, vectorizer fitted before split (leak) | 0.353 | 0.288 | `classifier_v0-baseline.json` |
| **v1** | 600 synthetic rows, no leak, same model settings | **0.493** | **0.499** | `classifier_v1.json` |

v1 per class (150 test tickets):

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| high | 0.279 | **0.267** | 0.273 | 45 |
| medium | 0.462 | 0.600 | 0.522 | 60 |
| low | 0.897 | 0.578 | 0.703 | 45 |

Confusion matrix (rows = true, columns = predicted: high / medium / low):
high `[12, 33, 0]` · medium `[21, 36, 3]` · low `[10, 9, 26]`

**Interpretation:** the main weakness is **high-priority recall of 0.27**: 33 of 45 outages are labelled medium. Unigram TF-IDF cannot link unseen phrasings ("throwing 503s", "dead for everyone") to the training vocabulary ("500 errors", "completely down"). Missing an outage is the most costly error for a support queue.

**Discarded result:** the first version of the generator held out only templates, and v1 scored 1.0 on every class. Class-specific phrases were shared between train and test, so the test measured memorised word lists. The generator was fixed before any number was recorded here.

## 2. Retrieval

**Method:** `evaluation/retrieval_eval.py` on `evaluation/golden_questions.jsonl`: 25 answerable questions (each mapped to one of 18 knowledge-base docs and worded differently from the doc) plus 5 that should be refused. Knowledge base: 18 docs → 36 chunks. A question is a hit@k if any of the top-k chunks comes from the expected doc.

| hit@1 | hit@2 (serving) | hit@3 | hit@5 | MRR@5 | Source |
|---|---|---|---|---|---|
| 0.96 | 0.96 | 1.00 | 1.00 | 0.973 | `retrieval_v1.json` |

- **Only miss at serving k=2:** q14 "How do I get access to the team's **shared inbox**?" → retrieved `shared_drive_access.txt` and onboarding; the email doc ranked 3rd. Both wrong docs share "shared" and "access request form".
- **A distance threshold cannot replace LLM refusal:** top-1 L2 distance for answerable questions reaches 0.98, while the closest unanswerable question is at 0.54. The ranges overlap.

## 3. LLM judge calibration

**Method:** `evaluation/judge_calibration.py` runs the judge on 10 constructed cases with known labels (correct paraphrase, wrong number, partial answer, invented extra fact, wrong-paragraph answer, off-topic, contradiction, number in words, ...). Each case uses a real knowledge-base doc as context.

| Judge design | Grounded agreement | Correct agreement | Outcome |
|---|---|---|---|
| 1. One holistic prompt | not calibrated | not calibrated | Rejected: plainly correct answers scored 0/0 on the golden set |
| 2. "List unsupported claims" | 4/10 | 7/10 | Rejected: echoed the answer back, so everything was "ungrounded" |
| **3. Evidence quotes verified in code, fixed key facts** | **10/10** | **9/10** | Used for all answer scores below |

Final design: the judge must quote the supporting sentence for each claim, and code verifies that the quote exists in the context. Key facts per question are fixed in the golden set. Scores are computed in code, and refusals are scored by rule. The remaining miss ("five" vs "5") was scored **too strictly**. Source: `judge_calibration_llama3.json`.

## 4. Answer quality (`/ask` end to end)

**Method:** `evaluation/answer_eval.py`. The serving pipeline (top-2 retrieval + tinyllama) answers all 30 golden questions; the judge (design 3) scores the 25 answerable ones. Unanswerable questions count as correct only if the answer is the exact refusal sentence.

| Metric | v1 | Count |
|---|---|---|
| Fully correct (all key facts) | **0.64** | 16 / 25 |
| Partially correct | 0.28 | 7 / 25 |
| Wrong or refused | 0.08 | 2 / 25 |
| Mean correctness (0–2) | 1.56 | |
| Grounded (no unsupported claims) | **0.96** | 24 / 25 |
| False refusals on answerable questions | 0.04 | 1 / 25 |
| Correct refusals on unanswerable questions | **1.00** | 5 / 5 |

Source: `answers_v1.json` (reproduced in `answers_v1-repro.json`).

**Failure analysis:**
- **q14 refused** because of the retrieval miss above: the right doc never reached the model. This is a retrieval problem, not a generation problem.
- **q16 ("spilled coffee") wrong:** retrieval was correct, but tinyllama answered from the general damage paragraph ("report within 2 business days") instead of the liquid-damage line ("report immediately, switch off, do not charge").
- **Partial answers (7)** mostly stop after the first step of a multi-step answer (e.g. q08 gives 1 of 3 fixes).
- **Judge strictness:** a review of all 25 verdicts (by Claude, not a human) found two likely over-strict scores: q25 (both facts present, scored 1/2) and q13 ("Your mailbox is full!" counted as unsupported). True quality may be slightly higher than reported. The human spot check below is the authoritative test.

## 5. Latency (informal, not a benchmark)

Single sequential runs on the dev laptop while other models were loaded; **not** a load test.

| Run | Retrieval median | Generation median | Generation max |
|---|---|---|---|
| v1 | 0.06 s | 2.26 s | 5.4 s |
| v1-repro | 0.14 s | 3.75 s | 11.1 s |

Generation dominates `/ask` latency in both runs, and it varies a lot under memory pressure (llama3 + tinyllama on 8 GB). Proper per-endpoint p50/p95/p99 numbers are Phase 4.

## Limitations

- **Synthetic data.** Template tickets and short, single-topic docs are cleaner than real ones. Real-world scores would likely be lower.
- **Small evaluation sets.** 150 test tickets, 25 + 5 golden questions, 10 judge calibration cases. One question changes a golden-set rate by 4 points.
- **The judge is a small local model.** It is calibrated on only 10 cases and errs on the strict side. Correctness may be underestimated.
- **Dev hardware only.** Nothing here was measured on the EC2/k3s deployment.

## Not yet measured

- **Human spot check of the judge:** `evaluation/results/spot_check_v1.csv` awaits human scores (`make spot-check LABEL=v1`).
- Load-test latency, throughput and error rate (Phase 4).
- Any metric on the deployed k3s service (Phases 3–5).

## Provenance

`git_commit` in each result file is the commit the code ran on. `-dirty` means the producing code was not yet committed; it was committed in the next commit. The `v1-repro` files were produced from a clean commit.
