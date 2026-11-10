import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import os

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
DB = ROOT / 'review_audit.db'

questions = {
    q['_id']: q
    for q in json.loads((DATA / 'questions.json').read_text(encoding='utf-8'))
}
reports = json.loads((DATA / 'reports.json').read_text(encoding='utf-8'))
RESULTS_FILE = os.getenv("RESULTS_FILE", "results.json")
RESULTS_PATH = ROOT / RESULTS_FILE

if not RESULTS_PATH.exists():
    raise FileNotFoundError(
        f"{RESULTS_FILE} not found. "
        "Set RESULTS_FILE to an available results JSON file."
    )

results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
taxonomy = json.loads((DATA / 'taxonomy.json').read_text(encoding='utf-8'))
result_by_id = {r['reportId']: r for r in results}
report_by_id = {r['reportId']: r for r in reports}

app = FastAPI(title='Acadza Report → Fix', version='1.0.0')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')


def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id TEXT NOT NULL,
            report_ids TEXT NOT NULL,
            action TEXT NOT NULL,
            note TEXT DEFAULT '',
            actor TEXT DEFAULT 'Faculty demo user',
            created_at TEXT NOT NULL
        )''')
        con.execute('''CREATE TABLE IF NOT EXISTS case_state (
            question_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            faculty_note TEXT DEFAULT '',
            faculty_edit TEXT DEFAULT '',
            updated_at TEXT NOT NULL
        )''')
        columns = {row['name'] for row in con.execute('PRAGMA table_info(case_state)').fetchall()}
        if 'faculty_edit' not in columns:
            con.execute("ALTER TABLE case_state ADD COLUMN faculty_edit TEXT DEFAULT ''")


init_db()


def clean_render_html(value: str) -> str:
    # The supplied benchmark HTML is rendered in a script-disabled sandboxed iframe.
    # This wrapper intentionally does not grant same-origin or script permissions.
    return value or '<p>No content supplied.</p>'


def proposed_edit(q: dict, result: dict, override=None):
    edit = result.get('edit')
    if edit and override:
        edit = {**edit, **override}
    if not edit:
        return None
    field = edit.get('field')
    qtype = q.get('questionType')
    if field == 'answer':
        before = q.get(qtype, {}).get('answer')
        before_text = json.dumps(before, ensure_ascii=False)
        after_text = json.dumps(edit.get('replace'), ensure_ascii=False)
        return {'field': 'answer', 'before': before_text, 'after': after_text, 'replacement': str(edit.get('replace'))}
    if field in ('question', 'solution'):
        before = q.get(qtype, {}).get(field, '')
        find = edit.get('find', '')
        after = before.replace(find, edit.get('replace', ''), 1) if find and find in before else before
        return {'field': field, 'before': before, 'after': after, 'replacement': edit.get('replace', ''), 'applied': after != before}
    return None


ROUTE_PRIORITY = {
    "no_change": 0,
    "auto_apply": 1,
    "faculty_review": 2,
}


def select_primary(items):
    """Choose the safest report-level decision for a question group.

    Faculty review takes precedence over auto-apply, regardless of confidence.
    Answer-key changes are treated as faculty-review items even if an upstream
    result incorrectly labels them auto_apply.
    """
    if not items:
        raise ValueError("Cannot select a primary result from an empty group.")

    def sort_key(item):
        route = item.get("route")
        if item.get("repair") == "answer_key" and route == "auto_apply":
            route = "faculty_review"
        return (
            ROUTE_PRIORITY.get(route, ROUTE_PRIORITY["faculty_review"]),
            item.get("confidence", 0),
        )

    primary = dict(max(items, key=sort_key))
    if primary.get("repair") == "answer_key" and primary.get("route") == "auto_apply":
        primary["route"] = "faculty_review"
    return primary


def get_case_groups():
    grouped = defaultdict(list)
    for report in reports:
        grouped[report['questionId']].append(report)
    cases = []
    for qid, group in grouped.items():
        q = questions.get(qid)
        if not q:
            continue
        items = [result_by_id[r['reportId']] for r in group]
        primary = select_primary(items)
        state = None
        with connect() as con:
            state = con.execute('SELECT status, faculty_note, faculty_edit, updated_at FROM case_state WHERE question_id=?', (qid,)).fetchone()
        severity = 0
        if primary.get('repair') == 'answer_key': severity = 100
        elif primary.get('repair') in ('diagram','option_repair','stem_data','unsound'): severity = 90
        elif primary['route'] == 'faculty_review': severity = 75
        elif primary['verdict'] in ('app_issue','display_issue'): severity = 45
        else: severity = 25
        cases.append({
            'questionId': qid,
            'subject': q.get('subject'), 'chapter': q.get('chapter'), 'questionType': q.get('questionType'),
            'level': q.get('level'), 'question': clean_render_html(q.get(q.get('questionType'), {}).get('question', '')),
            'solution': clean_render_html(q.get(q.get('questionType'), {}).get('solution', '')),
            'answer': q.get(q.get('questionType'), {}).get('answer'),
            'reports': group, 'results': items, 'primary': primary,
            'editPreview': proposed_edit(q, primary, json.loads(state['faculty_edit']) if state and state['faculty_edit'] else None),
            'facultyEdit': json.loads(state['faculty_edit']) if state and state['faculty_edit'] else None,
            'status': state['status'] if state else ('needs_review' if primary['route']=='faculty_review' else 'pending'),
            'facultyNote': state['faculty_note'] if state else '',
            'updatedAt': state['updated_at'] if state else None,
            'urgency': severity + min(len(group), 5) * 4,
        })
    cases.sort(key=lambda x: (-x['urgency'], -len(x['reports']), x['questionId']))
    return cases


@app.get('/')
def index():
    return FileResponse(ROOT / 'static' / 'index.html')


@app.get('/api/summary')
def summary():
    cases = get_case_groups()
    return {
        'reports': len(reports), 'questions': len(questions), 'reportedQuestions': len(cases),
        'facultyReview': sum(1 for c in cases if c['primary']['route']=='faculty_review'),
        'autoEligible': sum(1 for c in cases if c['primary']['route']=='auto_apply'),
        'noChange': sum(1 for c in cases if c['primary']['route']=='no_change'),
        'resolved': sum(1 for c in cases if c['status'] in ('approved','rejected','edited')),
    }


@app.get('/api/cases')
def list_cases(search: Optional[str] = None, route: Optional[str] = None, status: Optional[str] = None):
    cases = get_case_groups()
    if search:
        term = search.lower()
        cases = [c for c in cases if term in c['questionId'].lower() or term in (c['subject'] or '').lower() or term in (c['chapter'] or '').lower() or any(term in r['comment'].lower() for r in c['reports'])]
    if route and route != 'all':
        cases = [c for c in cases if c['primary']['route'] == route]
    if status and status != 'all':
        cases = [c for c in cases if c['status'] == status]
    return cases


class ActionBody(BaseModel):
    questionId: str
    action: str = Field(pattern='^(approve|reject|edit|reopen)$')
    note: str = ''
    actor: str = 'Faculty demo user'
    editField: Optional[str] = None
    editedValue: Optional[str] = None


@app.post('/api/action')
def record_action(body: ActionBody):
    if body.questionId not in questions:
        raise HTTPException(404, 'Question not found')
    reports_for_question = [r for r in reports if r['questionId'] == body.questionId]
    report_ids = [r['reportId'] for r in reports_for_question]
    status = {'approve':'approved', 'reject':'rejected', 'edit':'edited', 'reopen':'pending'}[body.action]
    faculty_edit = None
    if body.action == 'edit' and body.editedValue is not None:
        question_results = [
            result_by_id[r['reportId']]
            for r in reports_for_question
            if r['reportId'] in result_by_id
        ]
        if not question_results:
            raise HTTPException(400, 'No triage results are available for this question')
        primary = select_primary(question_results)
        allowed = taxonomy['repairs'].get(primary.get('repair'), {}).get('fields', [])
        if body.editField not in allowed:
            raise HTTPException(400, 'This repair does not permit editing that field')
        original = primary.get('edit')
        if not original or original.get('field') != body.editField:
            raise HTTPException(400, 'No matching surgical edit exists; add a faculty note or create a separate authored repair')
        if body.editField in ('question', 'solution') and original.get('find') not in questions[body.questionId][questions[body.questionId]['questionType']][body.editField]:
            raise HTTPException(400, 'The original source text no longer matches')
        if body.editField == 'answer':
            current_answer = questions[body.questionId][questions[body.questionId]['questionType']]['answer']
            if str(current_answer) != str(original.get('find')):
                raise HTTPException(400, 'The stored answer no longer matches the proposed before-value')
        faculty_edit = json.dumps({'field': body.editField, 'replace': body.editedValue}, ensure_ascii=False)
    audit_note = body.note
    if faculty_edit is not None:
        audit_note = (audit_note + ' | ' if audit_note else '') + 'Edited ' + body.editField + ' replacement to: ' + body.editedValue
    now = datetime.now(timezone.utc).isoformat()
    with connect() as con:
        con.execute('INSERT INTO audit(question_id, report_ids, action, note, actor, created_at) VALUES(?,?,?,?,?,?)',
                    (body.questionId, json.dumps(report_ids), body.action, audit_note, body.actor, now))
        con.execute('''INSERT INTO case_state(question_id,status,faculty_note,faculty_edit,updated_at) VALUES(?,?,?,?,?)
                    ON CONFLICT(question_id) DO UPDATE SET status=excluded.status, faculty_note=excluded.faculty_note, faculty_edit=COALESCE(excluded.faculty_edit, case_state.faculty_edit), updated_at=excluded.updated_at''',
                    (body.questionId, status, body.note, faculty_edit, now))
    return {'ok': True, 'status': status, 'audit': get_audit(body.questionId)}


def get_audit(qid):
    with connect() as con:
        rows = con.execute('SELECT * FROM audit WHERE question_id=? ORDER BY id DESC', (qid,)).fetchall()
    return [dict(r) for r in rows]


@app.get('/api/audit/{question_id}')
def audit(question_id: str):
    if question_id not in questions:
        raise HTTPException(404, 'Question not found')
    return get_audit(question_id)


@app.get('/api/taxonomy')
def get_taxonomy():
    return taxonomy


@app.get('/api/audit')
def audit_history():
    with connect() as con:
        rows = con.execute('SELECT * FROM audit ORDER BY id DESC').fetchall()
    history = []
    for row in rows:
        item = dict(row)
        q = questions.get(item['question_id'], {})
        item['subject'] = q.get('subject', 'Unknown')
        item['chapter'] = q.get('chapter', 'Unknown')
        history.append(item)
    return history


@app.get('/api/question-bank')
def question_bank(search: Optional[str] = None):
    items = []
    term = (search or '').strip().lower()
    for qid, q in questions.items():
        qtype = q.get('questionType')
        content = q.get(qtype, {}) if qtype else {}
        question_text = content.get('question', '') or ''
        searchable = ' '.join([
            str(qid), str(q.get('subject', '')), str(q.get('chapter', '')),
            str(qtype or ''), str(q.get('level', '')), str(question_text)
        ]).lower()
        if term and term not in searchable:
            continue
        items.append({
            'questionId': qid,
            'subject': q.get('subject'),
            'chapter': q.get('chapter'),
            'questionType': qtype,
            'level': q.get('level'),
            'question': question_text,
            'answer': content.get('answer'),
            'solution': content.get('solution', '')
        })
    return items


@app.get('/health')
def health():
    return {'ok': True, 'reports_loaded': len(results), 'questions_loaded': len(questions)}
