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

> **Revised in unit 8:** Of 10 texts I wrote or collected as genuine human
> writing, at most 1 receives the high-confidence AI label, in each of 3
> trials. At least 4 of the 10 must be in a register the detector is likely to
> misread: formal prose, writing to a rubric, a careful non-native speaker, or
> deliberate repetition.
>
> **Why revised:** The original number was checkable, but the test set could
> not fail it. My 10 texts were casual or ordinary, 8 of 10 landed in "unsure",
> and the criterion passed at exactly 1 of 10 in all 3 trials. The attack run
> then accused 6 of 8 formal or templated human texts (FP02 to FP07). A target
> that passes while the system accuses 6 of 8 of the writers it most needs to
> protect was not measuring what I meant. The limit of 1 in 10 is unchanged.
> Only the population it is measured on changed.

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


---
---

# Unit 9 criteria — the observability extension

Unit 9 added instrumentation around the existing service without changing what
it decides: a `run_id` on every request, stage timings with model time split
from overhead, token and compute-second cost, one execution record per request
(`logs/runs.jsonl`), one failure record per failure (`logs/failures.jsonl`),
link monitoring (status codes, rate-limit hits, availability), and aggregation
in `metrics.py` and `/metrics`.

All five criteria below are about that extension. Criterion 2 is the bad path,
and criterion 5 covers both the bad path of the extension itself and the
promise that the original system is unchanged.

"Warm" means after the first request since the service started (the first one
pays a one-time model load of 2 to 4 seconds). Targets hold in each of 3
trials.

---

## U9-1. Every request can be traced from response to log

In a batch of 20 requests (10 valid `/submit`, 3 refused inputs, 2 over the
rate limit, 3 `/ping`, 2 `/health`):

- all 20 responses carry an `X-Request-ID` header;
- the 20 ids appear in `logs/runs.jsonl` exactly once each (20 ids, 20 records,
  no duplicates, none missing);
- each of the 15 requests that write to the audit log (10 decisions, 3
  refused inputs, 2 rate-limited) has an `audit.jsonl` entry carrying the same
  `run_id`.

Target: 20 of 20, and 15 of 15.

**Why this target:** The `run_id` is the join key between three files, so
whether it is present is a rule, not a probability. Looser (19 of 20) means one
request can't be followed, and the one that can't be followed is the one I will
be searching for, the same trap unit 8 taught with rate-limited requests that
left no trace. Stricter isn't possible, because 100% is already the maximum.

---

## U9-2. Every refused or failed request leaves exactly one correct failure record

In a batch of 5 non-2xx requests:

| Request | Response | Stage | Category |
|---|---|---|---|
| text is only spaces | 400 | `validate` | `validation_failure` |
| `text` field missing | 400 | `validate` | `validation_failure` |
| 7th request from one `creator_id` within a minute | 429 | `request` | `rate_limit` |
| 8th request from the same `creator_id` | 429 | `request` | `rate_limit` |
| valid 40+ word text, service started with `AI201_DETECTOR_MODEL=not-a-real-model-xyz` | 500 | `model_signal` | `model_unavailable` |

`logs/failures.jsonl` gains exactly 5 records (none missing, none extra), each
with the `run_id` from that response's `X-Request-ID`, the stage and category in
the table, and a non-empty `message`. The HTTP status of each response is the
same as it was before instrumentation.

Target: 5 of 5.

**Why this target:** A failure that shows up only as an absence is one I will
never find, so a missing record is the failure this criterion exists to catch.
The category matters as much as the count: `metrics.py` counts only 5xx
responses as errors, so a model-load failure filed under `validation_failure`
would leave the error rate at 0.0 while the service was down. That is why I
check stage and category and not just that a record exists. Looser (4 of 5)
would let one whole class of failure go unrecorded.

---

## U9-3. Recorded timings agree with an independent clock

Over 20 warm `/submit` requests sent over real HTTP, measured with a stopwatch
in the client (`requests` elapsed time):

- for each request, the recorded `duration_ms` is within 15 ms of the
  client-measured time;
- for each request, the stage durations add up to at least 98% of
  `duration_ms`.

Target: 20 of 20 on both.

**Why this target:** A timing number nobody has compared to another clock is a
claim, not a measurement. I measured the gap on this laptop: client time
exceeded the recorded time by 1.0 to 5.1 ms (loopback HTTP and thread
hand-off), and the stages covered 99.5 to 99.7% of each request. 15 ms is about
three times the largest gap I saw and half of a typical 31 ms request, so it
passes normal noise but would catch a missing stage. Stricter (5 ms) would fail
on that noise and not on an error. Looser (100 ms) is more than three whole
requests, which would hide an untimed stage entirely, and it could never
distinguish model time from overhead, which is the point of recording them
separately.

---

## U9-4. `/metrics` reproduces what a recount of the raw logs gives

After a batch of 21 requests (16 successful, 3 refused inputs, 2 rate-limited),
the following figures from `GET /metrics` match a recount done by hand from
`runs.jsonl` and `failures.jsonl`:

1. total requests (21);
2. requests by outcome (16 ok, 3 client_error, 2 rate_limited);
3. rate-limit hits (2);
4. total failures (5);
5. total input tokens (summed from the run records);
6. request p50 latency (equal to the median of the recorded `duration_ms`, to 3
   decimals).

Target: 6 of 6 exact.

**Why this target:** `metrics.py` stores nothing; it recomputes from the files
on every call, so any difference is a bug and not noise. Exact is the only
honest tolerance: the rare events are the ones that matter, and a 5% tolerance
on 2 rate-limit hits out of 21 would accept 0 hits and call the link healthy.
A dashboard that disagrees with its own source data is worse than none, because
people act on it.

---

## U9-5. Telemetry never changes or blocks a response

Two checks of one rule:

- **Same answers:** for 10 fixed texts, the `/submit` response with telemetry
  on and with `AI201_TELEMETRY=0` has the same keys and the same `guess`,
  `label`, `confidence`, `model_score` and `style_score`. Target: 10 of 10.
- **Telemetry down:** with `logs/runs.jsonl` and `logs/failures.jsonl` replaced
  by directories of the same names (real files moved aside first and restored
  after), 10 valid submissions still return 200 with a full response and 1
  blank-text submission still returns 400. Target: 11 of 11.

**Why this target:** Unit 9's scope was to monitor the system "without
changing its classification behavior". A writer's verdict must not depend on
whether a measurement tool is running, so even one differing score means the
instrumentation altered what a person is told. The second check is the bad path
of the extension itself: if a full disk or a bad permission on a log file could
turn a writer's submission into a 500, the monitor would be the most fragile
part of the service. Both checks are deterministic in this system (the same
text gives the same scores), so 100% is achievable and anything less is a real
defect.
