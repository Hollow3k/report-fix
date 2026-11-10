"""
Safety guards for the Report -> Fix pipeline.

Every LLM (or precomputed) triage decision passes through here before it is
allowed to touch data. The guards are deliberately dumb and strict; anything
they cannot prove safe is escalated to faculty_review. A wrong auto-edit on a
live question bank hurts every student who meets the question, so the guards
err on the side of doing nothing.

Policy implemented:
  1. Verdicts and repairs must come from the closed taxonomy.
  2. An edit may only touch the fields its repair lists in the taxonomy.
  3. Repairs marked auto: false can never be auto-applied.
  4. Non-defect verdicts never carry an edit and always route no_change,
     except that faculty may still be asked to look (faculty_review) when
     confidence is low.
  5. answer_key is the highest-stakes repair: it auto-applies only when the
     analysis carries double_proof=True - i.e. an independent blind solve AND
     the stored solution's own math agree with the new key.
  6. Confidence below MIN_AUTO_CONFIDENCE forces faculty_review.
  7. Structural schema validation of every result row.
"""

import json
import os

MIN_AUTO_CONFIDENCE = 0.85
HIGH_STAKES_REPAIRS = {"answer_key", "type_mismatch"}

_here = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(_here, "..", "data")


def load_taxonomy(path=None):
    path = path or os.path.join(DATA, "taxonomy.json")
    with open(path) as f:
        return json.load(f)


class GuardError(Exception):
    pass


def validate_result_row(row, taxonomy):
    """Raise GuardError unless the row is schema-clean and taxonomy-clean."""
    verdicts = taxonomy["verdicts"]
    repairs = taxonomy["repairs"]

    if row["verdict"] not in verdicts:
        raise GuardError(f"{row['reportId']}: unknown verdict {row['verdict']!r}")
    repair = row.get("repair")
    if repair is not None and repair not in repairs:
        raise GuardError(f"{row['reportId']}: unknown repair {repair!r}")

    edit = row.get("edit")
    if edit is not None:
        if repair is None:
            raise GuardError(f"{row['reportId']}: edit without a repair")
        allowed = repairs[repair]["fields"]
        if edit["field"] not in allowed:
            raise GuardError(
                f"{row['reportId']}: repair {repair} may not touch {edit['field']!r}")
        if row["verdict"] != "defect":
            raise GuardError(f"{row['reportId']}: edit on a non-defect verdict")
        if not edit.get("replace") and edit["replace"] != "":
            raise GuardError(f"{row['reportId']}: edit has no replacement")

    if row["route"] not in ("auto_apply", "faculty_review", "no_change"):
        raise GuardError(f"{row['reportId']}: unknown route {row['route']!r}")

    if not isinstance(row.get("confidence"), (int, float)):
        raise GuardError(f"{row['reportId']}: confidence must be numeric")
    if not row.get("evidence"):
        raise GuardError(f"{row['reportId']}: evidence is required")
    if not row.get("student_reply"):
        raise GuardError(f"{row['reportId']}: student_reply is required")
    return True


def decide_route(analysis_row, taxonomy):
    """
    Mechanical, explainable routing. Returns (route, reasons[list[str]]).
    The LLM proposes; the guard disposes. The route in results.json always
    comes from here, never from the model.
    """
    repairs = taxonomy["repairs"]
    verdict = analysis_row["verdict"]
    repair = analysis_row.get("repair")
    conf = analysis_row.get("confidence", 0.0)
    reasons = []

    if verdict != "defect":
        if conf < MIN_AUTO_CONFIDENCE:
            reasons.append(f"non-defect but low confidence ({conf}) - human glance")
            return "faculty_review", reasons
        reasons.append("no content defect found - nothing to change")
        return "no_change", reasons

    if repair is None:
        reasons.append("defect with no actionable repair - human triage")
        return "faculty_review", reasons

    entry = repairs[repair]
    if not entry["auto"]:
        reasons.append(f"repair '{repair}' is human-only per taxonomy (auto: false)")
        return "faculty_review", reasons

    if analysis_row.get("edit") is None:
        reasons.append("auto-eligible repair but no concrete edit proposed")
        return "faculty_review", reasons

    if conf < MIN_AUTO_CONFIDENCE:
        reasons.append(f"confidence {conf} below auto threshold {MIN_AUTO_CONFIDENCE}")
        return "faculty_review", reasons

    if repair in HIGH_STAKES_REPAIRS:
        if not analysis_row.get("double_proof"):
            reasons.append(
                f"'{repair}' is high-stakes and lacks double proof "
                "(independent solve + stored solution agreement)")
            return "faculty_review", reasons
        reasons.append(f"'{repair}' auto-applied: double proof on record")
    else:
        reasons.append(f"repair '{repair}' auto-eligible, guards passed")

    return "auto_apply", reasons
