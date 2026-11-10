# Acadza Report → Fix

A benchmark implementation of the student-report triage loop and faculty review console.

## Run locally

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://127.0.0.1:8000. The `/health` endpoint confirms the dataset is loaded.

## What is included

- `data/questions.json`, `data/reports.json`, `data/taxonomy.json`: original assignment data.
- `results.json`: one triage result per each of the 44 reports.
- `build_results.py`: reproducible generator for the reviewed benchmark output.
- `app.py`: FastAPI API, question-level grouping, review actions and SQLite audit log.
- `static/index.html`: responsive faculty console with sandboxed HTML/MathML previews, evidence, before/after diff, editable proposed replacements, and student reply preview.
- `prompts/`: live triage prompt and user template.
- `llm_adapter.py`: optional Gemini integration and fail-closed validation.
- `PROMPTS.md`, `PRODUCT.md`: required product and prompt notes.

## Optional Gemini live triage

The submitted console does not require an API key: it loads the reviewed benchmark results. To experiment with live triage:

```bash
pip install google-genai
# PowerShell: $env:GEMINI_API_KEY="your-key"
# macOS/Linux: export GEMINI_API_KEY="your-key"
```

Call `triage_with_gemini(question, reports, taxonomy)` from `llm_adapter.py`, then pass the response to `validate_suggestion(...)` before showing or acting on it. Live model output is not the committed benchmark output. The validator rejects out-of-scope edits, unknown taxonomy keys, and model-only answer-key auto-application.

## Safety / demo scope

- Student comments are untrusted data and are never interpreted as instructions.
- The UI's Approve / Reject / Save edit actions write decisions and faculty overrides to `review_audit.db` only.
- This prototype does **not** mutate Acadza's production question bank, notify real students, or apply question edits to production.
- The supplied HTML/MathML is shown inside sandboxed iframes with scripts disabled.

## Deployment

A free Render web service can deploy this repository with the included `render.yaml`. The SQLite audit log is demo-grade and may reset on ephemeral filesystems; use managed PostgreSQL for durable production audit history.

## Bonus QA

See [`BONUS_FINDINGS.md`](BONUS_FINDINGS.md) for a candidate malformed-MathML issue in an unreported question.

## Run the grouped triage engine

```bash
# Deterministic, reviewed benchmark output (no API required)
python build_results.py

# Optional live Gemini pass: one call per unique question, then fan out to all reports
pip install google-genai
# set GEMINI_API_KEY first, then:
python run_triage.py --live --output results.live.json
```

The live run writes to a separate output file by default so it cannot overwrite the reviewed benchmark. It aborts on invalid or out-of-scope model output rather than silently accepting it.
