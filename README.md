# Provenance Guard

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first.**
>
> Once `python test.py` passes, in one terminal:
>
> ```bash
> python app.py
> ```
>
> and in another:
>
> ```bash
> curl -X POST http://127.0.0.1:5000/ping \
>   -H "Content-Type: application/json" \
>   -d '{"message": "hello"}'
> ```
>
> That's a web service. Something sent it text and it sent something back.
> Everything this unit is filling in the middle.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     Unit 7 asks for the first five sections. Unit 8 adds the five below.

     Everything is pasted as TEXT. A pasted curl response gets full credit;
     a picture of your terminal gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- The path a submission takes, from arriving to the label a reader sees.
     Six or seven steps — this is the trace you wrote in Milestone 1. -->



---

## Signals and Scoring

<!-- For each signal: what property it measures, why that might differ between
     human and AI writing, and WHAT IT CAN'T SEE.

     The blind spot is not optional. If you can't name it you don't understand
     the signal yet — and unit 8's attack set is built out of blind spots. -->

### Signal one — the model signal

**What it measures:**  How surprised GPT-2 is by the text, on average, per token. A perplexity of 53.6 means that at each step the model was about as unsure as if it were choosing among roughly 54 equally likely next tokens. Lower means more predictable (the text sticks to common words and common phrasings, which is what a model tends to produce), higher means more surprising (rare words, odd turns). It is not a measure of quality or authorship, only of predictability to this particular model. It also depends on length and topic, so the raw number isn't comparable across very different texts, which is why `model_signal` converts it into a 0–1 score instead of using it directly. 

**Why that might differ between human and AI writing:** The AI generated text will have more predictable words in sequence than human generated text.

**What it can't see:** Maybe how a writter using their second or third language still communicates by overthinking wording and how they might choose options that do not have high variability but are safest options, adn hence more predictable and resemble more AI-like text 

### Signal two — the style signal

**What it measures:** A 0–1 score (higher = more likely AI) built only from the shape of the text, without understanding any of it: how much sentence lengths vary, how much of the vocabulary repeats, and how much and what kind of punctuation there is. The idea is that generated prose tends toward even, mid-length sentences and a narrower vocabulary, while human writing is lumpier. It measures something different from perplexity: signal one asks "is this predictable?", this one asks "does this look uniform?". For this text it currently means very little. The stub returns a fixed 0.5, and even a real implementation would have nothing to work with on one short sentence, so a style score here should be read as "no evidence either way".

**Why that might differ between human and AI writing:** AI writting follows the patetrns and style it has seen through training, while humans curate their style by how they write, or the words they are prone to use, or maybe being more used to certain styles or figures of speech (such as metaphor, simile, etc).

**What it can't see:** Someone might have a very coarse style or a style that is simmilar to the patterns AI has seen throughought its training (and hence, patters it also uses). Moreover, in short texts, it is very difficult to see a distinctive patters

### The combining rule

<!-- Write the rule in words, then give the numbers. What happens when the two
     signals disagree? -->

**The rule:**

**The numbers:**

**Where it lives:** `scoring.py::combine_signals`

<!-- ⚠️ The grader checks your code against that line. If your rule lives
     somewhere else, say where. -->

**A case where my two signals split, and what my rule does with it:**



---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human |  |  |
| unsure |  |  |
| high-confidence AI |  |  |

**Why I worded the "unsure" one this way:**
<!-- It's the hardest of the three. It has to admit uncertainty without
     sounding like an accusation, because the person reading it may well have
     written every word themselves. -->



---

## Sample Run

<!-- One submission and one appeal, pasted as text: the request, the response,
     and the log entries. -->

**A submission**

