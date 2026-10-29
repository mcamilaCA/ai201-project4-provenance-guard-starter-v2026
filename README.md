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

### A failure I found: both signals ranked a poem pair backwards

I tested both signals on three short texts: a human-written poem, an AI-written poem, and "roses are red violets are blue" (a famous line, which could pass for either). The human poem scored *more* AI-like than the AI poem on both signals.

| Text | Words | Perplexity | `model_signal` | `style_signal` |
|---|---|---|---|---|
| Human poem ("She is both the tempest and the halcyon…") | 31 | 35.6 | 0.5922 | 0.6083 |
| AI poem ("In quiet hours when shadows softly bend…") | 30 | 181.4 | 0.0971 | 0.5444 |
| "roses are red violets are blue" | 6 | 148.7 | 0.1287 (computed from the perplexity) | 0.5444 |

These numbers were measured on the original code, before the 40-word floor, the newline splitting and the whitespace fix described below. The two poems were also laid out differently: the human poem had a blank line between every line, the AI poem had single newlines. I did not control for that at first, and it turned out to matter (see the correction after the signal-one paragraph).

Raw output, pasted as text (the human poem, from `python detector.py` and `python stylometry.py`):

```
perplexity     35.6
model_signal   0.5922   (higher = more likely AI)

3 sentences, 31 words
sentence_length_spread   0.3110855084191276
type_token_ratio         0.8387096774193549
punctuation_density      0.06451612903225806
style_signal             0.6083   (higher = more likely AI)
```

**Stage and mechanism: signal one.** GPT-2 found the AI poem *more* surprising (perplexity 181) than the human one (36). The rhymed, slightly archaic phrasing ("shadows softly bend… familiar end") is unusual word-by-word for a small model, while "just like art" and "meant to be felt" are everyday phrases. Perplexity measures how predictable the words are to GPT-2, not who wrote them. `model_signal` is strictly decreasing in perplexity, so changing `midpoint` or `steepness` can slide the scores but can never swap the order of the two texts. That is why I did not tune it. Thirty words is also very little for a per-token average, and a famous line like "roses are red" is predictable because it is memorized, not because a model wrote it.

**Correction: layout was moving the perplexity too.** While testing a poem of my own I found that the same words scored very differently depending only on whitespace: 36.1 with a blank line between every line, 115.3 with single newlines, and 49.4 on one run-on line. Line breaks and extra spaces are tokens, and GPT-2 treats them as part of the text. That meant the first measurement above was partly a layout effect, so I could not tell from it how much of the reversal was the model. I now collapse all whitespace to single spaces inside `detector.perplexity()` and measured the pair again with that fixed:

| Text | Perplexity before | Perplexity with whitespace normalized | `model_signal` (normalized) |
|---|---|---|---|
| Human poem | 35.6 | 49.4 | 0.4629 |
| AI poem | 181.4 | 231.3 | 0.0679 |

Layout exaggerated the gap, but the reversal is still there: the AI poem is still far more surprising to GPT-2 than the human one. So the mechanism in the paragraph above holds, and layout was a second, separate problem in the same stage. It is also a way to move a score without changing a word, which a writer or an attack could use deliberately.

**Stage and mechanism: signal two.** `sentences()` split only on `. ! ?`, so the AI poem, which has no punctuation until its last word, counted as *one* sentence. One sentence has no spread, so `sentence_length_spread` returned its placeholder 0.3 instead of measuring anything. The 0.06 gap between the two style scores came from that artifact, not from a real stylistic difference.

**What I changed** (the first two cover both signals, the third is signal one only):

