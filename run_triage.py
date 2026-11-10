
"""Run live triage with automatic checkpointing and resume support."""

import argparse
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path

from llm_adapter import triage_with_groq, validate_suggestion

ROOT = Path(__file__).parent


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json_atomic(path, data):
    """Write JSON safely using a temporary file and atomic replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=path.stem + "_",
        suffix=".tmp"
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False
            )
            file.write("\n")

        os.replace(temp_path, path)

    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Run AI-powered report triage with checkpointing."
    )

    parser.add_argument(
        "--live",
        action="store_true",
        help="Run live Groq triage."
    )

    parser.add_argument(
        "--output",
        default="results.live.json",
        help="Output JSON filename."
    )

    parser.add_argument(
        "--restart",
        action="store_true",
        help="Discard the previous checkpoint and start again."
    )

    args = parser.parse_args()

    if not args.live:
        raise SystemExit(
            "Use --live to call Groq. "
            "For the reviewed baseline, run: python build_results.py"
        )

    if not os.getenv("GROQ_API_KEY"):
        raise SystemExit(
            "GROQ_API_KEY is not set. "
            "Set your Groq API key before running."
        )

    data_dir = ROOT / "data"

    questions = {
        question["_id"]: question
        for question in load_json(data_dir / "questions.json")
    }

    reports = load_json(data_dir / "reports.json")
    taxonomy = load_json(data_dir / "taxonomy.json")

    grouped = defaultdict(list)

    for report in reports:
        grouped[report["questionId"]].append(report)

    output_path = ROOT / args.output

    checkpoint_path = output_path.with_name(
        output_path.stem + ".checkpoint.json"
    )

    if args.restart and checkpoint_path.exists():
        checkpoint_path.unlink()
        print("Previous checkpoint removed.")

    completed_results = []

    completed_question_ids = set()

    if checkpoint_path.exists():

        try:
            completed_results = load_json(checkpoint_path)

            if not isinstance(completed_results, list):
                raise ValueError("Invalid checkpoint format.")

            completed_question_ids = {
                item["questionId"]
                for item in completed_results
            }

            print(
                f"Resuming from checkpoint: "
                f"{len(completed_question_ids)}/{len(grouped)} "
                f"question groups already completed."
            )

        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise SystemExit(
                f"Checkpoint is invalid: {exc}. "
                "Use --restart to start again."
            )

    else:
        print("Starting a new live triage run.")

    total_groups = len(grouped)

    for index, (qid, report_group) in enumerate(
        grouped.items(),
        start=1
    ):

        if qid in completed_question_ids:
            print(
                f"[{index}/{total_groups}] "
                f"Skipping completed question {qid}"
            )
            continue

        if qid not in questions:
            raise ValueError(
                f"Question {qid} not found in questions.json"
            )

        question = questions[qid]

        print(
            f"[{index}/{total_groups}] "
            f"triaging {qid} "
            f"({len(report_group)} report(s))"
        )

        suggestion = triage_with_groq(
            question,
            report_group,
            taxonomy
        )

        validate_suggestion(
            suggestion,
            question,
            taxonomy
        )

        group_results = []

        for report in report_group:

            group_results.append({
                "reportId": report["reportId"],
                "questionId": qid,
                **suggestion
            })

        # Save the complete question group only after validation.
        completed_results.extend(group_results)

        # Checkpoint immediately after each successful question.
        save_json_atomic(
            checkpoint_path,
            completed_results
        )

        completed_question_ids.add(qid)

        print(
            f"Checkpoint saved: "
            f"{len(completed_question_ids)}/{total_groups} groups"
        )

    # Write final output only after every group has completed.
    save_json_atomic(
        output_path,
        completed_results
    )

    print("\nLive triage completed successfully.")
    print(f"Question groups processed: {total_groups}")
    print(f"Report decisions generated: {len(completed_results)}")
    print(f"Output file: {output_path.name}")
    print(f"Checkpoint file: {checkpoint_path.name}")


if __name__ == "__main__":
    main()