<!-- The response needs content_id, guess, confidence, label, AND both
     signal scores - model_score and style_score. Unit 8's tools read those
     two off the response, so leaving them out costs you next unit's
     diagnostics. -->

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "She is both the tempest and the halcyon an element of nature in its most genuine form. Never meant to be contained, simply made to be admired.", "creator_id": "camila"}'
```

```json
-H "Content-Type: application/json" \
  -d '{"text": "She is both the tempest and the halcyon an element of nature in its most genuine form. Never meant to be contained, simply made to be admired.", "creator_id": "camila"}'
{
  "confidence": 0.73,
  "content_id": "887f326e-4095-4f44-aa6c-2c94c2c4fe04",
  "guess": "ai",
  "label": "likely_ai",
  "model_score": 0.2349,
  "style_score": 0.65
}
```

**An appeal**

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "...", "reasoning": "..."}'
```

```json

```

**What the log shows afterwards**

```bash
$ curl "http://127.0.0.1:5000/log?limit=3"
```

```json

```

---

## How I Used AI

**Moment 1**

- *What I asked for:* Guidance on code section where I got too many errors (in this case how to unpack from payload or how to succesfully catch errors on the payload being a dict or not)
- *What came back:* instructions and clues on how the code unfolds, for example: What to pass. Check the signature at audit.py:35. It takes content_id, creator_id, guess, model_score, style_score, combined_score, label and status. Everything after creator_id defaults to None.
- *What I changed:* I wrote the code since the agent did not provide it but provided instructions

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** ___ per minute, ___ per day

**Why those numbers and not others:**
<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->

**What a caller counts as:** <!-- per address, or per creator_id? They fail
differently — one script can look like a thousand callers, and one household
can look like one. -->

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```

```

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->



**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json

```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |
| 2.  |  |  |  |  |  |
| 3.  |  |  |  |  |  |
| 4.  |  |  |  |  |  |
| 5.  |  |  |  |  |  |

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

```json

