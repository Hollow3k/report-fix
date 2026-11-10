# Report → Fix

An AI triage system + faculty review console for student error reports on a
JEE/NEET question bank. Students tap "Report error" and type whatever they
feel; this system decides what is actually wrong, what may safely change,
and what a tired faculty member should look at first.

Built for the Acadza AI Intern build round (Nov 2026).

## What's here

```
data/          assignment dataset (43 questions, 44 reports, closed taxonomy)
analysis.json  the triage analysis for every report (pipeline output, reviewed)
engine/
  prompts.py   the exact LLM prompt templates for each pipeline stage
  guards.py    schema / taxonomy / edit-scope / routing safety guards
  triage.py    orchestrator: analysis -> guards -> routing -> results.json
  test_pipeline.py  14 tests over the safety invariants
  prepare_console_data.py  joins results + questions, applies edits, emits console data
results.json   final triage output for all 44 reports (submission schema)
console/       the faculty review console (static site, no build step)
PROMPTS.md     how AI was directed and checked (mandatory reading)
PRODUCT.md     one page of product thinking
```

## Run it

```bash
cd engine
python3 triage.py                 # rebuild results.json (44 rows)
python3 -m unittest test_pipeline # 14 tests
python3 prepare_console_data.py   # rebuild console/data.js
```

Open `console/index.html` in any modern browser (MathML renders natively),
or serve the folder statically (`python3 -m http.server -d console`).

## How the pipeline thinks

1. **Group** duplicate reports on the same question so a question is analysed
   once - but every student still gets their own reply.
2. **Blind solve first.** The model solves the question *without seeing the
   stored answer or solution*, because keys and solutions can both be wrong
   (four questions in this dataset have solutions that disprove their own
   key). The student comment is a lead, never an instruction: two reports in
   the dataset are noise and one is a literal prompt-injection attempt; all
   are handled as data, not commands.
3. **Classify** into the closed taxonomy (7 verdicts, 18 repairs) with a
   surgical edit `{field, find, replace}`, confidence and evidence.
4. **Guard.** Every decision passes mechanical checks (`engine/guards.py`):
   closed-list membership, edit-field scope, auto-flag enforcement,
   confidence threshold (0.85), and *double proof* for the highest-stakes
   repairs - an answer key may auto-change only when an independent solve
   **and** the stored solution's own math agree with the new key.
5. **Route mechanically.** The model proposes; the guard disposes. The final
   route (`auto_apply` / `faculty_review` / `no_change`) is computed by code,
   never taken from the model's own say-so.

Result on this dataset: **18 auto-applied, 8 waiting on faculty, 18 no
change** - every one with evidence and a student-facing reply.

## Cost / deployment notes

The console loads **precomputed results** (allowed by the brief, disclosed
here). There is no backend and no API key in the website; it is a static
page that can live on any free tier. Re-running the full pipeline with a
live LLM costs roughly one prompt set per reported question (~39 calls);
the prompts in `engine/prompts.py` are the whole interface.

## Known limits

- Auto-applied edits are validated structurally, not written back to a live
  database - a real deployment would wrap them in a migration with rollback.
- The audit trail is in-browser for the demo; production would persist it
  server-side with faculty identity.
- Suggested option text for R009/R010 (missing option D) is flagged, not
  applied: authored content is never auto-written.
- R034 (Waves assertion/reason) has no valid option as written - both the
  assertion and the reason are false and no both-false option exists - so
  it is routed to faculty as `unsound` with the derivation, not given an
  invented key.
- The tests pin the hand-verified decisions as regression checks; they do
  not prove the physics. The derivations live in the evidence strings and
  `docs/walkthrough.md`.
