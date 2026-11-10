"""Optional Gemini triage adapter. The benchmark's committed results remain reproducible without an API key."""
import json, os
from pathlib import Path

ROOT = Path(__file__).parent

SYSTEM_PROMPT = (ROOT / 'prompts/triage_system.txt').read_text()
USER_TEMPLATE = (ROOT / 'prompts/triage_user_template.txt').read_text()


def triage_with_gemini(question, reports, taxonomy):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('Set GEMINI_API_KEY to enable live model triage. Precomputed results remain available.')
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError('Install optional dependency with: pip install google-genai') from exc

    user_prompt = USER_TEMPLATE.replace('{{taxonomy_json}}', json.dumps(taxonomy, ensure_ascii=False))
    user_prompt = user_prompt.replace('{{question_json}}', json.dumps(question, ensure_ascii=False))
    user_prompt = user_prompt.replace('{{reports_json}}', json.dumps(reports, ensure_ascii=False))
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type='application/json',
            temperature=0.1,
        ),
    )
    return json.loads(response.text)


def validate_suggestion(suggestion, question, taxonomy):
    """Fail closed: validate vocabulary, scope, source match, and auto-apply policy."""
    verdicts = taxonomy['verdicts']
    repairs = taxonomy['repairs']
    if suggestion.get('verdict') not in verdicts:
        raise ValueError('Unknown verdict')
    route = suggestion.get('route')
    confidence = suggestion.get('confidence')
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError('Confidence must be a number between 0 and 1')
    if not isinstance(suggestion.get('evidence'), str) or not isinstance(suggestion.get('student_reply'), str):
        raise ValueError('Evidence and student_reply must be strings')
    if route not in {'auto_apply', 'faculty_review', 'no_change'}:
        raise ValueError('Unknown route')
    repair = suggestion.get('repair')
    edit = suggestion.get('edit')
    if suggestion['verdict'] != 'defect':
        if repair is not None or edit is not None or route != 'no_change':
            raise ValueError('Non-defect must not propose a repair or mutation')
        return suggestion
    if repair not in repairs:
        raise ValueError('Unknown repair')
    if route == 'no_change':
        raise ValueError('A defect cannot be routed as no_change')
    if edit is not None and not isinstance(edit, dict):
        raise ValueError('Edit must be an object or null')
    if edit and not repairs[repair]['fields']:
        raise ValueError('This repair type does not permit field edits')
    if route == 'auto_apply' and not repairs[repair]['auto']:
        raise ValueError('Repair is not eligible for auto-apply')
    if edit:
        field = edit.get('field')
        if field not in repairs[repair]['fields']:
            raise ValueError('Edit touches a field outside the repair scope')
        if field in {'question', 'solution'}:
            body = question.get(question.get('questionType'), {}).get(field, '')
            if not edit.get('find') or edit.get('find') not in body:
                raise ValueError('Exact source text not found; refusing unsafe edit')
        elif field == 'answer':
            current = question.get(question.get('questionType'), {}).get('answer')
            if str(current) != str(edit.get('find')):
                raise ValueError('Stored answer does not match the proposed before-value')
        if not isinstance(edit.get('replace'), (str, int, float, list)):
            raise ValueError('Replacement must be a JSON scalar or list')
    if route == 'auto_apply' and not edit:
        raise ValueError('Auto-apply requires a concrete, validated edit')
    if repair == 'answer_key' and route == 'auto_apply':
        # A language model's confidence is not an independent mathematical proof.
        raise ValueError('Answer-key changes require independent verification before auto-apply')
    return suggestion
