"""Run one triage call per question group and fan the result out to report IDs."""
import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

from llm_adapter import triage_with_gemini, validate_suggestion

ROOT = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Call Gemini for each unique question (requires GEMINI_API_KEY)')
    parser.add_argument('--output', default='results.live.json')
    args = parser.parse_args()
    if not args.live:
        raise SystemExit('Use --live to call Gemini. For the no-key reviewed baseline, run: python build_results.py')
    if not os.getenv('GEMINI_API_KEY'):
        raise SystemExit('GEMINI_API_KEY is not set. The reviewed results.json works without an API key.')

    data = ROOT / 'data'
    questions = {q['_id']: q for q in json.loads((data / 'questions.json').read_text())}
    reports = json.loads((data / 'reports.json').read_text())
    taxonomy = json.loads((data / 'taxonomy.json').read_text())
    grouped = defaultdict(list)
    for report in reports:
        grouped[report['questionId']].append(report)

    output = []
    for index, (qid, report_group) in enumerate(grouped.items(), start=1):
        question = questions[qid]
        print(f'[{index}/{len(grouped)}] triaging {qid} ({len(report_group)} report(s))')
        suggestion = triage_with_gemini(question, report_group, taxonomy)
        validate_suggestion(suggestion, question, taxonomy)
        for report in report_group:
            output.append({
                'reportId': report['reportId'],
                'questionId': qid,
                **suggestion,
            })

    output_path = ROOT / args.output
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(f'Wrote {len(output)} report decisions across {len(grouped)} question groups to {output_path.name}')


if __name__ == '__main__':
    main()
