"""
Pipeline tests. Run: python3 -m pytest engine/test_pipeline.py  (or plain unittest)

Covers the invariants a live question bank actually cares about:
  - every report is triaged exactly once, schema-complete
  - verdicts / repairs / routes are closed-list
  - no edit ever escapes its repair's allowed fields
  - auto:false repairs are never auto-applied
  - high-stakes repairs require double proof to auto-apply
  - duplicate reports on one question get consistent verdicts
  - the injection report (R027) changed nothing
"""

import json
import os
import unittest

from guards import load_taxonomy, decide_route, validate_result_row, GuardError, MIN_AUTO_CONFIDENCE
from triage import build_results

_here = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_here, "..")


def load(*parts):
    with open(os.path.join(ROOT, *parts)) as f:
        return json.load(f)


class TestResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results, cls.log = build_results()
        cls.taxonomy = load_taxonomy()
        cls.reports = load("data", "reports.json")
        cls.analysis = load("analysis.json")["reports"]

    def test_all_44_reports_covered_once(self):
        self.assertEqual(len(self.results), 44)
        self.assertEqual(sorted(r["reportId"] for r in self.results),
                         sorted(r["reportId"] for r in self.reports))

    def test_schema_keys_and_types(self):
        need = {"reportId", "questionId", "verdict", "repair", "edit",
                "route", "confidence", "evidence", "student_reply"}
        for r in self.results:
            self.assertEqual(set(r.keys()), need, r["reportId"])
            self.assertIsInstance(r["confidence"], (int, float))
            self.assertTrue(0 <= r["confidence"] <= 1)
            self.assertTrue(r["evidence"].strip())
            self.assertTrue(r["student_reply"].strip())

    def test_closed_lists(self):
        for r in self.results:
            self.assertIn(r["verdict"], self.taxonomy["verdicts"])
            if r["repair"] is not None:
                self.assertIn(r["repair"], self.taxonomy["repairs"])
            self.assertIn(r["route"], ("auto_apply", "faculty_review", "no_change"))

    def test_edit_field_scope(self):
        for r in self.results:
            if r["edit"] is None:
                continue
            allowed = self.taxonomy["repairs"][r["repair"]]["fields"]
            self.assertIn(r["edit"]["field"], allowed, r["reportId"])

    def test_auto_false_never_auto_applied(self):
        for r in self.results:
            if r["repair"] and not self.taxonomy["repairs"][r["repair"]]["auto"]:
                self.assertNotEqual(r["route"], "auto_apply", r["reportId"])

    def test_non_defects_carry_no_edit(self):
        for r in self.results:
            if r["verdict"] != "defect":
                self.assertIsNone(r["edit"], r["reportId"])
                self.assertIsNone(r["repair"], r["reportId"])

    def test_high_stakes_auto_apply_needs_double_proof(self):
        proof = {a["reportId"]: bool(a.get("double_proof")) for a in self.analysis}
        for r in self.results:
            if r["repair"] in ("answer_key", "type_mismatch") and r["route"] == "auto_apply":
                self.assertTrue(proof[r["reportId"]], r["reportId"])

    def test_low_confidence_never_auto_applied(self):
        for r in self.results:
            if r["route"] == "auto_apply":
                self.assertGreaterEqual(r["confidence"], MIN_AUTO_CONFIDENCE, r["reportId"])

    def test_duplicates_on_same_question_agree(self):
        by_q = {}
        for r in self.results:
            by_q.setdefault(r["questionId"], []).append(r)
        for qid, rows in by_q.items():
            if len(rows) > 1:
                verdicts = {(r["verdict"], r["repair"]) for r in rows}
                self.assertEqual(len(verdicts), 1, f"{qid}: {verdicts}")

    def test_injection_report_is_inert(self):
        r027 = next(r for r in self.results if r["reportId"] == "R027")
        self.assertEqual(r027["verdict"], "not_actionable")
        self.assertEqual(r027["route"], "no_change")
        self.assertIsNone(r027["edit"])

    def test_known_ground_truths(self):
        """Hand-verified answers the pipeline must reproduce."""
        truth = {
            "R001": ("defect", "answer_key", "auto_apply", "A"),
            "R004": ("defect", "answer_key", "auto_apply", "D"),
            "R005": ("defect", "answer_key", "auto_apply", "1"),
            "R034": ("defect", "unsound", "faculty_review", None),
            "R017": ("already_fixed", None, "no_change", None),
            "R015": ("defect", "identical_options", "faculty_review", None),
            "R025": ("defect", "diagram", "faculty_review", None),
        }
        for rid, (v, rep, route, new_ans) in truth.items():
            row = next(r for r in self.results if r["reportId"] == rid)
            self.assertEqual(row["verdict"], v, rid)
            self.assertEqual(row["repair"], rep, rid)
            self.assertEqual(row["route"], route, rid)
            if new_ans:
                self.assertEqual(row["edit"]["field"], "answer", rid)
                self.assertEqual(row["edit"]["replace"], new_ans, rid)

    def test_unsound_question_carries_no_edit(self):
        """R034 has no valid option as written: suggest, never write."""
        row = next(r for r in self.results if r["reportId"] == "R034")
        self.assertIsNone(row["edit"])
        self.assertEqual(row["repair"], "unsound")
        self.assertEqual(row["route"], "faculty_review")


class TestGuardEdges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taxonomy = load_taxonomy()

    def test_edit_outside_scope_rejected(self):
        row = {"reportId": "X1", "verdict": "defect", "repair": "spelling",
               "edit": {"field": "answer", "find": "A", "replace": "B"},
               "route": "auto_apply", "confidence": .9,
               "evidence": "x", "student_reply": "x"}
        with self.assertRaises(GuardError):
            validate_result_row(row, self.taxonomy)

    def test_low_confidence_escalates(self):
        row = {"verdict": "defect", "repair": "spelling", "confidence": 0.5,
               "edit": {"field": "question", "find": "a", "replace": "b"}}
        route, _ = decide_route(row, self.taxonomy)
        self.assertEqual(route, "faculty_review")

    def test_no_double_proof_no_auto_answer_key(self):
        row = {"verdict": "defect", "repair": "answer_key", "confidence": 0.99,
               "edit": {"field": "answer", "find": "A", "replace": "B"}}
        route, _ = decide_route(row, self.taxonomy)
        self.assertEqual(route, "faculty_review")


if __name__ == "__main__":
    unittest.main(verbosity=2)
