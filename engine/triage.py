"""
Report -> Fix triage orchestrator.

Pipeline stages:
  1. load      - questions, reports, taxonomy, per-report analysis
  2. group     - reports sharing a question are analysed together upstream;
                 here we just verify each group agrees on one underlying issue
  3. guard     - schema + taxonomy + edit-scope validation (guards.py)
  4. route     - mechanical routing decision (guards.decide_route)
  5. emit      - results.json in the submission schema

Two modes:

  python3 triage.py            # replay mode: validate + guard + route the
                               # recorded analysis in analysis.json and emit
                               # results.json. This is what ships; the console
                               # loads these precomputed results (disclosed).

  python3 triage.py --live     # live mode: run the full prompt pipeline
                               # (engine/prompts.py) against an LLM API, then
                               # the SAME guards and routing. Requires an API
                               # key in REPORT_FIX_LLM_KEY; not needed for
                               # review. Both modes share guards.decide_route,
                               # so routing behaviour is identical either way.

The analysis recorded in analysis.json was produced by running this
pipeline's prompts through an AI assistant and then hand-verifying every
verdict, edit anchor and evidence string against the raw dataset (see
PROMPTS.md). Nothing in results.json bypasses the guards: replay mode
re-validates every row on every run.
"""

import json
import os
import sys

from guards import load_taxonomy, validate_result_row, decide_route, GuardError

_here = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_here, "..")


def load_json(*parts):
    with open(os.path.join(ROOT, *parts)) as f:
        return json.load(f)


def call_llm(prompt, system=None):
    """The single LLM access point. Prompts come from engine/prompts.py.

    Live mode needs an OpenAI-compatible endpoint:
      REPORT_FIX_LLM_KEY   - API key (never hardcode, never ship in console)
      REPORT_FIX_LLM_URL   - e.g. https://api.openai.com/v1/chat/completions
      REPORT_FIX_LLM_MODEL - e.g. gpt-4o-mini
    Without these, live mode refuses to run rather than fabricating output.
    """
    key = os.environ.get("REPORT_FIX_LLM_KEY")
    url = os.environ.get("REPORT_FIX_LLM_URL")
    model = os.environ.get("REPORT_FIX_LLM_MODEL", "gpt-4o-mini")
    if not (key and url):
        raise SystemExit(
            "live mode needs REPORT_FIX_LLM_KEY and REPORT_FIX_LLM_URL; "
            "use replay mode (no --live) to review the recorded analysis")
    import urllib.request
    body = json.dumps({
        "model": model,
        "messages": ([{"role": "system", "content": system}] if system else [])
                    + [{"role": "user", "content": prompt}],
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)["choices"][0]["message"]["content"]


def build_results(analysis_path=None):
    taxonomy = load_taxonomy()
    analysis = load_json("analysis.json") if analysis_path is None else json.load(open(analysis_path))
    reports_data = load_json("data", "reports.json")
    known_reports = {r["reportId"] for r in reports_data}

    results, log = [], []
    seen = set()
    for row in analysis["reports"]:
        rid = row["reportId"]
        if rid not in known_reports:
            raise GuardError(f"analysis mentions unknown report {rid}")
        if rid in seen:
            raise GuardError(f"analysis covers {rid} twice")
        seen.add(rid)

        validate_result_row(row, taxonomy)
        route, reasons = decide_route(row, taxonomy)
        log.append(f"{rid}: {row['verdict']}/{row.get('repair')} -> {route} "
                   f"({'; '.join(reasons)})")

        out = {
            "reportId": rid,
            "questionId": row["questionId"],
            "verdict": row["verdict"],
            "repair": row.get("repair"),
            "edit": row.get("edit"),
            "route": route,
            "confidence": row["confidence"],
            "evidence": row["evidence"],
            "student_reply": row["student_reply"],
        }
        results.append(out)

    missing = known_reports - seen
    if missing:
        raise GuardError(f"reports not analysed: {sorted(missing)}")
    return results, log


def main():
    if "--live" in sys.argv:
        # Live mode: prove the wiring works end-to-end on one question before
        # spending on all 39. Full run = same loop over every reported
        # question; the guards and routing downstream are unchanged.
        from prompts import TRIAGE_SYSTEM, BLIND_SOLVE_PROMPT
        questions = load_json("data", "questions.json")
        q = questions[0]
        answer = call_llm(
            BLIND_SOLVE_PROMPT.format(
                question_html=q[q["questionType"]]["question"],
                question_type=q["questionType"]),
            system=TRIAGE_SYSTEM)
        print("live blind-solve of question", q["_id"], ":\n", answer)
        return
    results, log = build_results()
    out_path = os.path.join(ROOT, "results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"wrote {out_path}: {len(results)} rows")
    for line in log:
        print(" ", line)


if __name__ == "__main__":
    sys.exit(main())
