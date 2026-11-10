
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
    """
    Fail-closed validation of AI suggestions.

    Unsafe or unverifiable edits are discarded and routed
    to faculty review instead of being automatically applied.
    """

    verdicts = taxonomy["verdicts"]
    repairs = taxonomy["repairs"]

    if suggestion.get("verdict") not in verdicts:
        raise ValueError("Unknown verdict")

    route = suggestion.get("route")
    confidence = suggestion.get("confidence")

    if (
        not isinstance(confidence, (int, float))
        or not 0 <= confidence <= 1
    ):
        raise ValueError(
            "Confidence must be a number between 0 and 1"
        )

    if (
        not isinstance(suggestion.get("evidence"), str)
        or not isinstance(suggestion.get("student_reply"), str)
    ):
        raise ValueError(
            "Evidence and student_reply must be strings"
        )

    if route not in {
        "auto_apply",
        "faculty_review",
        "no_change"
    }:
        raise ValueError("Unknown route")

    repair = suggestion.get("repair")
    edit = suggestion.get("edit")

    # Non-defects must never propose a mutation.
    if suggestion["verdict"] != "defect":

        if (
            repair is not None
            or edit is not None
            or route != "no_change"
        ):
            raise ValueError(
                "Non-defect must not propose a repair or mutation"
            )

        return suggestion

    if repair not in repairs:
        raise ValueError("Unknown repair")

    if route == "no_change":
        raise ValueError(
            "A defect cannot be routed as no_change"
        )

    if edit is not None and not isinstance(edit, dict):
        raise ValueError(
            "Edit must be an object or null"
        )

    if edit and not repairs[repair]["fields"]:
        raise ValueError(
            "This repair type does not permit field edits"
        )

    if (
        route == "auto_apply"
        and not repairs[repair]["auto"]
    ):
        raise ValueError(
            "Repair is not eligible for auto-apply"
        )

    if edit:

        field = edit.get("field")

        if field not in repairs[repair]["fields"]:
            raise ValueError(
                "Edit touches a field outside the repair scope"
            )

        if field in {"question", "solution"}:

            body = question.get(
                question.get("questionType"), {}
            ).get(field, "")

            if (
                not isinstance(body, str)
                or not isinstance(edit.get("find"), str)
                or not edit["find"]
                or edit["find"] not in body
            ):
                print(
                    "WARNING: Exact source text mismatch. "
                    "Discarding proposed edit and routing "
                    "to faculty review."
                )

                suggestion["edit"] = None
                suggestion["route"] = "faculty_review"
                edit = None

        elif field == "answer":

            current = question.get(
                question.get("questionType"), {}
            ).get("answer")

            if str(current) != str(edit.get("find")):

                print(
                    "WARNING: Answer before-value mismatch. "
                    "Discarding proposed edit and routing "
                    "to faculty review."
                )

                suggestion["edit"] = None
                suggestion["route"] = "faculty_review"
                edit = None

        if edit and not isinstance(
            edit.get("replace"),
            (str, int, float, list)
        ):
            raise ValueError(
                "Replacement must be a JSON scalar or list"
            )

    # Auto-apply requires a concrete, validated edit.
    if (
        suggestion["route"] == "auto_apply"
        and not suggestion.get("edit")
    ):
        raise ValueError(
            "Auto-apply requires a concrete, validated edit"
        )

    # Answer-key changes always require human review.
    if (
        repair == "answer_key"
        and suggestion["route"] == "auto_apply"
    ):
        print(
            "Answer-key change routed to faculty review."
        )

        suggestion["route"] = "faculty_review"

    return suggestion
