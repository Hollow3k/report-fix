"""
Prepare console/data.js for the faculty review console.

Joins results.json with the source questions and applies each proposed
edit to produce before/after content for the diff view. Auto-applied rows
ship with the edit applied; faculty_review rows show the suggestion only.
Every action a faculty member takes in the console appends to an audit
trail (kept in-browser; this file seeds it).
"""

import json
import os

_here = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_here, "..")


def load(*parts):
    with open(os.path.join(ROOT, *parts)) as f:
        return json.load(f)


def apply_edit(question, row):
    """Return (field, before_html, after_html) or None when no concrete edit."""
    edit = row.get("edit")
    if not edit:
        return None
    qtype = question["questionType"]
    content = question[qtype]
    field = edit["field"]

    if field == "answer":
        return ("answer", json.dumps(content.get("answer")), json.dumps(edit["replace"]))
    if field == "questionType":
        return ("questionType", qtype, edit["replace"])
    if field in ("question", "solution"):
        before = content.get(field) or ""
        find = edit["find"]
        if find == "(entire solution)":
            return (field, before, edit["replace"])
        if find in before:
            return (field, before, before.replace(find, edit["replace"], 1))
        # anchor not found verbatim: surface as suggestion rather than pretend
        return (field, before, before + f"\n<!-- PROPOSED: replace {find!r} with {edit['replace']!r} -->")
    return None


def main():
    questions = {q["_id"]: q for q in load("data", "questions.json")}
    results = load("results.json")
    analysis = {r["reportId"]: r for r in load("analysis.json")["reports"]}
    taxonomy = load("data", "taxonomy.json")
    bonus = load("analysis.json")["bonus_findings"]

    cases = []
    for row in results:
        q = questions[row["questionId"]]
        qtype = q["questionType"]
        diff = apply_edit(q, row)
        a = analysis[row["reportId"]]
        cases.append({
            "reportId": row["reportId"],
            "questionId": row["questionId"],
            "subject": q.get("subject"),
            "chapter": q.get("chapter"),
            "level": q.get("level"),
            "questionType": qtype,
            "questionHtml": q[qtype].get("question", ""),
            "solutionHtml": q[qtype].get("solution", ""),
            "storedAnswer": q[qtype].get("answer"),
            "errorHistory": q.get("errorHistory", []),
            "verdict": row["verdict"],
            "verdictLabel": taxonomy["verdicts"][row["verdict"]],
            "repair": row.get("repair"),
            "repairLabel": taxonomy["repairs"].get(row.get("repair"), {}).get("label") if row.get("repair") else None,
            "edit": row.get("edit"),
            "diff": ({"field": diff[0], "before": diff[1], "after": diff[2]} if diff else None),
            "route": row["route"],
            "confidence": row["confidence"],
            "evidence": row["evidence"],
            "studentReply": row["student_reply"],
            "doubleProof": bool(a.get("double_proof")),
        })

    # group by question; urgency ordering explained in PRODUCT.md:
    # faculty_review first (a human is the bottleneck), correctness-affecting
    # repairs before cosmetic ones, more student reports = more urgent.
    route_rank = {"faculty_review": 0, "auto_apply": 1, "no_change": 2}
    impact_rank = {
        "option_repair": 0, "identical_options": 1, "diagram": 2,
        "answer_key": 3, "type_mismatch": 4, "stem_data": 5,
        "solution_fix": 6, "wrong_chapter": 7, "syllabus": 8,
        "markup_leak": 9, "answer_form": 10, "exam_reference": 11, "spelling": 12,
    }
    groups = {}
    for c in cases:
        groups.setdefault(c["questionId"], []).append(c)
    ordered = []
    for qid, members in groups.items():
        best = min(members, key=lambda c: (route_rank[c["route"]],
                                           impact_rank.get(c.get("repair"), 20)))
        urgency = (route_rank[best["route"]],
                   impact_rank.get(best.get("repair"), 20),
                   -len(members))
        ordered.append((urgency, qid, members))
    ordered.sort(key=lambda t: t[0])

    out = {
        "generatedBy": "report-fix triage pipeline (precomputed results)",
        "queueOrder": [qid for _, qid, _ in ordered],
        "cases": cases,
        "bonusFindings": bonus,
    }
    dest = os.path.join(ROOT, "console", "data.js")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w") as f:
        f.write("window.CONSOLE_DATA = ")
        json.dump(out, f, ensure_ascii=False)
        f.write(";\n")
    print(f"wrote {dest}: {len(cases)} cases, {len(ordered)} question groups")


if __name__ == "__main__":
    main()
