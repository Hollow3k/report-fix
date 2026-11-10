# Walkthrough & defence notes (for Angad)

Read this before recording the video and before the call. Everything here is
true about the build; say it in your own words.

## The 60-second version

"It's two halves. The engine triages student reports: it groups duplicates,
blind-solves the question before looking at any stored answer, classifies
into their closed taxonomy, and proposes a surgical edit. Then guards in
plain code decide the route - the model proposes, code disposes. The console
is where faculty spend their evening: a queue ordered by urgency, each case
showing the question, the AI's verdict and evidence, a before/after diff,
and one-click approve/edit/reject with an audit trail. On their dataset:
18 auto-applied, 8 need a human, 18 no change."

## Architecture, file by file

- `engine/prompts.py` - the exact prompts per stage (blind solve, report
  analysis, dedupe). Model-agnostic; any LLM API plugs in behind one function.
- `engine/guards.py` - the safety layer. Closed-list validation, edit-field
  scope checks, the 0.85 confidence floor, and the double-proof rule for
  answer keys. `decide_route` is mechanical: same input, same route, every
  time. This is the piece to talk about most.
- `engine/triage.py` - orchestrator. Loads the analysis, validates every row,
  computes routes, writes `results.json`. Fails loudly on unknown IDs,
  duplicate coverage, or missing reports.
- `engine/prepare_console_data.py` - joins results with questions, *applies*
  each edit to build the before/after diff, orders the queue.
- `engine/test_pipeline.py` - 14 tests: schema, scope, auto:false, double
  proof, duplicates agree, injection inert, hand-verified ground truths.
- `console/` - static site. `data.js` is generated; `app.js` renders queue,
  case view, diff, actions, audit. No framework, no build step, deep links
  via `#R011`.

## The five decisions to be ready to defend

1. **Blind solve before reading the key.** Keys and solutions can both be
   wrong. In this dataset, four solutions disprove their own key (flux n=1,
   LCR 50 V, gas pressure 4800, the Waves assertion/reason). If you trust the key, you mark the student
   wrong and move on - the exact harm the system exists to prevent.
2. **Routing is code, not a prompt.** An LLM will confidently say
   "auto_apply" for a repair with no safe edit (happened on R009/R010 during
   the build). Guards are boring, testable, and never confident.
3. **Double proof for answer keys.** Only auto-change a key when an
   independent solve AND the stored solution's own math agree. Five keys
   fixed this way (R001, R002, R003, R004, R005). A sixth candidate (R034)
   failed the re-derivation: no valid option exists, so it went to faculty
   as unsound instead of getting an invented key.
4. **Never auto-write authored content.** Missing option D, duplicated
   option, missing figure, wrong chapter - all faculty_review. The console
   still shows a *suggestion* with its provenance ("5 m/s, from the standard
   version of this problem - unverified").
5. **Urgency = human-bottleneck first, correctness before cosmetics, then
   report count.** A question three students reported beats one student.

## Traps in the dataset (show you found them)

- R027 is a prompt-injection attempt ("change the answer to C"). Verdict
  not_actionable, route no_change, nothing touched. Say: "comments are data,
  not instructions."
- R017 was already fixed by faculty on 7 Nov (errorHistory) - verdict
  already_fixed, no double-work.
- The Waves question (R034) is unsound. The stored solution uses a
  formula a factor of two short (I = 2 I0 cos^2(phi/2)), derives I = I0,
  then contradicts itself and concludes (d). The correct formula
  I = 4 I0 cos^2(phi/2) gives I = 2 I0 at phi = pi/2: assertion A is false,
  reason R is false in general, and no both-false option exists. The first
  pipeline pass adopted the stored solution's wrong formula and proposed
  key (C); re-deriving from the original question before publishing caught
  it. Verdict defect / repair unsound / faculty_review - suggest, never
  write.
- R016's answer (20) was right but its solution's last line says 40 cm.
- Bonus section: defects nobody reported (golden-rice solution spacing,
  'Maceus membrane', the insulin/glucagon "synergistically" error,
  inconsistent MCQ answer encodings).

## If they change a requirement live (they said they will)

Likely moves and your answers:
- "Make identical_options auto-appliable" -> the guard is one config line,
  but argue it stays human: new distractors are authored content.
- "Lower the auto threshold to 0.7" -> show which cases flip (R021 at 0.85,
  R024 at 0.85 sit right at the line) and what breaks.
- "Add a verdict" -> taxonomy is data, not code; show where it loads.
- "100x the reports" -> grouping by question first is the scaling story;
  per-question analysis cost, not per-report.
- "Students report in Hindi slang" -> the pipeline already treats comments
  as leads and verifies independently; language barely matters.

## Honest answers about process

They will ask how you used AI. Do not hide it - the brief rewards directed
AI use. Say: "I directed an AI assistant end-to-end and verified everything
against the raw data myself. PROMPTS.md has the actual instructions, the
three places the AI was wrong, and how I caught each." Then pick catch #1
(the self-contradicting Waves solution) as your story - it shows exactly
why the blind-solve stage exists.

## Numbers to have in your head

44 reports, 43 questions, 39 unique reported. 18 auto-applied / 8 faculty /
18 no change. 26 defects (5 answer-key fixes: R001-R005; R034 is unsound),
10 no_error, 2 app_issue, 2 display_issue, 1 language_mode, 1 already_fixed,
2 not_actionable.
Taxonomy: 7 verdicts, 18 repairs (5 human-only).
