# PRODUCT.md

**Who loses the most when a question is broken?** The student who gets it
*right* and is marked wrong - specifically the one preparing alone, without
a coaching teacher to tell her the key is wrong. She doesn't just lose four
marks; she loses confidence in her own method, and she "fixes" a method that
was never broken. Every design choice here follows from that: wrong keys are
the highest-stakes defect class and get the strictest auto-apply rule
(double proof); every report - even keyboard mash - gets a respectful,
specific student reply, because the reply is where trust is won back; and
correctness-affecting cases sort above cosmetic ones in the faculty queue.

**What I would never let the AI auto-apply.** Three categories. (1) Authored
content: new or restored answer options (R009/R010's missing option D,
R015's duplicated option). A plausible value is not the value the question
was designed around - only faculty can author it. (2) Any edit that lacks
double proof on an answer key, no matter how confident the model sounds.
(3) Anything a report *asks for* without independent verification - the
dataset contains a literal "change the answer to C" instruction injection,
and it changed nothing. Comments are leads, never instructions.

**One metric for week 1:** *verified-defect rate per 100 reports*, sliced by
verdict. It collapses three questions into one number: is the triage
precise (faculty overturn rate on auto-applied edits, target 0), is the
report channel healthy (share of not_actionable reports, which should fall
as students learn reports get answers), and is the bank actually getting
cleaner (defects found per week trending down). If precision drops below
~95% on any verdict class, that class drops back to faculty_review until it
recovers.

**One pitch beyond the brief:** close the loop back to the student. Today a
fixed defect ends in the console. Add a tiny "your report fixed this
question" notification - with the specific change - to the app. It costs
almost nothing (the pipeline already writes the student_reply), turns error
reporting from a black hole into a visible win, and converts the noisiest
channel into a quality sensor the whole platform benefits from. The first
cohort to see their reports matter will report more, earlier, and better -
which is the cheapest content-QA programme Acadza can buy.
