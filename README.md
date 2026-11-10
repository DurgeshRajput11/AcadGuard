# Acadza Report → Fix

**An AI-assisted question integrity and faculty review system for competitive examination question banks.**





**Live Application:** [https://acadguard.onrender.com/](https://acadguard.onrender.com/)
**GitHub Repository:** [https://github.com/DurgeshRajput11/AcadGuard](https://github.com/DurgeshRajput11/AcadGuard)

---

## 1. Overview

Competitive examination platforms maintain large question banks containing hundreds of thousands of questions. Even a small number of incorrect answer keys, incomplete questions, formatting issues, or faulty explanations can negatively affect students.

When students report these issues, faculty members need to investigate the reports, identify duplicate complaints, verify the underlying question, and decide whether a correction is necessary.

This project implements a student-report triage workflow and a faculty review console to make that process more structured, transparent, and safe.

The system:

- Groups multiple student reports associated with the same question.
- Categorizes reported issues using a predefined taxonomy.
- Routes cases to appropriate review categories.
- Presents evidence and proposed corrections to faculty.
- Supports approval, rejection, editing, and reopening of cases.
- Maintains an audit trail of faculty decisions.
- Provides an optional Gemini integration for experimenting with live AI-assisted triage.

The central design principle is:

**Resolve student reports with evidence, not guesswork.**

## 2. Live Demo

The deployed application provides a faculty-facing dashboard with the following sections:

| Section         | Functionality                                                              |
| --------------- | -------------------------------------------------------------------------- |
| Review Queue    | View and investigate reported questions                                    |
| Audit History   | Review recorded faculty actions                                            |
| Question Bank   | Search and inspect available questions                                     |
| Triage Settings | View triage configuration                                                  |
| Case Details    | Inspect question previews, student reports, evidence, and proposed changes |

The interface includes:

- Dashboard statistics and case summaries.
- Question-level report grouping.
- Issue categories and review statuses.
- Question and MathML previews.
- Before/after correction comparison.
- Editable proposed replacements.
- Student reply previews.
- Faculty review actions.

**Live URL:** [https://acadguard.onrender.com/](https://acadguard.onrender.com/)

## 3. Benchmark Results

The supplied assignment dataset contains:

| Metric                    | Result |
| ------------------------- | -----: |
| Student reports           |     44 |
| Unique reported questions |     39 |
| Auto-eligible cases       |     12 |
| Faculty review cases      |      9 |
| No-change cases           |     18 |

The benchmark demonstrates how multiple reports can be consolidated around individual questions instead of requiring faculty to investigate every report independently.

The benchmark classifications are reviewed outputs, not claims of production-scale model performance.

## 4. System Architecture

The application follows a modular architecture.

```text
                 Student Reports
                        |
                        v
              Dataset Loading
                        |
                        v
             Question-Level Grouping
                        |
                        v
              Triage and Classification
                        |
              +---------+---------+
              |                   |
              v                   v
        Benchmark Results    Optional Gemini
              |              Integration
              |                   |
              |             Structured Output
              |                   |
              |             Safety Validation
              |                   |
              +---------+---------+
                        |
                        v
               FastAPI Backend
                        |
                        v
             Faculty Review Console
                        |
             +----------+----------+
             |          |          |
             v          v          v
           Approve    Reject      Edit
             |          |          |
             +----------+----------+
                        |
                        v
                 SQLite Audit Log
```

### Technology Stack

| Component       | Technology            |
| --------------- | --------------------- |
| Backend         | Python, FastAPI       |
| Frontend        | HTML, CSS, JavaScript |
| Data storage    | JSON                  |
| Audit logging   | SQLite                |
| Data validation | Pydantic              |
| Optional LLM    | Google Gemini API     |
| Deployment      | Render                |
| Version control | Git and GitHub        |

## 5. How the Triage Workflow Works

### Step 1: Load and organize reports

The system loads the supplied question bank, student reports, and issue taxonomy.

Reports associated with the same question are grouped together to reduce duplicate investigation.

### Step 2: Classify reported issues

Cases are organized into categories such as:

- Answer-key issues
- Question or stem defects
- Missing information
- Solution or explanation issues
- Other content-related concerns

### Step 3: Route cases

The triage workflow distinguishes between cases that may qualify for narrow, validated repairs, cases requiring faculty review, and reports that do not justify a change.

### Step 4: Present evidence

Faculty can inspect:

- Original question content.
- Student-submitted reports.
- Issue classification.
- Current answer information.
- Proposed replacement.
- Supporting evidence and reasoning.

### Step 5: Faculty decision

Faculty members can approve, reject, edit, or reopen a case.

The application records review decisions and overrides in its local SQLite audit database.

## 6. AI Integration

The deployed application currently uses reviewed benchmark results and does not require an API key.

An optional Gemini integration is included for experimenting with live AI-assisted triage.

### Live triage workflow

1. Provide the question, associated reports, and permitted issue taxonomy.
2. Request structured JSON output from Gemini.
3. Validate the model response before presenting the suggestion.
4. Reject unsupported or out-of-scope changes.
5. Route uncertain cases to faculty review.

### Running optional Gemini triage

Install the additional dependency:

```bash
pip install google-genai
```

Set the API key.

**Windows PowerShell:**

```powershell
$env:GEMINI_API_KEY="your-key"
```

**macOS/Linux:**

```bash
export GEMINI_API_KEY="your-key"
```

Run the optional live triage pipeline:

```bash
python run_triage.py --live --output results.live.json
```

The live pipeline makes one model call per unique question and distributes the resulting triage output across its associated reports.

Live model output is stored separately from the reviewed benchmark output.

The pipeline validates model suggestions and aborts on invalid or out-of-scope output rather than silently accepting unsafe changes.

**Note:** The deployed benchmark application does not automatically invoke Gemini. Live integration is an optional experimentation path.

## 7. Safety and Reliability

Educational content requires a conservative correction workflow. An incorrect automated correction can be more harmful than leaving a reported issue unresolved.

The system follows these principles:

### No unsupported content generation

AI must not invent:

- Missing question statements.
- Missing options or diagrams.
- Unsupported explanations.
- Missing mathematical assumptions.
- Unverified syllabus classifications.

### Answer-key protection

A model's confidence score alone is not sufficient to change an answer key.

Answer-key changes require independent verification and appropriate faculty review.

### Untrusted student input

Student comments and submitted content are treated as untrusted data, not as instructions to the AI system.

### Fail-closed validation

The optional LLM integration validates structured outputs, taxonomy values, and permitted edit scope before suggestions are accepted.

### No silent production changes

The prototype does not modify the production question bank or notify real students.

Faculty actions are recorded in the local audit database only.

### Safe content previews

Supplied HTML and MathML previews are displayed inside sandboxed iframes with scripts disabled.

## 8. Product Decisions and Assignment Questions

### 1. Who is most affected by incorrect questions?

Students preparing for competitive examinations are the most directly affected.

An incorrect answer key, incomplete question, or faulty explanation can lead to incorrect learning and loss of confidence.

Faculty members are also affected because they must spend time investigating repeated reports and verifying content.

### 2. What should AI never automatically change?

AI should never invent missing question content, diagrams, answer options, explanations, or syllabus information.

It should not change an answer key based only on model confidence.

Ambiguous cases and corrections without sufficient evidence should be routed to faculty.

### 3. What metric matters most in the first week?

**Verified defect precision** is the most important initial metric.

It measures the percentage of proposed corrections that faculty confirm are genuine defects.

The priority should be producing trustworthy suggestions rather than maximizing the number of processed reports.

### 4. What would be built next?

A question-impact prioritization system.

It would consider:

- Number of reports associated with a question.
- Severity of the reported issue.
- Examination relevance.
- Number of potentially affected students.
- Faculty review priority.

This would help faculty investigate the most important reported defects first.

## 9. Project Structure

```text
AcadGuard/
|
|-- app.py
|-- build_results.py
|-- run_triage.py
|-- llm_adapter.py
|
|-- requirements.txt
|-- render.yaml
|-- README.md
|-- PROMPTS.md
|-- PRODUCT.md
|-- BONUS_FINDINGS.md
|
|-- results.json
|
|-- data/
|   |-- questions.json
|   |-- reports.json
|   |-- taxonomy.json
|
|-- prompts/
|   |-- system_prompt.txt
|   |-- user_template.txt
|
|-- static/
    |-- index.html
```

## 10. Run Locally

### Prerequisites

- Python 3.11 or later.
- pip.
- Git.

### Clone the repository

```bash
git clone https://github.com/DurgeshRajput11/AcadGuard.git
cd AcadGuard
```

### Create a virtual environment

```bash
python -m venv .venv
```

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Start the application

```bash
uvicorn app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

Check backend health:

```text
http://127.0.0.1:8000/health
```

The health endpoint reports whether the dataset has loaded successfully.

## 11. Reproduce the Benchmark

Generate the deterministic reviewed benchmark output:

```bash
python build_results.py
```

This does not require an LLM API key.

For optional live Gemini experimentation:

```bash
python run_triage.py --live --output results.live.json
```

The live output is kept separate so it cannot overwrite the reviewed benchmark results.

## 12. Deployment

The application is deployed on Render.

The repository includes `render.yaml` for deployment configuration.

**Live application:** [https://acadguard.onrender.com/](https://acadguard.onrender.com/)

### Deployment notes

- The deployed application uses the reviewed benchmark results.
- Optional Gemini experimentation requires a valid API key.
- The SQLite audit database is suitable for demonstration purposes.
- Free hosting environments may use ephemeral filesystems, so SQLite data may reset after redeployment or instance replacement.
- A managed PostgreSQL database is recommended for durable production audit history.

## 13. Limitations and Future Improvements

This implementation is a benchmark prototype, not a production deployment for an entire question bank of approximately 800,000 questions.

Potential future improvements include:

- Managed PostgreSQL for persistent audit history.
- Authentication and role-based faculty permissions.
- Background processing for large report volumes.
- Better mathematical and scientific verification.
- Calibrated model confidence evaluation.
- Faculty feedback and correction-quality analytics.
- Question-impact prioritization.
- Production integration with a versioned question bank.

Any production integration should preserve faculty approval, auditability, and rollback capability.

## 14. Additional Documentation

- [PROMPTS.md](PROMPTS.md) — System prompts, user templates, and prompt design decisions.
- [PRODUCT.md](PRODUCT.md) — Product reasoning, safety boundaries, and prioritization decisions.
- [BONUS_FINDINGS.md](BONUS_FINDINGS.md) — Additional quality-assurance finding.

---

## Final Note

Acadza Report → Fix explores how student feedback can become a structured question-quality workflow.

The objective is not to let AI make unchecked changes to educational content. It is to help faculty identify, investigate, and resolve reported defects with evidence, transparency, and control.
