# AI Resume Screening & Ranking System

A small, explainable Python CLI that processes a directory of resumes, applies hard Python + AI eligibility gates, ranks eligible candidates out of 100, and optionally enriches scores with public GitHub repository signals.

## Features
- PDF required; DOCX and TXT supported.
- Batch processing with per-file failure isolation.
- Hard eligibility filter: both Python evidence and AI/LLM/agentic evidence are required.
- Deterministic, explainable 100-point scoring.
- Optional public GitHub enrichment; failures never stop the batch.
- JSON output containing eligible and rejected candidates, score breakdowns, evidence, and batch statistics.
- Unit tests for eligibility and score invariants.

## Requirements
Python 3.10+ recommended.

## Setup
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

## Run against the supplied dataset
```bash
python main.py --input ./resumes --output ./output/results.json
```
The repository includes the supplied `resumes/` dataset and a generated `output/results.json` from the current run. To screen a different directory, pass its path to `--input`.

## Optional GitHub token
Copy `.env.example` to `.env` and set `GITHUB_TOKEN` if desired. The app does not automatically load `.env`; export the variable in your shell or use your preferred environment-variable loader. Never commit real tokens. Unauthenticated public API requests may be rate-limited.

## Tests
```bash
python -m unittest discover -s tests -v
```

## Scoring model (100 points)
| Category | Maximum | Signals |
|---|---:|---|
| AI / Agentic / RAG project depth | 40 | Evidence in project section for retrieval, agents, tools, orchestration, evaluation, embeddings, and related workflows |
| Python & backend engineering | 30 | Python evidence plus API/backend, async, SQL, Redis, testing, and backend frameworks |
| Cloud / deployment / full stack | 15 | Docker, cloud platforms, deployment, CI/CD, React/Next.js and related end-to-end signals |
| GitHub activity | 10 | Recent public repository updates and relevant Python/AI repositories |
| Engineering depth | 5 | Testing, caching, queues, observability, concurrency, retries, logging, architecture and failure handling |

The scoring is intentionally heuristic and deterministic. The score is a decision-support signal, not a substitute for human review. Missing GitHub data gives zero GitHub points but does not affect eligibility. Rejected candidates have `total_score: 0` and no score breakdown because ranking is only applied to eligible candidates.

## Design Decisions
- **Hard filters before ranking:** candidates must have both Python and AI/LLM/agentic evidence. JavaScript, Java, React, or Next.js do not disqualify candidates when both required signals exist.
- **Evidence-first scoring:** category points are derived from detected terms and project text. AI project depth is capped when project details are absent, and limited project signals incur a shallow-evidence penalty.
- **No mandatory LLM dependency:** deterministic rules make the baseline repeatable, testable, and runnable without API keys. This trades semantic nuance for reliability and transparency. A provider adapter with structured output is a logical next improvement.
- **GitHub is optional enrichment:** public repository metadata is queried only when a profile is found. API/network failures are recorded and do not stop processing.
- **Batch reliability:** a bad PDF, unsupported file, duplicate content, or extraction failure is isolated to that file.
- **Privacy:** the program writes extracted candidate details to the local JSON output. Review the output before publishing it publicly; avoid publishing candidate personal data to a public repository.

## If I Had More Time
1. Add OCR for scanned/image-only PDFs and stronger section-aware parsing.
2. Add an optional LLM extraction adapter with schema validation and evidence citations.
3. Improve GitHub signals using public events/commit history, cache responses, and bounded concurrency.
4. Add calibration tests and human-reviewed examples to measure false positives/negatives.

## Limitations
- Resume parsing and skill detection are heuristic; unusual wording and scanned PDFs can be missed.
- Project quality is estimated from textual signals and can over/under-score candidates.
- GitHub API results depend on network availability and rate limits.
- This is an assignment prototype, not an automated hiring decision system. Human review remains necessary.
