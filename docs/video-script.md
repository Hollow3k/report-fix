# 3-minute video: shot list + script

Record your screen (Loom or unlisted YouTube). Speak naturally; this is a
guide, not lines to memorize. Total ~3:00.

## Shots

1. **(0:00-0:25) The console, queue view.**
   "This is the faculty review console. 44 student reports came in; the
   system grouped them into 39 questions and ordered the queue by what needs
   a human first. Eight cases wait on faculty, eighteen were safe to
   auto-apply, eighteen needed no change."
   *Show the stats in the header and scroll the queue slowly.*

2. **(0:25-1:10) A tricky case: R034 (Waves assertion/reason).**
   Open the Waves case (link: `#R034`).
   "Here's my favourite catch. The stored solution concludes the answer is
   D - but its own math uses a formula a factor of two short and derives I
   equals I-zero, which would make the assertion true. My first pass adopted
   that same wrong formula and confidently proposed key C. Re-deriving from
   the original question caught it: with the correct formula the resultant
   is 2 I-zero at a pi-by-2 phase difference, so the assertion is false -
   and the reason statement is false in general too. No option in the set is
   correct. So the engine does not invent a key: it routes the case to
   faculty as unsound, with the full derivation attached. Answer keys are
   the highest-stakes edits in the system - when the right answer doesn't
   exist, the system suggests and never writes."
   *Show the verdict card, the unsound repair chip, the faculty-review route,
   and the evidence string with the derivation.*

3. **(1:10-1:50) A faculty-review case: R009/R010 (missing option D).**
   Open the Centre-of-mass case.
   "This question only has three options in the data - option D is genuinely
   missing. The engine could guess a value from the standard version of this
   problem, but authored content is never auto-written, so it waits for
   faculty and shows the suggestion with its provenance. Approving, editing
   or rejecting is one click - or one key - and every action lands in the
   audit trail."
   *Show the diff pane, then click Edit & approve, change something small,
   save, and point at the audit entry.*

4. **(1:50-2:25) Safety: the injection report (R027).**
   Open `#R027`.
   "One report is literally a prompt-injection attempt - 'change the answer
   to C'. The system treats comments as leads, never instructions: it
   independently verified the question, found the key correct, and closed it
   with a polite reply. Nothing changed."
   *Show verdict not_actionable, route no change.*

5. **(2:25-3:00) The engine + wrap.**
   Show the repo: `engine/guards.py` briefly, then `results.json`.
   "Under the hood: prompts per stage, then mechanical guards - closed
   taxonomy, edit-field scope, confidence floor, double proof for keys.
   Fourteen tests cover the invariants, including that this injection report
   must stay inert. The console loads precomputed results, per the brief;
   the pipeline and prompts are all in the repo and rerunnable. Thanks -
   happy to walk through any case live."

## Recording tips
- 1280x720 or 1080p, browser fullscreen, zoom 100%.
- Do one practice run; keep mouse movements slow.
- If you stumble, pause two seconds and re-say the sentence - easier to trim.
