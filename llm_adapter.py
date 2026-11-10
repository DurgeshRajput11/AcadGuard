
"""Optional Groq triage adapter with retries and fail-safe validation."""

import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).parent

SYSTEM_PROMPT = (
    ROOT / "prompts/triage_system.txt"
).read_text(encoding="utf-8")

USER_TEMPLATE = (
    ROOT / "prompts/triage_user_template.txt"
).read_text(encoding="utf-8")


def triage_with_groq(question, reports, taxonomy):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Set GROQ_API_KEY to enable live model triage. "
            "Precomputed results remain available."
        )

    try:
        from groq import Groq, RateLimitError
    except ImportError as exc:
        raise RuntimeError(
            "Install optional dependency with: pip install groq"
        ) from exc

    user_prompt = USER_TEMPLATE.replace(
        "{{taxonomy_json}}",
        json.dumps(taxonomy, ensure_ascii=False)
    )

    user_prompt = user_prompt.replace(
        "{{question_json}}",
        json.dumps(question, ensure_ascii=False)
    )

    user_prompt = user_prompt.replace(
        "{{reports_json}}",
        json.dumps(reports, ensure_ascii=False)
    )

    client = Groq(api_key=api_key)

    model = os.getenv(
        "GROQ_MODEL",
        "openai/gpt-oss-120b"
    )

    response = None

    for attempt in range(8):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                response_format={
                    "type": "json_object"
                },
                temperature=0.1,
            )

            print("Groq request successful.")

            # Allow the token-per-minute window to recover.
            time.sleep(25)

            break

        except RateLimitError:
            if attempt == 7:
                raise

            wait = 25

            print(
                f"Rate limit exceeded. "
                f"Waiting {wait} seconds "
                f"(retry {attempt + 1}/8)..."
            )

            time.sleep(wait)

    if response is None:
        raise RuntimeError(
            "Groq did not return a response."
        )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError(
            "Groq returned an empty response."
        )

    try:
        return json.loads(content)

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Groq returned invalid JSON: {content[:500]}"
        ) from exc


def validate_suggestion(suggestion, question, taxonomy):
    """Strict, fail-closed validation of model-generated triage decisions."""
    import math

    required = {
        "verdict", "repair", "edit", "route",
        "confidence", "evidence", "student_reply"
    }
    if not isinstance(suggestion, dict) or set(suggestion) != required:
        raise ValueError("Suggestion must contain exactly the seven required keys")

    verdicts = taxonomy.get("verdicts", {})
    repairs = taxonomy.get("repairs", {})
    verdict = suggestion.get("verdict")
    route = suggestion.get("route")
    confidence = suggestion.get("confidence")

    if verdict not in verdicts:
        raise ValueError("Unknown verdict")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(float(confidence))
        or not 0 <= confidence <= 1
    ):
        raise ValueError("Confidence must be a finite number between 0 and 1")
    if route not in {"auto_apply", "faculty_review", "no_change"}:
        raise ValueError("Unknown route")
    for key in ("evidence", "student_reply"):
        if not isinstance(suggestion.get(key), str) or not suggestion[key].strip():
            raise ValueError(f"{key} must be a non-empty string")

    repair, edit = suggestion.get("repair"), suggestion.get("edit")
    if verdict != "defect":
        if repair is not None or edit is not None or route != "no_change":
            raise ValueError("Non-defects require null repair/edit and no_change route")
        return suggestion

    if repair not in repairs:
        raise ValueError("Unknown repair")
    rule = repairs[repair]
    fields = rule.get("fields", [])
    if not isinstance(fields, list):
        raise ValueError("Repair fields must be a list")
    if route == "no_change":
        raise ValueError("A defect cannot be routed as no_change")

    if edit is None:
        if route == "auto_apply":
            suggestion["route"] = "faculty_review"
        return suggestion
    if not isinstance(edit, dict) or set(edit) != {"field", "find", "replace"}:
        raise ValueError("Edit must contain exactly field, find, and replace")
    field, before, after = edit["field"], edit["find"], edit["replace"]
    if field not in fields:
        raise ValueError("Edit field is outside the repair taxonomy scope")
    if not isinstance(before, str) or not before:
        raise ValueError("Edit before-value must be a non-empty string")
    if isinstance(after, bool) or not isinstance(after, (str, int, float, list)):
        raise ValueError("Replacement must be a string, number, or list")
    if isinstance(after, list) and any(isinstance(x, (dict, list, bool)) for x in after):
        raise ValueError("Replacement lists may contain only scalar values")

    record = question.get(question.get("questionType"), {})
    if field in {"question", "solution"}:
        if not isinstance(after, str):
            raise ValueError("Question/solution replacements must be strings")
        source = record.get(field, "")
        if not isinstance(source, str) or before not in source:
            suggestion["edit"] = None
            suggestion["route"] = "faculty_review"
            return suggestion
    elif field == "answer":
        if str(record.get("answer")) != before:
            suggestion["edit"] = None
            suggestion["route"] = "faculty_review"
            return suggestion

    # Only deterministic text-cleanup categories can remain automatic.
    safe_auto = {"spelling", "noise", "exam_reference", "markup_leak"}
    if route == "auto_apply" and (
        repair not in safe_auto or rule.get("auto") is not True or confidence < 0.95
    ):
        suggestion["route"] = "faculty_review"
    return suggestion