1. **Short text gets "no evidence either way".** New setting `MIN_WORDS = 40` in `config.py`. Below it, `detector.model_signal` and `stylometry.style_signal` both return 0.5 instead of a confident number, so the combined score lands in the unsure band. All three texts above are under the floor and now score 0.5 on both signals. This also stops `"..."` from scoring as maximally AI (its style score was 1.0 before).
2. **Line breaks end a sentence.** `stylometry.sentences()` now also splits at newlines, so the AI poem is measured as four lines of 7, 7, 8 and 8 words (spread 0.077) and the human poem as six lines (spread 0.333). The spread now points the right way on this pair: the uneven human text has the higher spread.
3. **Whitespace is normalized before the detector scores.** `detector.perplexity()` collapses every run of spaces and line breaks to one space, so layout can no longer change the number. The line structure still reaches `stylometry.sentences()`, which gets the original text.

**What I gave up.** The 40-word floor means a writer who submits a short poem or a few lines gets "unsure" every time, and so does someone sending a short AI-written message, so the system declines to judge both. Splitting on newlines has a cost too: prose that was hard-wrapped mid-sentence (pasted from an email or a terminal) is now cut at every wrap, which makes its sentences look short and uniform, and so more AI-like. I have not measured how often that happens, and 40 is a starting value I chose, not one I tuned. I have also only seen this failure on three samples, so it shows a mechanism, not a rate.

### The combining rule

<!-- Write the rule in words, then give the numbers. What happens when the two
     signals disagree? -->

**The rule:** A weighted average of the two scores, both on the same scale (higher = more likely AI). I don't resolve a disagreement in favour of either signal: when one says AI and the other says human, the average lands between them, in the unsure band, because two methods disagreeing is itself uncertainty. Text under 40 words never reaches this point with an opinion, because both signals return 0.5 for it (see "A failure I found" above), so the combined score is 0.5 and the label is unsure.

**The numbers:** `WEIGHT_MODEL_SIGNAL = 0.5`, `WEIGHT_STYLE_SIGNAL = 0.5` in `config.py`. Equal, because neither signal has earned more trust: the model signal was fooled by a rhymed poem, and the style signal is built on three crude measures with bounds I guessed rather than tuned. The score is rounded to 4 places. `confidence` in the response is `abs(combined_score - 0.5) * 2`: 0.0 means the signals say nothing, 1.0 means they are as sure as they get.

**Where it lives:** `scoring.py::combine_signals`

<!-- ⚠️ The grader checks your code against that line. If your rule lives
     somewhere else, say where. -->

**Four-input check** (one text each, so a sanity check and not a measurement; every text is over the 40-word floor): an AI-written paragraph on remote work, Twain's opening of *Huckleberry Finn* as clearly human, Darwin's "entangled bank" passage as formal human writing, and the AI paragraph again with light edits (swapped words, merged sentences, one typo).

| Text | Words | `model_score` | `style_score` | Combined | Label |
|---|---|---|---|---|---|
| Clearly AI | 78 | 0.8048 | 0.6211 | 0.7129 | ai |
| Clearly human (Twain) | 108 | 0.4556 | 0.5534 | 0.5045 | unsure |
| Formal human (Darwin) | 89 | 0.4904 | 0.5148 | 0.5026 | unsure |
| Lightly-edited AI | 82 | 0.6591 | 0.6639 | 0.6615 | ai |

What it showed:

- **The formal human text was not accused**, which is the case that matters most. It came out unsure, though, not human.
- **Neither human text reached the human label.** Both sit near 0.50, because neither signal goes low on them. The model signal does almost all the separating (0.80 for AI against 0.46 and 0.49 for the human texts); the style signal only ranges from 0.51 to 0.66 across all four.
- **The edited AI is barely still caught:** 0.6615 against an AI threshold of 0.65. The edits dropped `model_score` from 0.80 to 0.66, so one more round of edits would likely turn it into unsure.
- **The edit moved `style_score` the wrong way, up from 0.62 to 0.66.** My edits removed the commas after "First," "Additionally," and "Furthermore," so `punctuation_density` fell from 0.090 to 0.049, which reads as *more* AI. That is the signal-two blind spot from the file's own docstring, seen directly: changing the shape without changing the substance moves it.
- **The flat style scores have a cause, shown in the per-measure table below.**
- **No text here was a true split** (signals on opposite sides of 0.5): the largest gap between the two scores was 0.18 (the AI paragraph), and both of its scores were above 0.5.

