# Acceptance criteria — Provenance Guard

Five criteria that say what "working" means for this service, written in unit 7
**before** you built it.

**All five are yours.** None are given.

An acceptance criterion names a number or something plainly observable. *"The
detector is accurate"* is an opinion — and perfect AI detection isn't possible
anyway, so it's an opinion about something nobody can deliver. *"Of 10 pieces I
wrote myself, at most 1 is labelled high-confidence AI"* is a criterion.

Under each, write a sentence or two on **why that target**. *"I allow at most 1
false positive in 10 because on a writing site a wrong accusation costs more
than a missed detection"* is a real answer.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## Pick numbers you can defend

**Cover at least three of these five areas.** They're prompts, not a form.

| Area | A question it could answer |
|---|---|
| False positives | How often may a human's writing get called AI? |
| Score spread | How far apart should clearly-AI and clearly-human text score? |
| Label coverage | Is every one of your three labels actually reachable? |
| The appeal path | Does an appeal always change status and always get recorded? |
| Bad input | What happens when `text` is missing, empty, or enormous? |

Two things worth knowing before you pick numbers:

- **The expensive mistake is one-sided.** Missing some AI text costs the site a
  little. Accusing a real writer costs that person a lot. A criterion that
  treats both errors as equally bad is describing a system nobody would ship.
- **Unit 8 tests across three trials, and the target has to hold across all
  three.** Your first signal runs a model, so identical input can score
  differently twice. A target of "at most 1 in 10" against trials of 2, 1, 2 is
  a **miss**.

---
## 1. Human writing is almost never labelled high-confidence AI

Of 10 texts I wrote myself, at most 1 receives the high-confidence AI label,
and this holds in each of 3 trials. Landing in the "unsure" label does not
count as a false positive.

**Why this target:** On a writing site, wrongly accusing a real writer costs
that person far more than missing some AI text costs the site. I allow 1 in 10
because the first signal runs a model and can't be perfect, but I count only
the high-confidence label as an accusation, since "unsure" invites a closer
look and doesn't blame anyone.

---

## 2. Clearly-AI and clearly-human text score far apart

Across 5 clearly-AI and 5 clearly-human texts, the mean AI score is at least
0.4 higher than the mean human score, and the lowest AI score is above the
highest human score. This holds in each of 3 trials.

**Why this target:** A detector that gives everything 0.5 has a tiny spread
and is useless. Requiring a gap of 0.4 and no overlap on obvious cases shows
the score actually separates the two kinds of text, which the labels depend on.

---

## 3. Every label is reachable and none dominates

Across a 12-text test set (4 clearly human, 4 clearly AI, 4 borderline), each
of the three labels appears at least twice, and no label covers more than 60%
of the results (7 of 12).

**Why this target:** A label nobody can reach is dead code, and a label that
takes most results means the thresholds are badly placed. I chose a test set
with known categories so the spread isn't just a product of whatever inputs I
happened to pick.

---

## 4. Appeals always change status and are always recorded

In 10 submitted appeals, 10 (100%) change the record's status to "under
appeal" and are stored with a timestamp and the writer's explanation. An
appeal never clears a record automatically.

**Why this target:** Whether an appeal is recorded is a rule, not a
probability. If even one in four appeals goes missing, the audit trail is
broken and a wrongly accused writer has no recourse. Whether the appeal later
changes the verdict is a separate human decision, so it isn't part of this
target.

---

## 5. Bad input is handled explicitly

- Missing, empty, or whitespace-only `text` returns HTTP 400 with an error
  message, and nothing is stored.
- Text over 50,000 characters returns HTTP 200 with a `warning` field and a
  complete analysis.

All 4 cases (missing, empty, whitespace-only, over 50,000 characters) are
checked in each of 3 trials and must behave as described.

**Why this target:** A silent failure on empty input could produce a score for
nothing, and a crash on long input would punish writers with long pieces. The
split is deliberate: empty text can't be analysed, so it is rejected, while
long text can be analysed, so it is analysed with a warning. 50,000 characters
gives "enormous" a number I can pass or fail.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 8 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath, like this:

         ## 2. Uncertain cases land in the unsure band

         The system handles uncertain cases well.

         **Why this target:** ...

         > **Revised in unit 8:** Text I judged borderline scores between
         > 0.4 and 0.6 in at least 4 of 5 cases.
         >
         > **Why revised:** "well" gave me nothing to check. I couldn't
         > reach a verdict from it at all.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "At most 1 of 10 of my own pieces flagged as AI" → "at most 3
            of 10", because 1 of 10 turned out to be hard.

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