```

**Diagnoses**

<!-- For each miss AND each broken attack: the stage and the mechanism.

     Your service has five stages: the route, signal one, signal two, the
     combining rule, and the label mapping.

     Not a diagnosis:  "The evasion attacks got through."
     A diagnosis:      "Four evasion inputs got through. All four had typos
                        added to AI-generated text. My second signal measures
                        word variety, and typos raise word variety — so it read
                        them as more human. My combining rule weights that
                        signal at 0.6, so it dragged the whole score down."

     Look for a pattern. Five failures on one signal is one problem, not five. -->



---

## The Improvement

**What I changed:**

**Which diagnosis pointed at it:**

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->



**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->



---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->



**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [ ] criteria.md has five numbered criteria, each naming a target
       [ ] Each has a reason underneath
       [ ] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [ ] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [ ] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [ ] Rate limiting on /submit, with your numbers justified
       [ ] The pasted run of status codes showing 429
       [ ] Audit log with all nine fields, recording rejections too
       [ ] The attack set run IN FULL, every input with an outcome
       [ ] Ten audit log entries pasted as text
       [ ] Five criteria across three trials
       [ ] A diagnosis for every miss and every broken attack — stage AND mechanism
       [ ] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**

# Tracing a Run - Pre-Build.

## Trace of: "She is both the tempest and the halcyon"

Output 
`
perplexity: 53.6
model signal: 0.4302
style signal: 0.5
`

## Steps 

### Step 0: /submit request (file: app.py)
**What happens:** The request arrives as JSON: `{"text": "She is both the tempest and the halcyon", "creator_id": "..."}`. `submit()` reads it with `request.get_json(silent=True) or {}`, pulls out `text` and `creator_id`, and generates a `content_id = str(uuid.uuid4())` that `/appeal` will need later.

**Design decision:** Is this input scorable at all? It is 8 words, one sentence, no final punctuation. I have to decide what the route does with empty, missing, very short or over-400-token text: reject, score with a warning, or return `unsure` ("too short to judge"). Any refusal should still be written with `audit.log_rejection`. Also: what the client sees if `DetectorUnavailable` or `ValueError` is raised (neither is caught today).

**AI vs human:** Not decided here. This is the gate that decides whether the system should attempt the differentiation.

### Step 1: detector.model_signal(text)  (file: detector.py)
**What happens:** `perplexity(text)` loads GPT-2 once (`_load()` caches it in `_model`), tokenizes the text (truncated at `DETECTOR_MAX_TOKENS` = 400), and refuses fewer than 3 tokens. It then runs `model(input_ids, labels=input_ids)` under `torch.no_grad()`. The loss is the mean negative log-likelihood per token (the first token is never scored), and `exp(loss)` is the perplexity. Measured: **53.6**. `model_signal` squashes it with `1 / (1 + (ppl / 45) ** 1.6)` into **0.4302** (higher = more likely AI).

**What perplexity means:** How surprised GPT-2 is by the text, on average, per token. A perplexity of 53.6 means that at each step the model was about as unsure as if it were choosing among roughly 54 equally likely next tokens. Lower means more predictable (the text sticks to common words and common phrasings, which is what a model tends to produce), higher means more surprising (rare words, odd turns). It is not a measure of quality or authorship, only of predictability to this particular model. It also depends on length and topic, so the raw number isn't comparable across very different texts, which is why `model_signal` converts it into a 0–1 score instead of using it directly. Here the rare words "tempest" and "halcyon" push it up, while the common words around them pull it down.

**Design decision:** The midpoint (45) and steepness (1.6) are given, not mine. I should recalibrate them against the four calibration inputs and document it. I also need to decide whether short text should pull the score toward 0.5.

**AI vs human:** This is where it is first decided (signal one). Low perplexity reads as AI, high as human. Here 53.6 is just above the midpoint, which reads as slightly human. But with about 10 tokens and rare words ("tempest", "halcyon") the reading is noisy, so 0.43 really means "can't tell".

### Step 2: stylometry.style_signal(text) (file: stylometry.py)
**What happens:** `sentences()` splits on whitespace after `.`, `!` or `?` (1 sentence here). `words()` lowercases and keeps `[a-z0-9']+` (8 words, 7 unique). The three measures are then combined into one 0–1 score, same direction as signal one. Today they are stubs, so the output is the placeholder **0.5**. Hand-computed for this text:

- `sentence_length_spread`: undefined (one sentence, `stdev` needs two values)
- `type_token_ratio`: 7/8 = 0.875, high only because the text is short
- `punctuation_density`: 0 marks, ambiguous

**What style signal means:** A 0–1 score (higher = more likely AI) built only from the shape of the text, without understanding any of it: how much sentence lengths vary, how much of the vocabulary repeats, and how much and what kind of punctuation there is. The idea is that generated prose tends toward even, mid-length sentences and a narrower vocabulary, while human writing is lumpier. It measures something different from perplexity: signal one asks "is this predictable?", this one asks "does this look uniform?". For this text it currently means very little. The stub returns a fixed 0.5, and even a real implementation would have nothing to work with on one short sentence, so a style score here should be read as "no evidence either way".

**Design decision:** What each edge case returns (one sentence, short text). Which direction each measure points (low spread and low TTR mean more AI, so they need flipping). How to scale them so none wins by default. Ideally a signal could report "no opinion" instead of a fake number.

**AI vs human:** Decided here too (signal two), from shape alone. For this text all three measures are undefined or driven by length, so the signal is essentially noise. Blind spot: it can't read, so edits to the shape move it.

### Step 3: scoring.combine_signals(model_score, style_score) (file: scoring.py)
**What happens:** Weighted average with `WEIGHT_MODEL_SIGNAL` = 0.5 and `WEIGHT_STYLE_SIGNAL` = 0.5 from `config.py`: 0.5 × 0.4302 + 0.5 × 0.5 = **0.4651**.

**Design decision:** The most consequential one in the pipeline.

- The weights.
- What happens when the signals disagree: average them, or treat disagreement itself as `unsure`.
- Which way to be wrong: weighting toward the more human-reading signal means fewer false accusations and more AI text getting through.
- Whether short text should lower the weight of both signals.

While the style signal is a stub at 0.5, the combined score is pinned to 0.25–0.75.

**AI vs human:** This is where the two verdicts are reconciled into one. It is where my false-positive decision from Milestone 1 is actually made.

### Step 4: scoring.score_to_label(score) (file: scoring.py)
**What happens:** Returns `(guess, label_text)`. Score ≥ `AI_THRESHOLD` (0.65) gives `"ai"`, score ≤ `HUMAN_THRESHOLD` (0.35) gives `"human"`, anything between gives `"unsure"`. 0.4651 falls in the middle, so the result is **`unsure`**, which is the honest answer for one poetic line.

**Design decision:** The thresholds in `config.py`. A wider unsure band means fewer wrong accusations and less coverage. The label text must be written for someone who has never heard of a threshold, and the `unsure` text must not read as an accusation, since the writer may have written every word. Possibly a separate "too short to assess" label.

**AI vs human:** This turns the number into a claim about a person. Mistakes here land on the writer, which is why the unsure band exists.

### Step 5: audit.log_decision(content_id,creator_id,guess,model_score,   style_score,combined_score,label, status) (file: audit.py)
**What happens:** Builds one entry with a UTC timestamp, the passed fields and `status="decided"`, then `_append` writes it as one JSON line to `logs/audit.jsonl` (append-only, behind a thread lock). An appeal later becomes a separate entry, never an edit.

**Design decision:** What extra to log beyond the nine required fields, e.g. token count or a "low confidence because short" flag. In unit 8 I can't diagnose a miss without them.

**AI vs human:** Nothing is decided here. It records what was decided so a wrong accusation can be traced to a stage.

### Step 6: craft the response

**What happens:** `submit()` returns JSON: `content_id`, `guess` (`unsure`), `confidence`, `label`, `model_score` (0.4302) and `style_score` (0.5 while stubbed). Both signal scores must be in the response, because unit 8's `run_attacks.py` and `run_eval.py` read them from it.

**Design decision:** What `confidence` means: the combined score itself, or distance from the nearest threshold (arguably more honest).

**AI vs human:** The result is not hidden here. The reader sees the label text, so its wording matters more than the number.

## False Positive: Human Written text labeled as AI 
Low perplexity text, and short sentences that do not give enough context for a relevant statistical measurement

**Where does it show?** 
- detector.py -> model_signal >0.8
- score.py -> model_signal and style_signal > 0.65

**What to tweak?** 
- AI_THRESHOLD -> if > 0.65 fewer people get accused of AI (but more AI text passes)
- combine_signals() weights -> which signal makes a text more human? which one is not too AI prone?
- /submit input fate -> short text usually default to unsure 

# Endpoint Shapes 
## POST/submit 

### Input 
|Field | Type | Required |
|--|--|--|
| text | string | yes |
| creator_id | string| yes |

### Output (200)
|Field | Type | Meaning |
|--|--|--|
| content_id | string | UUID (handle needed by /appeal) |
| guess | string| should be "human", or "unsure" or "ai" |
| confidence | number [0-1] | how sure the system is of `guess`|
| label | string | what the reader sees |
| model_score | number [0-1] | 1st signal. Read -> one = AI; 0 = human |
| style_score | number [0-1] | 2nd signal. Read -> one = AI; 0 = human |
|-------|------|-----|

### Output (error)
format {"error" : "<code>", "message": "<human sentence>"}

| Cause | Status | error code |
|--|--|--|
| Body isn't JSON or isn't an object | 400 | invalid_body |
| `text` missing or not string | 400| invalid_text |
| `text` empty or whitespace | 400 | empty_text`|
| `creator_id` missing or non-empty string| 400 | invalid_creator |