**Finding: the style signal barely discriminates, and it is not one problem but three.** Printing every number that feeds `style_score` for the same four texts (each column is the AI-ness of one measure after scaling and flipping, 0 to 1):

| Text | `model_score` | spread | type-token | punctuation | `style_score` |
|---|---|---|---|---|---|
| Clearly AI | 0.805 | 0.902 | 0.141 | 0.821 | 0.621 |
| Clearly human (Twain) | 0.456 | 0.520 | 0.400 | 0.741 | 0.553 |
| Formal human (Darwin) | 0.490 | 0.544 | 0.225 | 0.775 | 0.515 |
| Lightly-edited AI | 0.659 | 0.906 | 0.183 | 0.902 | 0.664 |
| **Range (max − min)** | **0.349** | **0.387** | **0.259** | **0.162** | **0.149** |

- **Sentence-length spread works.** It rates the two AI texts about 0.90 and the two human texts about 0.52 to 0.54, and the light edit barely moved it (0.902 to 0.906). It is the only part of signal two that separates these texts.
- **Type-token ratio runs the wrong way on these four.** The AI paragraph gets the *lowest* AI-ness (0.141) and Twain the highest (0.400). Twain repeats words on purpose ("he told the truth", "Aunt Polly") and the AI text varies its vocabulary, which is the opposite of what the measure assumes. With one text each this may not hold in general, but on this set it drags the style score the wrong way.
- **Punctuation density is nearly flat and high for everything** (0.74 to 0.90). It is scaled against a ceiling of 0.5 marks per word, but all four texts sit between 0.05 and 0.13, so it adds a high AI-ish value to every text and tells me almost nothing. The light edit also *raised* it (0.821 to 0.902), because removing commas after "Additionally," and "Furthermore," reads as more AI.
- **Net effect:** one working measure, one backwards, one saturated, averaged with equal weights, which is why `style_score` spans only 0.149 against the model signal's 0.349 and puts the AI paragraph (0.62) only 0.07 above Twain (0.55).

I have not retuned the scaling bounds or dropped a measure, because four texts are too few to tune against without just fitting them. This is the finding to carry into unit 8: signal two as built is close to a one-measure signal, and its weight in the combined score (0.5) is higher than what it has earned.

**A case where my two signals split, and what my rule does with it:**

I lengthened the AI poem from my earlier test to two stanzas (61 words, over the 40-word floor). The first stanza is the chatbot-written one from before; I added the second stanza in the same style, so the whole text is AI-written.

```
In quiet hours when shadows softly bend,
And whispered thoughts find no familiar end,
A steady warmth begins to trace the air,
A gentle proof that you are resting there.
The morning light will find its patient way,
Through curtains drawn against the fading grey,
And every hush that lingers on the stair
Will carry back the quiet of your prayer.
```

| `model_score` | `style_score` | Gap | Combined | Label |
|---|---|---|---|---|
| 0.2618 | 0.6516 | 0.39 | 0.4567 | unsure |

The signals land on opposite sides of 0.5. Signal one reads it as human because GPT-2 finds rhymed, slightly archaic phrasing surprising (the same mechanism as in "A failure I found"). Signal two reads it as AI because every line is 7 to 9 words long, so the spread is low. My rule averages them to 0.4567, inside the unsure band, so the result is "unsure". That is the behaviour I wanted: two methods disagreeing is treated as uncertainty, and the writer gets neither a human nor an AI verdict. The cost is the same as everywhere else: this really is AI text, and the system did not catch it. Here the style signal was right and the model signal was wrong, and the average let the wrong one pull the result away from "ai".



---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human | 0.00 – 0.35 | "We think this was probably written by a person." |
| unsure | 0.35 – 0.65 | "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you." |
| high-confidence AI | 0.65 – 1.00 | "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result." |

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

       [x] criteria.md has five numbered criteria, each naming a target
       [x] Each has a reason underneath
       [x] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [x] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [x] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [x] At least four new commits
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
