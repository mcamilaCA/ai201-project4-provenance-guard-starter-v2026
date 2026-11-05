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

A writer (or a script) sends a piece of text and gets back a verdict a person can read. Here is the path one submission takes through `POST /submit`:

1. **The request arrives** (`app.py::submit`). The body is JSON with `text` and `creator_id`. A body that isn't a JSON object is treated as empty, and a missing `creator_id` becomes `"unknown"`.
2. **The route decides whether the text can be scored at all.** If `text` is missing, not a string, or only whitespace, the route writes a `rejected` entry to the audit log and answers `400 invalid_text`. Otherwise it creates a `content_id` (a UUID), which `/appeal` needs later.
3. **Signal one: how predictable is it?** (`detector.py::model_signal`). Whitespace is collapsed to single spaces, GPT-2 measures its average surprise per token (perplexity), and that is converted to a 0–1 score where higher means more AI-like. Text under 40 words returns 0.5, meaning "no evidence either way".
4. **Signal two: how uniform does it look?** (`stylometry.py::style_signal`). It measures sentence-length spread (line breaks count as sentence ends), vocabulary repetition and punctuation density, and combines them into a 0–1 score pointing the same way. Under 40 words it also returns 0.5.
5. **The two scores become one** (`scoring.py::combine_signals`). It is an equal-weight average (0.5 and 0.5, set in `config.py`). When the signals disagree, the average lands in the middle, so disagreement shows up as uncertainty.
6. **The score becomes a label** (`scoring.py::score_to_label`). 0.35 or lower is "human", 0.65 or higher is "ai", and anything between is "unsure". Each comes with a full sentence written for a reader, shown under Label Variants. The response's `confidence` is how far the score is from 0.5, scaled to 0–1.
7. **The decision is logged and answered** (`audit.py::log_decision`). One line goes into `logs/audit.jsonl` with the `content_id`, `creator_id`, guess, both signal scores, the combined score, the label and the status `decided`. The response carries `content_id`, `guess`, `confidence`, `label`, `model_score` and `style_score`.

**If the writer disagrees:** `POST /appeal` takes the `content_id` and the writer's reasoning, checks that the id exists, appends an appeal entry to the log with status `under_review` (the original decision is never edited), and confirms. Appealing the same result twice returns `409`, and an unknown id returns `404`.

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

**The numbers:** *(Superseded in unit 8: the weights are now 0.3 and 0.7, see "The Improvement". The measurements in this section were taken at 0.5/0.5.)* `WEIGHT_MODEL_SIGNAL = 0.5`, `WEIGHT_STYLE_SIGNAL = 0.5` in `config.py`. Equal, because neither signal has earned more trust: the model signal was fooled by a rhymed poem, and the style signal is built on three crude measures with bounds I guessed rather than tuned. The score is rounded to 4 places. `confidence` in the response is `abs(combined_score - 0.5) * 2`: 0.0 means the signals say nothing, 1.0 means they are as sure as they get.

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


## GET /content/<id> Endpoint - Stretch Feature

Give it a `content_id` from `/submit` and it reads that item's entries back from the audit log and returns its current status (`decided` or `under_review`) with the original decision and any appeal, or a 404 if the id is unknown.

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

The person reading this label may have written every word themselves, so it had to do three things:

1. **Say plainly that the system doesn't know.** "We can't tell" is the whole finding. It doesn't hint at a lean in either direction, and it doesn't use words like "score", "confidence" or "inconclusive" that a reader would have to decode.
2. **Say the uncertainty is the system's limit, not the writer's fault.** "That isn't a judgment about you or your writing" puts the gap in the tool. Someone who reads "unsure" as "you sound like a robot" is told directly that it doesn't mean that.
3. **Tell them nothing is required.** "Nothing more is needed from you" stops the label from reading like a summons or a request to prove themselves. Unlike the AI label, it doesn't mention an appeal, because there is no decision against them to appeal.

I avoided "might be AI" and "could be either" in this one. A reader hears "might be AI" as an accusation with a hedge on it, and that is the reading this label exists to prevent.

**Boundaries.** A score of exactly 0.35 gets the human label and exactly 0.65 gets the AI label (`score_to_label` in `scoring.py` uses `<=` and `>=`). The numbers come from `HUMAN_THRESHOLD` and `AI_THRESHOLD` in `config.py`, and `scoring.label_ranges()` prints them, so this table can be checked against the code. All three labels are reachable: the four-input check above produced "ai" and "unsure", and any text scoring 0.35 or lower produces "human".



---

## Sample Run

<!-- One submission and one appeal, pasted as text: the request, the response,
     and the log entries. -->

**A submission**

<!-- The response needs content_id, guess, confidence, label, AND both
     signal scores - model_score and style_score. Unit 8's tools read those
     two off the response, so leaving them out costs you next unit's
     diagnostics. -->

The text is an AI-style paragraph on remote work that I wrote to exercise the "ai" label. It is not real human writing.

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "Remote work has transformed the modern workplace in significant ways. First, it offers employees greater flexibility, allowing them to balance professional and personal responsibilities. Additionally, it reduces commuting time, which can improve overall well-being. Furthermore, companies can access a broader talent pool. However, it is important to consider challenges such as communication barriers and feelings of isolation. Overall, remote work presents both opportunities and challenges for organizations.", "creator_id": "camila-label-test"}'
```

```json
{
  "confidence": 0.3528,
  "content_id": "02bdc904-0470-4c2b-bc8c-b41d166394d8",
  "guess": "ai",
  "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
  "model_score": 0.7578,
  "style_score": 0.5949
}
```

(Use `127.0.0.1`, not `localhost`: on macOS, `localhost:5000` is answered by AirPlay, not this service.)

**An appeal**

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "02bdc904-0470-4c2b-bc8c-b41d166394d8", "reasoning": "I wrote this paragraph myself for a class assignment. It is formal because the assignment asked for a formal tone."}'
```

```json
{
  "content_id": "02bdc904-0470-4c2b-bc8c-b41d166394d8",
  "message": "Thank you. Your appeal has been recorded and this result is now under review.",
  "status": "under_review"
}
```

Sending the same appeal again returns `409 already_under_review`, an unknown `content_id` returns `404 unknown_content_id`, and a missing `reasoning` returns `400 invalid_reasoning`. The 400s and the 404 are also written to the log as `rejected` entries.

**What the log shows afterwards**

```bash
$ curl "http://127.0.0.1:5000/log"
```

`/log` returns every entry, so this is that response filtered to the entries for the content_id above. The third entry is my own test of the missing-`reasoning` case. The log is append-only: the original decision keeps `"status": "decided"`, and the appeal sits after it with `"status": "under_review"`.

```json
{
  "count": 3,
  "entries": [
    {
      "combined_score": 0.6764,
      "content_id": "02bdc904-0470-4c2b-bc8c-b41d166394d8",
      "creator_id": "camila-label-test",
      "guess": "ai",
      "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
      "model_score": 0.7578,
      "status": "decided",
      "style_score": 0.5949,
      "timestamp": "2026-11-02T00:33:48+00:00"
    },
    {
      "content_id": "02bdc904-0470-4c2b-bc8c-b41d166394d8",
      "creator_id": "camila-label-test",
      "event": "appeal",
      "reasoning": "I wrote this paragraph myself for a class assignment. It is formal because the assignment asked for a formal tone.",
      "status": "under_review",
      "timestamp": "2026-11-02T00:34:55+00:00"
    },
    {
      "content_id": "02bdc904-0470-4c2b-bc8c-b41d166394d8",
      "creator_id": "unknown",
      "event": "rejected",
      "reason": "invalid_reasoning",
      "status": "rejected",
      "timestamp": "2026-11-02T00:34:55+00:00"
    }
  ]
}
```
## The Human Path - Stretch Feature

**What it does:** A writer asks for a challenge (`POST /verify/start`), answers a fresh prompt of at least 40 words within 10 minutes (`POST /verify/complete`), and if the answer isn't scored as AI they earn a verified-human credential that shows as `"verified_human": true` on `/submit` and `GET /content/<id>`, including on work submitted earlier. It only adds a badge; the verdict and label are unchanged.

**Limits:** The check reuses the same detector as everything else, so it inherits that detector's blind spots, and "not scored as AI" includes "unsure", so lightly edited AI text could earn the credential. The answer also isn't tied to later submissions, so a verified writer can still submit AI text and it will carry the badge.

**Future work:** Add a reviewer-approved route (the writer submits drafts or version history and a person approves it), let the credential expire or be revoked, and tie it to individual submissions instead of to the writer.


---

## How I Used AI

**Moment 1**

- *What I asked for:* Guidance on code section where I got too many errors (in this case how to unpack from payload or how to succesfully catch errors on the payload being a dict or not)
- *What came back:* instructions and clues on how the code unfolds, for example: What to pass. Check the signature at audit.py:35. It takes content_id, creator_id, guess, model_score, style_score, combined_score, label and status. Everything after creator_id defaults to None.
- *What I changed:* I wrote the code since the agent did not provide it but provided instructions

**Moment 2**

- *What I asked for:* Text that would produce each of the three labels, submitted through the running service, so I could show that all three are reachable.
- *What came back:* Three texts the assistant wrote itself (an AI-style paragraph, a casual anecdote, a short memoir passage) and the real `/submit` responses for them: "ai" at 0.6764, "unsure" at 0.4675 and "human" at 0.3392. It also pointed out two things I would otherwise have missed: the "human" passage is AI-written, so it shows the range is reachable and says nothing about whether the detector works, and it only just got under the 0.35 cutoff, carried by the model signal while the style signal stayed near 0.5. Separately, `curl` to `localhost:5000` was being answered by macOS AirPlay, not my app.
- *What I changed:* I use `127.0.0.1:5000` in every curl command in this README and say why next to the first one. I treat that "human" result as a range check, not as evidence, and the Sample Run says the submitted text is AI-style text written for the test.

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** __6_ per minute, _120__ per day

**Why those numbers and not others:**
<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->
     I believe a writter, if and when editting, might make small changes which take less than a minute to fix, which is why I selected 6. Especially in case they are adding small punctuation marks, or maybe double checking spelling. I believe if you change your text more than 6 times in one same minute (which is around 10 seconds for change and submitting), you might be using an AI helper, no human uses that little time to think and correct oneself

     In terms of 120 per day, writing is a hard skill, and unless you are dedicating a whole day to submit, you most likely need to tend to you job, and other needs. Again, if you are submitting too many times and too little time, it might indicate some AI usage.

**What a caller counts as:** <!-- per address, or per creator_id? They fail differently — one script can look like a thousand callers, and one household can look like one. -->

A caller should be a same creator id, since several creators might share the same address when submiting and hence it is not a good standard for checking individuality. Moreover, if using creator id AND address, it would not count once a user has moved an is uploading under their same account, hence it would still be useless. However, if any time your same alias (in this case creator_id) is being used, it means you are the same creator. 

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```
15 submissions as 'flood_tester' against http://127.0.0.1:5000
The first one is slow while the model loads.

  [ 1/15] 200
  [ 2/15] 200
  [ 3/15] 200
  [ 4/15] 200
  [ 5/15] 200
  [ 6/15] 200
  [ 7/15] 429
  [ 8/15] 429
  [ 9/15] 429
  [10/15] 429
  [11/15] 429
  [12/15] 429
  [13/15] 429
  [14/15] 429
  [15/15] 429

============================================================
200 200 200 200 200 200 429 429 429 429 429 429 429 429 429
============================================================

9 of 15 were rate limited. Paste the run above into your README
under **Rate Limiting**, and check GET /log recorded the rejections.
```

---

## Attack Run — Before

56 attacks: **39 held, 16 broke, 1 inconclusive**. The service had no 5xx or crash. "Combined" is the 0.5/0.5 average of the two signals, worked out from the per-attack JSON. It is blank where the request was rejected (400 or 429).

| ID | Family | Targeting | Status | Guess | Combined | Verdict | Why |
|---|---|---|---|---|---|---|---|
| EV01 | evasion | signal two: typos raise word variety | 200 | unsure | 0.407 | BROKE | AI text slipped to unsure |
| EV02 | evasion | signal two: broken-up sentences raise length spread | 200 | unsure | 0.554 | BROKE | AI text slipped to unsure |
| EV03 | evasion | signal two: a pasted quotation changes the shape | 200 | unsure | 0.625 | BROKE | AI text slipped to unsure |
| EV04 | evasion | signal one: unusual words raise perplexity | 200 | unsure | 0.629 | BROKE | AI text slipped to unsure |
| EV05 | evasion | both signals: heavy human editing pass | 200 | unsure | 0.437 | BROKE | AI text slipped to unsure |
| EV06 | evasion | signal two: one very long sentence and one very short | 200 | unsure | 0.519 | BROKE | AI text slipped to unsure |
| EV07 | evasion | signal two: padding with punctuation | 200 | unsure | 0.580 | BROKE | AI text slipped to unsure |
| EV08 | evasion | signal one: text below the token window | 200 | unsure | 0.500 | BROKE | Text below token window scores 0.5 |
| EV09 | evasion | both: AI text with a human opening paragraph bolted on | 200 | unsure | 0.628 | BROKE | AI text slipped to unsure |
| EV10 | evasion | signal two: repeated stanza structure | 200 | ai | 0.917 | HELD | Caught as ai (0.83) |
| FP01 | false_positive | plain, clear human writing with no flourishes | 200 | unsure | 0.635 | HELD | Human not accused |
| FP02 | false_positive | human writing in a formal register | 200 | ai | 0.720 | BROKE | Real human writing labeled ai |
| FP03 | false_positive | a non-native English speaker writing carefully | 200 | ai | 0.746 | BROKE | Real human writing labeled ai |
| FP04 | false_positive | a student essay written to a rubric | 200 | ai | 0.736 | BROKE | Real human writing labeled ai |
| FP05 | false_positive | technical documentation written by a person | 200 | ai | 0.762 | BROKE | Real human writing labeled ai |
| FP06 | false_positive | a person imitating a formal template | 200 | ai | 0.755 | BROKE | Real human writing labeled ai |
| FP07 | false_positive | human writing that repeats a phrase deliberately | 200 | ai | 0.772 | BROKE | Real human writing labeled ai |
| FP08 | false_positive | very short genuine human submission | 200 | unsure | 0.500 | HELD | Human not accused |
| PI01 | prompt_injection | instruction to ignore the check | 200 | unsure | 0.502 | HELD | Instruction ignored; stays unsure |
| PI02 | prompt_injection | instruction disguised as a system message | 200 | human | 0.332 | BROKE | Odd-word padding lowered score to human |
| PI03 | prompt_injection | instruction wrapped in the writer's voice | 200 | unsure | 0.540 | HELD | Instruction ignored; stays unsure |
| PI04 | prompt_injection | attempt to make the label text hostile | 200 | unsure | 0.536 | HELD | Fixed label; human text not accused |
| PI05 | prompt_injection | attempt to inject into the audit log | 200 | unsure | 0.500 | HELD | Audit log stayed intact |
| PI06 | prompt_injection | instruction plus real human text | 200 | unsure | 0.589 | HELD | Fixed label; human text not accused |
| MF01 | malformed | text is only whitespace | 400 | — | — | HELD | Clean 400 rejection |
| MF02 | malformed | text is a single character | 200 | unsure | 0.500 | HELD | No crash; safe unsure |
| MF03 | malformed | text is control characters | 200 | unsure | 0.500 | HELD | No crash; safe unsure |
| MF04 | malformed | text is only punctuation | 200 | unsure | 0.500 | HELD | No crash; safe unsure |
| MF05 | malformed | text is a very long single word | 200 | unsure | 0.500 | HELD | No crash; safe unsure |
| MF06 | malformed | text is emoji only | 200 | unsure | 0.500 | HELD | No crash; safe unsure |
| MF07 | malformed | text is right-to-left script | 200 | unsure | 0.500 | HELD | No crash; safe unsure |
| MF08 | malformed | text is 60,000 characters | 200 | ai | 0.823 | HELD | Handled 60,000 characters |
| RQ01 | malformed | no text field at all | 400 | — | — | HELD | Clean 400 rejection |
| RQ02 | malformed | no creator_id | 200 | unsure | 0.500 | HELD | Safe fallback to unknown creator |
| RQ03 | malformed | text is a number | 400 | — | — | HELD | Clean 400 rejection |
| RQ04 | malformed | text is a list | 400 | — | — | HELD | Clean 400 rejection |
| RQ05 | malformed | text is null | 400 | — | — | HELD | Clean 400 rejection |
| RQ06 | malformed | creator_id is an object | 200 | unsure | 0.500 | HELD | Safe fallback to unknown creator |
| RQ07 | malformed | body is a JSON array, not an object | 400 | — | — | HELD | Clean 400 rejection |
| RQ08 | malformed | body is unparseable JSON | 400 | — | — | HELD | Clean 400 rejection |
| RQ09 | malformed | body is empty | 400 | — | — | HELD | Clean 400 rejection |
| RQ10 | malformed | body is form-encoded, not JSON | 400 | — | — | HELD | Clean 400 rejection |
| RQ11 | malformed | body is JSON claiming to be plain text | 429 | — | — | INCONCLUSIVE | Rate limiter fired first; rerun alone |
| RQ12 | malformed | deeply nested JSON | 400 | — | — | HELD | Clean 400 rejection |
| FL01_01 | flood_same_creator | 20 rapid submissions from one creator | 200 | unsure | 0.500 | HELD | Allowed within the limit |
| FL01_02 | flood_same_creator | 20 rapid submissions from one creator | 200 | unsure | 0.500 | HELD | Allowed within the limit |
| FL01_03 | flood_same_creator | 20 rapid submissions from one creator | 200 | unsure | 0.500 | HELD | Allowed within the limit |
| FL01_04 | flood_same_creator | 20 rapid submissions from one creator | 200 | unsure | 0.500 | HELD | Allowed within the limit |
| FL01_05 | flood_same_creator | 20 rapid submissions from one creator | 200 | unsure | 0.500 | HELD | Allowed within the limit |
| FL01_06 | flood_same_creator | 20 rapid submissions from one creator | 200 | unsure | 0.500 | HELD | Allowed within the limit |
| FL01_07 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | Blocked with 429 |
| FL01_08 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | Blocked with 429 |
| FL01_09 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | Blocked with 429 |
| FL01_10 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | Blocked with 429 |
| FL01_11 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | Blocked with 429 |
| FL01_12 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD | Blocked with 429 |

**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

### PI02 — `prompt_injection`

```json
{
  "timestamp": "2026-11-05T00:11:07+00:00",
  "content_id": "82f7e795-a26e-4935-8e64-0788d1873c8a",
  "creator_id": "attacker_PI02",
  "guess": "human",
  "model_score": 0.1576,
  "style_score": 0.507,
  "combined_score": 0.3323,
  "label": "We think this was probably written by a person.",
  "status": "decided"
}
```

### EV04 — `evasion`

```json
{
  "timestamp": "2026-11-05T00:11:07+00:00",
  "content_id": "22f98ab5-54df-4421-89fa-8e41582442d2",
  "creator_id": "attacker_EV04",
  "guess": "unsure",
  "model_score": 0.6114,
  "style_score": 0.6474,
  "combined_score": 0.6294,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "status": "decided"
}
```

### EV07 — `evasion`

```json
{
  "timestamp": "2026-11-05T00:11:07+00:00",
  "content_id": "2338a9c1-309a-4b54-86e4-75c4a3ce84ae",
  "creator_id": "attacker_EV07",
  "guess": "unsure",
  "model_score": 0.6278,
  "style_score": 0.5313,
  "combined_score": 0.5796,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "status": "decided"
}
```

### EV08 — `evasion`

```json
{
  "timestamp": "2026-11-05T00:11:07+00:00",
  "content_id": "3ee54403-090a-4221-9a52-5a14aaa113fa",
  "creator_id": "attacker_EV08",
  "guess": "unsure",
  "model_score": 0.5,
  "style_score": 0.5,
  "combined_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "status": "decided"
}
```

### EV09 — `evasion`

```json
{
  "timestamp": "2026-11-05T00:11:07+00:00",
  "content_id": "e8473f6e-18a1-4238-8406-9f8d37de71d4",
  "creator_id": "attacker_EV09",
  "guess": "unsure",
  "model_score": 0.6834,
  "style_score": 0.5727,
  "combined_score": 0.628,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "status": "decided"
}
```

### FP02 — `false_positive`

```json
{
  "timestamp": "2026-11-05T00:11:07+00:00",
  "content_id": "8e7955ee-4d60-45de-834f-fa753e186014",
  "creator_id": "attacker_FP02",
  "guess": "ai",
  "model_score": 0.7387,
  "style_score": 0.701,
  "combined_score": 0.7198,
  "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
  "status": "decided"
}
```

### FP03 — `false_positive`

```json
{
  "timestamp": "2026-11-05T00:11:07+00:00",
  "content_id": "ea6f2f81-0ff9-4bac-880c-731a1976c44f",
  "creator_id": "attacker_FP03",
  "guess": "ai",
  "model_score": 0.8051,
  "style_score": 0.6861,
  "combined_score": 0.7456,
  "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
  "status": "decided"
}
```

### FP06 — `false_positive`

```json
{
  "timestamp": "2026-11-05T00:11:07+00:00",
  "content_id": "0cbfcc13-6f5f-48de-b246-a7903c82f4a0",
  "creator_id": "attacker_FP06",
  "guess": "ai",
  "model_score": 0.8814,
  "style_score": 0.6294,
  "combined_score": 0.7554,
  "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
  "status": "decided"
}
```

### FP07 — `false_positive`

```json
{
  "timestamp": "2026-11-05T00:11:07+00:00",
  "content_id": "16d58783-807c-47a8-a0f2-f5254194bded",
  "creator_id": "attacker_FP07",
  "guess": "ai",
  "model_score": 0.8816,
  "style_score": 0.6624,
  "combined_score": 0.772,
  "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
  "status": "decided"
}
```

### RQ11 — `malformed`

```json
{
  "timestamp": "2026-11-05T00:11:08+00:00",
  "creator_id": "unknown",
  "event": "rejected",
  "status": "rejected",
  "reason": "rate_limited",
  "limit": "6 per 1 minute"
}
```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:

In this case, I would go for the false positive, for example FP03. I believe it a huge failure to automatically asume non-native speakers are AI simply because they are doing their best in a language that is not even the one(s) they are used to using. Or a native speaker, telling them that their way of expressing themselves is "not really human" or "not human enough" and can be mixed up with a system that imitates instead of feeling.


---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. False positives | Of 10 texts I wrote, at most 1 gets the high-confidence AI label, in each of 3 trials | 1 of 10 `ai` (8 unsure, 1 human) | 1 of 10 `ai` | 1 of 10 `ai` | **Met**, with no margin: it sits exactly at the limit every trial |
| 2. Score spread | Over 5 clearly-AI and 5 clearly-human texts, mean AI score is at least 0.4 above mean human score, and the lowest AI score is above the highest human score, in each trial | Mean gap 0.15 (AI 0.71, human 0.56); lowest AI 0.688 vs highest human 0.678 | Same guesses as trial 1 | Same guesses as trial 1 | **Missed**: the 0.15 gap is well under 0.4. The no-overlap half held only by 0.01. |
| 3. Label coverage | In a 12-text set (4 human, 4 AI, 4 borderline), each label appears at least twice and none covers more than 7 of 12 | human 0, ai 5, unsure 7 | human 0, ai 5, unsure 7 | human 0, ai 5, unsure 7 | **Missed**: the human label never appeared. Unsure was 7 of 12, exactly at the cap. |
| 4. Appeals | 10 of 10 appeals set status to "under appeal" and are stored with a timestamp and the writer's explanation | not run | not run | not run | **Unverified**: `run_eval.py` does not exercise `/appeal`, so there is no evidence either way. |
| 5. Bad input | Missing, empty and whitespace-only text return 400 with nothing stored; text over 50,000 characters returns 200 with a `warning` field and a full analysis. All 4 cases pass in each of 3 trials | 3 of 4: the three 400s passed, the long-text case returned 200 with no `warning` | 3 of 4 | 3 of 4 | **Missed**: `app.py` has no warning logic for long text. |

Combined scores in criterion 2 come from the printed signals, since the
combining rule is a 0.5/0.5 average (`config.py`). I worked them out from
trial 1; trials 2 and 3 returned identical guesses.

**Real output, trial 1 of each criterion**, produced by `run_eval.py::main`, which sends each text to `app.py::submit` (POST /submit) and records the response. The file is `results/run_2026-11-04_2116_before.md`. The `sent` field is the first 70 characters of the text submitted.

**1. False positives (own writing)**

```json
[
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.131,
    "model_score": 0.4578,
    "style_score": 0.6731,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": " When looking at Mi Youren's painting and more so the mountains, we se"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.0046,
    "model_score": 0.338,
    "style_score": 0.6666,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "As a computer science major, witnessing the city's recreation through "
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.4786,
    "model_score": 0.8102,
    "style_score": 0.6684,
    "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
    "sent": "When enrolling in college classes, it can be difficult to find the bes"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.134,
    "model_score": 0.5796,
    "style_score": 0.5543,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "We will be using Support Vector Machine (SVM). Some of the reasons why"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.1802,
    "model_score": 0.2045,
    "style_score": 0.6153,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "By analysing propositions and deciphering their values AI can be able "
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.1074,
    "model_score": 0.5116,
    "style_score": 0.5958,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "In my opinion, to understand and comprehend something, you need to que"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.0444,
    "model_score": 0.4953,
    "style_score": 0.5492,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "are people comfortable not being perfect around you? Meaning, are they"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.0,
    "model_score": 0.5,
    "style_score": 0.5,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "To be able to know your boundaries because of how deeply you understan"
  },
  {
    "status": 200,
    "guess": "human",
    "confidence": 0.3934,
    "model_score": 0.1275,
    "style_score": 0.4791,
    "label": "We think this was probably written by a person.",
    "sent": "I am a living controversy: so complicated yet so simple; sometimes com"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.0,
    "model_score": 0.5,
    "style_score": 0.5,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "Feeling stuck is a symptom of waiting for \u201csomething\u201d to finally happe"
  }
]
```

**2. Score spread: clearly human**

```json
[
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.1444,
    "model_score": 0.5635,
    "style_score": 0.5809,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "ugh don't even get me started on my landlord. he said he'd fix the hea"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.0932,
    "model_score": 0.3848,
    "style_score": 0.5219,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "Went to my cousin's wedding Saturday and the best moment was when the "
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.079,
    "model_score": 0.3942,
    "style_score": 0.5268,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "Quick update on the fence: the guy came, measured everything wrong, an"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.2624,
    "model_score": 0.7489,
    "style_score": 0.5135,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "When I was nine I broke my arm falling out of the apple tree behind ou"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.3566,
    "model_score": 0.832,
    "style_score": 0.5246,
    "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
    "sent": "Look, I'm not saying the movie was bad, I'm saying it was two and a ha"
  }
]
```

**2. Score spread: clearly AI**

```json
[
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.4136,
    "model_score": 0.8126,
    "style_score": 0.601,
    "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
    "sent": "In today's fast-paced digital landscape, effective time management has"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.3758,
    "model_score": 0.7631,
    "style_score": 0.6126,
    "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
    "sent": "Artificial intelligence is a transformative technology that is reshapi"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.4598,
    "model_score": 0.9103,
    "style_score": 0.5495,
    "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
    "sent": "Climate change represents one of the most pressing challenges of our t"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.4736,
    "model_score": 0.8613,
    "style_score": 0.6123,
    "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
    "sent": "Maintaining a healthy lifestyle involves a holistic approach that enco"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.3894,
    "model_score": 0.7907,
    "style_score": 0.5987,
    "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
    "sent": "Effective communication is a cornerstone of successful teamwork. It fo"
  }
]
```

**3. Label coverage: human set**

```json
[
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.1344,
    "model_score": 0.5409,
    "style_score": 0.5934,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "my sister called at 11pm to tell me she got the job and i literally sc"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.0154,
    "model_score": 0.5442,
    "style_score": 0.4712,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "Not gonna lie, the hike was harder than the website made it sound. Two"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.1564,
    "model_score": 0.3932,
    "style_score": 0.4504,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "Update on the sourdough: it's alive!! After two failed attempts I fina"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.264,
    "model_score": 0.6733,
    "style_score": 0.5906,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "I keep rewriting the first paragraph of this essay and it keeps gettin"
  }
]
```

**3. Label coverage: AI set**

```json
[
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.4514,
    "model_score": 0.8558,
    "style_score": 0.5955,
    "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
    "sent": "Sustainable urban development requires a comprehensive strategy that i"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.282,
    "model_score": 0.6574,
    "style_score": 0.6245,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "Remote work has fundamentally changed the modern workplace, offering f"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.4764,
    "model_score": 0.8554,
    "style_score": 0.6209,
    "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
    "sent": "Education plays a pivotal role in shaping individuals and societies. A"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.4414,
    "model_score": 0.8785,
    "style_score": 0.5628,
    "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
    "sent": "Cybersecurity has emerged as a critical priority for organizations of "
  }
]
```

**3. Label coverage: borderline set**

```json
[
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.16,
    "model_score": 0.5378,
    "style_score": 0.6222,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "The committee reviewed the proposal in detail and concluded that, whil"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.3084,
    "model_score": 0.7241,
    "style_score": 0.5844,
    "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
    "sent": "I believe remote work has real benefits, though it isn't for everyone."
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.2436,
    "model_score": 0.666,
    "style_score": 0.5775,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "Over the past decade, the local library has become more than a place t"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.3924,
    "model_score": 0.7586,
    "style_score": 0.6337,
    "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
    "sent": "When approaching a new codebase, I find it helpful to start with the t"
  }
]
```

**5. Bad input**

```json
[
  {
    "status": 400,
    "guess": null,
    "confidence": null,
    "model_score": null,
    "style_score": null,
    "label": null,
    "sent": "{\"creator_id\": \"eval_bad_missing\"}"
  },
  {
    "status": 400,
    "guess": null,
    "confidence": null,
    "model_score": null,
    "style_score": null,
    "label": null,
    "sent": "(empty text)"
  },
  {
    "status": 400,
    "guess": null,
    "confidence": null,
    "model_score": null,
    "style_score": null,
    "label": null,
    "sent": "   \n\t  "
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.0,
    "model_score": 0.5,
    "style_score": 0.5,
    "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
    "sent": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
]
```

**4. Appeals:** no output, because `run_eval.py` does not call `/appeal`.

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

**Eval misses (criteria 2, 3, 5)**

- **Criteria 2 and 3 are one problem: the model signal is too weak, and the
  style signal does not separate the classes at all.** Clearly-human texts get
  style scores of 0.51 to 0.58 and clearly-AI texts get 0.55 to 0.61, so the
  style signal moves the average by about 0.03. The model signal has the
  spread (AI 0.76 to 0.91) but it also scored two clearly-human texts at 0.75
  and 0.83. Because the combining rule averages 0.5/0.5, a style signal stuck
  near 0.55 pulls every combined score toward the middle. That squeezes
  scores into roughly 0.45 to 0.74. With `HUMAN_THRESHOLD = 0.35`, almost
  nothing can drop below the human line, so the human label is never reached.
  Stage at fault: signal two, then the combining rule.
- **Criterion 1 passes only because the 8 other texts land in "unsure".** The
  one accused text had a model score of 0.81, which is the same model-signal
  weakness. This is a pass I would not trust.
- **Criterion 5: the long-text case was never implemented.** `app.py::submit`
  rejects empty input but has no length check and no `warning` field. The
  all-`a` input came back with scores of exactly 0.5 and 0.5, so the
  signals appear to have no usable signal on degenerate text. Stage at
  fault: the route.
- **Criterion 4** needs an appeal test added to `run_eval.py` before it can
  get a verdict.

**Attack run: 16 of 56 broke** (9 evasion, 6 false positive, 1 prompt injection). Scores are from `results/attack_run_2026-11-04_1811.md`. "Combined" is the 0.5/0.5 average, and the AI threshold is 0.65.

*The pattern behind the 9 evasions.* Every one slipped to "unsure" and none reached "human". Clean AI text scored only 0.69 to 0.74 combined in the eval run, so it sits about 0.04 above `AI_THRESHOLD`. Any edit that shaves 0.04 off either signal flips the label. That is a thin margin at the combining rule and the label mapping, and each row below shows what moved.

| Attack | Combined | What moved | Stage and mechanism |
|---|---|---|---|
| EV01 typos | 0.41 | model 0.16, style 0.65 | **Signal one.** I aimed this at signal two and it failed there: style stayed at 0.65. The typos broke words into rare tokens, which spiked perplexity and dropped `model_score` to 0.16. |
| EV02 broken-up sentences | 0.55 | model 0.59, style 0.51 | **Signal two.** Short fragments raise `sentence_length_spread`, which flips toward human. |
| EV03 pasted quotation | 0.625 | model 0.67, style 0.58 | **Signal two, then the label mapping.** A small shift in both signals, and 0.025 below the threshold was enough. |
| EV04 unusual words | 0.629 | model 0.61, style 0.65 | **Signal one.** Rare words raise perplexity. The score ended 0.021 below `AI_THRESHOLD`. |
| EV05 heavy human edit | 0.44 | model 0.32, style 0.55 | **Signal one and signal two together.** Both moved, and the average followed. |
| EV06 one long, one short sentence | 0.52 | model 0.57, style 0.46 | **Signal two.** Two extreme sentence lengths inflate the coefficient of variation. |
| EV07 punctuation padding | 0.58 | model 0.63, style 0.53 | **Signal two.** `punctuation_density` counts only `:;,()?!—–`, so adding them is free. |
| EV08 text below the token window | 0.50 | both exactly 0.5 | **Signals one and two, through the `MIN_WORDS` gate.** Both return 0.5 on short text, so the combining rule gets 0.5 and 0.5 and the label is "unsure". Short AI text can't be caught. |
| EV09 human paragraph bolted on | 0.628 | model 0.68, style 0.57 | **Signal one and signal two, plus the route.** Both signals read the whole text, so a human opening dilutes the AI part. Nothing scores paragraphs separately. |

*The 6 false positives (FP02 to FP07, combined 0.72 to 0.77).* These are real human texts labelled "ai". Both signals agree on them, which is why they got through.
- **Signal one is the main driver, with `model_score` 0.74 to 0.88.** Formal, rubric-shaped, templated and deliberately repetitive writing is predictable to the language model, so perplexity is low. That is how FP03 (a careful non-native speaker) and FP07 (a repeated phrase) scored 0.81 and 0.88.
- **Signal two corroborates at 0.63 to 0.72.** Even sentence lengths, little punctuation variety and repeated vocabulary all read as AI, so it adds to the accusation.
- **The combining rule cannot dissent.** An average has no way to say "formal register, so discount signal one." FP01, plain and clear human writing, landed at 0.635, which is only 0.015 below the line. At 0.65 the label mapping is the last defence, and it is set too close.
- These break the criterion 1 target in spirit. That target passed on my own 10 texts, but these six show the same mechanism on other writers.

*PI02 (`prompt_injection`, combined 0.332, label "human").* **Signal one.** This is the only attack that reached the human label. Its odd-word padding raised perplexity, so `model_score` fell to 0.16 while style sat at 0.51. The "system message" instruction itself did nothing, because the detector never reads instructions. PI01, PI03, PI04, PI05 and PI06 held for that reason.

*RQ11 is not a break.* The rate limiter returned 429 before the request was analysed, so the result is INCONCLUSIVE. It has to be rerun alone before it can be called held or broken. The route stage is not shown to be at fault.

*Also seen.* MF08 (60,000 characters) is marked HELD, but it came back with no `warning` field. That is the same gap as the criterion 5 miss.

**The pattern: nothing held across the board, and the misses collapse into three problems, not twenty.**

I did not hold everything. Three of five criteria missed (2, 3, 5), one is unverified (4), and 16 of 56 attacks broke. Counting by the signal that moved the score:

| Problem | Where it shows up | Stage |
|---|---|---|
| **1. Perplexity measures predictability, not authorship, and it errs in both directions.** | 10 of the 16 broken attacks. The 6 false positives (FP02 to FP07) fail because formal, templated or repetitive human text has low perplexity (`model_score` 0.74 to 0.88). EV01, EV04, EV05 and PI02 fail the other way: typos and odd words push perplexity up, so AI text reads as human (`model_score` as low as 0.16). It also explains why 2 of 5 clearly-human eval texts scored 0.75 and 0.83. | Signal one |
| **2. The scores overlap, so no threshold can fix it.** | Formal human text (FP02 to FP07) scored 0.72 to 0.77 combined. The clearly-AI eval texts scored 0.69 to 0.74. The human texts score *higher*. Lowering `AI_THRESHOLD` below 0.65 accuses more writers, and raising it above 0.77 lets all the AI through. This is the same cause as the missed criteria 2 and 3, where the mean gap was 0.15 and the human label was never reached. | Combining rule, then the label mapping |
| **3. Signal two is weak, and it agrees with signal one instead of checking it.** | Style scores were 0.51 to 0.58 on human and 0.55 to 0.61 on AI, so it barely separates anything. On the false positives it sat at 0.63 to 0.72 and joined the accusation, because uneven vocabulary and few varied punctuation marks are also what formal human text looks like. Three evasions (EV02, EV06, EV07) beat it with cheap edits. A 0.5/0.5 average of two signals that share the same blind spot gives no protection. | Signal two |

Two smaller causes sit outside these three:
- **The `MIN_WORDS` gate** (EV08, and the short bad-input cases). Both signals return 0.5 on short text. That is safe for humans, but short AI text can't be caught.
- **Whole-text scoring** (EV09). A human paragraph pasted ahead of AI text dilutes it, and nothing scores sections separately.

The best single fix is upstream of the thresholds. The false positives and the evasions are both caused by signal one reading predictability as authorship, so tuning the thresholds can't fix them. The second signal needs to measure something that doesn't move with register and padding.

**Were my targets too low?** Not in the way the question suggests, since I missed three of them. But one target was too easy, and it is **criterion 1**.
- It passed in all 3 trials at exactly 1 of 10, which is the limit with no margin.
- Eight of those ten texts landed in "unsure", so the pass came from the system not committing, not from it recognising my writing.
- The false-positive attacks show the real picture: 6 of 8 human texts were accused. The target held because my 10 texts were casual or ordinary writing, which signal one scores as human or unsure. It never faced the formal, non-native or templated writing that gets accused.
- I would tighten it by changing the test population, not the number: at most 1 of 10 accused, where the 10 must include at least 4 in a formal register, a rubric style, or written by a non-native speaker.
- By that standard, the current code would score 6 of 8, which is a clear miss.

The original criterion 1 stays as written in `criteria.md`. The tightened version is added below it as a revision.



---

## The Improvement

**What I changed:** I reweighted the signals. The model signal (perplexity) now counts for **0.3 instead of 0.5**, a cut of 0.2 (40% of its old weight), and the style signal counts for **0.7 instead of 0.5**. Only two numbers changed, in `config.py`: `WEIGHT_MODEL_SIGNAL = 0.3` and `WEIGHT_STYLE_SIGNAL = 0.7`. The rule in `scoring.py::combine_signals` is the same weighted average, and neither signal's own code changed. The goal was to stop a writer from being accused just because their English is careful and plain, which is what a non-native speaker often produces.

**Which diagnosis pointed at it:** Problem 1 in the diagnosis table: perplexity measures predictability, not authorship. FP03 (a non-native speaker writing carefully) got `model_score` 0.805, and the other formal or templated human texts got 0.74 to 0.88. The model signal was the larger driver of those accusations, so I turned it down.

**Why 0.3 and not lower.** I recomputed combined scores from the `model_score` and `style_score` values in `logs/audit.jsonl`, using the weights I was testing. Going below 0.3 starts to cost real AI detection. The 9 clearly-AI eval texts I could check (the clearly-AI and AI label-coverage sets) combined at 0.656 to 0.691 at 0.3, still above the 0.65 line but only just. The one that was already unsure stays unsure. At 0.2 they would sit around 0.62 to 0.66 and most would drop out. So 0.3 is about the lowest weight that keeps the AI texts I tested labelled "ai".

### Attack Run — After

Run with `python run_attacks.py --set /Users/camila/Downloads/attack_set --label after` against the service with the new 0.3/0.7 weights (`results/attack_run_2026-11-05_1645_after.md`, eval run in `results/run_2026-11-05_1646_after.md`). The "after" combined scores below come from the audit log of that run and match what I had predicted by recomputing the old scores, to four places. The tool's own "Score" column holds confidence, not the combined score, so I did not use it. The service again had no 5xx or crash.

**Result: 15 broke (was 16), 40 held (was 39), 1 inconclusive (unchanged).** The only attack whose verdict changed is PI02.

| ID | Targeting | Combined before (0.5/0.5) | Combined after (0.3/0.7) | Guess before → after | Verdict before → after |
|---|---|---|---|---|---|
| EV01 | typos | 0.407 | 0.505 | unsure → unsure | BROKE → BROKE |
| EV02 | broken-up sentences | 0.554 | 0.539 | unsure → unsure | BROKE → BROKE |
| EV03 | pasted quotation | 0.625 | 0.608 | unsure → unsure | BROKE → BROKE |
| EV04 | unusual words | 0.629 | 0.637 | unsure → unsure | BROKE → BROKE |
| EV05 | heavy human editing | 0.437 | 0.484 | unsure → unsure | BROKE → BROKE |
| EV06 | one very long, one very short sentence | 0.519 | 0.497 | unsure → unsure | BROKE → BROKE |
| EV07 | punctuation padding | 0.580 | 0.560 | unsure → unsure | BROKE → BROKE |
| EV08 | text below token window | 0.500 | 0.500 | unsure → unsure | BROKE → BROKE |
| EV09 | human opening bolted on | 0.628 | 0.606 | unsure → unsure | BROKE → BROKE |
| EV10 | repeated stanza structure | 0.917 | 0.893 | ai → ai | HELD → HELD |
| FP01 | plain, clear human writing | 0.635 | 0.642 | unsure → unsure | HELD → HELD |
| FP02 | formal register | 0.720 | 0.712 | ai → ai | BROKE → BROKE |
| FP03 | non-native speaker, careful | 0.746 | 0.722 | ai → ai | BROKE → BROKE |
| FP04 | student essay to a rubric | 0.736 | 0.697 | ai → ai | BROKE → BROKE |
| FP05 | technical documentation | 0.762 | 0.747 | ai → ai | BROKE → BROKE |
| FP06 | imitating a formal template | 0.755 | 0.705 | ai → ai | BROKE → BROKE |
| FP07 | deliberate repeated phrase | 0.772 | 0.728 | ai → ai | BROKE → BROKE |
| FP08 | very short human text | 0.500 | 0.500 | unsure → unsure | HELD → HELD |
| PI01 | ignore-the-check instruction | 0.502 | 0.518 | unsure → unsure | HELD → HELD |
| PI02 | system-message instruction + odd-word padding | 0.332 | 0.402 | **human → unsure** | **BROKE → HELD** |
| PI03 | instruction in the writer's voice | 0.540 | 0.542 | unsure → unsure | HELD → HELD |
| PI04 | hostile label text | 0.536 | 0.550 | unsure → unsure | HELD → HELD |
| PI05 | audit log injection | 0.500 | 0.500 | unsure → unsure | HELD → HELD |
| PI06 | instruction plus real human text | 0.589 | 0.612 | unsure → unsure | HELD → HELD |
| MF08 | 60,000 characters | 0.823 | 0.757 | ai → ai | HELD → HELD |

The other 30 attacks (MF01 to MF07, RQ01 to RQ12, FL01_01 to FL01_12) returned the same status and guess as before: the same 400s, the same 0.500 "unsure" results, and the flood blocked from the seventh request. RQ11 was rate-limited (429) again because the run sends 56 requests close together, so it is still INCONCLUSIVE and has to be rerun on its own.

### Eval run — before and after

Same `run_eval.py`, three trials each, and all three trials returned identical guesses both times. Combined scores are `0.5 × model + 0.5 × style` before and `0.3 × model + 0.7 × style` after, computed from the `model_score` and `style_score` in each response (the signal scores themselves did not change).

| Criterion | Before (0.5/0.5) | After (0.3/0.7) | Verdict before → after |
|---|---|---|---|
| 1. False positives, 10 own texts | 1 `ai`, 8 unsure, 1 human | 1 `ai`, **9 unsure, 0 human** | Met at the limit → Met at the limit |
| 2. Score spread, mean gap (target 0.4) | AI 0.71, human 0.56, **gap 0.15**. Lowest AI 0.688, highest human 0.678 (margin 0.01) | AI 0.665, human 0.549, **gap 0.116**. Lowest AI 0.656, highest human 0.617 (margin 0.039) | Missed → Missed |
| 3. Label coverage (12 texts) | human 0, ai 5, unsure 7 | human 0, **ai 4, unsure 8** | Missed (unsure at the 7 cap) → **Missed on two counts (unsure now over the cap)** |
| 4. Appeals | not run | not run | Unverified → Unverified |
| 5. Bad input | 3 of 4 (no `warning` on long text) | 3 of 4 | Missed → Missed |

Per-text guesses for the sets that moved, trial 1 (after combined score in brackets):

| Set | Before | After |
|---|---|---|
| Own writing | unsure ×8, ai ×1, human ×1 (the "living controversy" text, 0.323) | unsure ×9, ai ×1 (the same text is now unsure, 0.374) |
| Clearly human | unsure, unsure, unsure, unsure, ai | unsure ×5 (0.576, 0.481, 0.487, 0.584, 0.617) |
| Clearly AI | ai ×5 | ai ×5 (0.664, 0.658, 0.658, 0.687, 0.656) |
| Label set: human | unsure ×4 | unsure ×4 (0.578, 0.493, 0.433, 0.615) |
| Label set: AI | ai, unsure, ai, ai | ai, unsure, ai, ai (0.674, 0.634, 0.691, 0.658) |
| Label set: borderline | unsure, ai, unsure, ai | unsure, **unsure**, unsure, ai (0.597, 0.626, 0.604, 0.671) |

**Did it help, and how do I know:** **No, not for the goal I set, and it made two other things slightly worse.**

- **The false positives did not move.** FP02 to FP07 were "ai" before and are "ai" after, and FP03, the non-native speaker, went from 0.746 to 0.722 and is still labelled "ai", 0.07 over the line. The weights moved their scores by 0.008 to 0.050 and the label never changed. This is the result I flagged before the run: on these texts the style signal also reads as AI (0.63 to 0.72), so shifting weight onto it replaces one accusing score with another. A weighted average cannot turn two agreeing signals into a disagreement.
- **The one gain is on the evasion side.** PI02 no longer reaches the "human" label (0.332 → 0.402, now "unsure"), and the attack count goes from 16 to 15. That happened because the signal that padding fools now counts for less. It is not a fairness fix.
- **The trade it created.** Clean AI text lost margin: clearly-AI eval texts went from 0.69 to 0.74 down to 0.656 to 0.687, which is 0.006 to 0.037 above the 0.65 line. The score spread shrank (gap 0.15 → 0.116), because the signal that separates the two classes best now counts for less and the flatter one counts for more.
- **Two eval changes.** The borderline text that had been labelled "ai" at 0.7241 on the model signal is now "unsure" (0.626), so label coverage changed from `ai 5, unsure 7` to `ai 4, unsure 8`, and "unsure" is now over the cap of 7 of 12. The one human-labelled own-writing text also became "unsure", so the "human" label now appears nowhere in the eval at all. Criterion 2's no-overlap margin did get better (0.01 → 0.039), since human texts with high model scores were discounted.
- **Net:** one attack fixed, zero false positives fixed, the human label gone from the eval, and AI text closer to slipping under the line. I am keeping 0.3/0.7 because it has the one real gain and the AI texts I tested still land at "ai", but I would not call this the fix for non-native writers.

---

## Attacks of My Own - Stretch Feature

**What I'm adding:** three attacks I wrote myself, sent to my own service through `POST /submit` the way an outside user would, using a new script, `attack_own.py`. "Someone else's system" here means my service seen from the user's side, not another person's deployment. Each attack is sent next to an unmodified control, so any change in score comes from the edit. They are different from the 56-attack set: they target things I found in my own results, not the families in `attacks.csv`.

1. **Lookalike letters (evasion, signal one and two).** Take an AI paragraph and swap a few Latin letters for visually identical Cyrillic ones (`a`, `e`, `o`). A reader sees no change. GPT-2 splits the altered words into rare tokens, which should raise perplexity, and `stylometry.words()` only keeps `[a-z0-9']`, so those words should drop out of the vocabulary count.
2. **Hard-wrapped human text (false positive, signal two).** Take a human paragraph and break it into short lines, as happens when text is pasted from an email or terminal. I wrote in the README that newline splitting would make wrapped prose look short and uniform, and that I had not measured it. This measures it.
3. **AI text hidden past the token window (evasion, signal one).** Put about 450 tokens of casual human-style text first and the AI paragraph last. `DETECTOR_MAX_TOKENS = 400`, so signal one should never read the AI part, while signal two reads all of it. This is different from EV09, which bolted a short human opening on and did not test the 400-token cutoff.

All texts are written by me for the test (the "human" ones are my own writing, the "AI" one is an AI-style paragraph), so the results show mechanisms, not rates.

### What the three attacks did

Run with `python attack_own.py` at the 0.3/0.7 weights (raw output in `results/attack_own_2026-11-05_1656.json`). Each attack was sent as its own `creator_id` (`OWN1_attack` and so on), spaced 12 seconds apart to stay under the 6-per-minute limit, and all six returned 200. "Combined" is `0.3 × model + 0.7 × style`.

```
OWN1_control   200  unsure  model 0.7578  style 0.5949  combined 0.6438
OWN1_attack    200  unsure  model 0.415   style 0.7307  combined 0.636
OWN2_control   200  unsure  model 0.6173  style 0.5545  combined 0.5733
OWN2_attack    200  unsure  model 0.6173  style 0.6172  combined 0.6172
OWN3_control   200  unsure  model 0.7578  style 0.5949  combined 0.6438
OWN3_attack    200  unsure  model 0.6223  style 0.5935  combined 0.6021
```

| Attack | Model score (control → attack) | Style score (control → attack) | Combined | Label | Did it work? |
|---|---|---|---|---|---|
| OWN1 lookalike letters | 0.758 → 0.415 (−0.343) | 0.595 → 0.731 (+0.136) | 0.644 → 0.636 | unsure → unsure | **Half.** Signal one fell as predicted, signal two moved the wrong way. |
| OWN2 hard-wrapped human text | 0.617 → 0.617 (no change) | 0.555 → 0.617 (+0.063) | 0.573 → 0.617 | unsure → unsure | **Yes, in direction.** Human text looks more AI after wrapping, but not enough to cross 0.65. |
| OWN3 AI past the token window | 0.758 → 0.622 (−0.136) | 0.595 → 0.594 (no change) | 0.644 → 0.602 | unsure → unsure | **Yes, in mechanism.** Signal one stopped seeing the AI text. The label did not change. |

**No attack changed a label, and I need to say why that is a weak result.** The control for OWN1 and OWN3 is the same AI paragraph from my Sample Run. At the old 0.5/0.5 weights it scored 0.6764 and was labelled "ai". At 0.3/0.7 it scores 0.6438, which is 0.006 under `AI_THRESHOLD`, so it is "unsure" before any attack touches it. That is a side effect of my reweight: the label I used in the Sample Run to show the "ai" label no longer comes out of that text. An attack that starts from "unsure" can't be shown to move the label to "unsure", so the useful numbers are the signal scores, not the labels.

**OWN1: lookalike letters.** The perplexity half worked as predicted: `model_score` dropped from 0.758 to 0.415 (by 0.343) because the altered words tokenize into rare pieces, and that is a bigger move than any evasion in the attack set made with visible edits. A reader sees the same sentence. The style half went the other way from what I predicted. I thought `words()` would drop the altered words, but it splits each one at the Cyrillic letters instead. The same text went from 68 words (58 unique, type-token ratio 0.853) to 159 "words" (74 unique, ratio 0.465), because the fragments repeat. A low type-token ratio reads as repetitive vocabulary, so `style_score` rose from 0.595 to 0.731. The two signals moved in opposite directions and the weighted average roughly cancelled them (0.644 → 0.636). The 0.3/0.7 weights helped here: at the old 0.5/0.5 the same moves would have given 0.676 → 0.573, a drop of 0.10 that crosses the line. So this evasion works worse against the reweighted system than it would have before, and the reason is that signal two now counts for more and it happens to resist this edit. A better attacker would pair the lookalike letters with something that lowers signal two as well.

**OWN2: hard-wrapped human text.** This confirms the cost I wrote down in "A failure I found" and had not measured. The text is 81 words and 4 sentences (lengths 15, 40, 9, 17). Wrapped at 34 characters, `stylometry.sentences()` sees 17 lines of 2 to 8 words each. `model_score` did not move at all (0.6173 both times), which shows the whitespace fix in `detector.perplexity()` works. `style_score` rose from 0.555 to 0.617, and the combined score from 0.573 to 0.617, which is 0.033 under the AI line. It is one sample, but an ordinary email-wrapped paragraph moved most of the way toward an accusation with no change in wording. A writer who pastes hard-wrapped text from a terminal is the person this hurts, and a longer or more uniform wrapped text would likely cross the line.

**OWN3: AI text past the token window.** I made a 428-token casual opening and put the AI paragraph last. `model_score` fell from 0.758 to 0.622, and 0.622 is what GPT-2 says about the casual opening by itself, which means signal one never read the AI paragraph. `style_score` stayed 0.594 because it reads all the text, and the AI paragraph is a small share of it, so it barely moved. Two findings here. The attack works as designed: anything after about 300 words is invisible to signal one. And the casual human-style opening itself scored 0.62 on the model signal, which is high for text meant to read as clearly human, the same weakness as in the false-positive attacks. The combined score fell by 0.04 (0.644 → 0.602). A longer AI text, where the AI part is most of the text, would already have been scored on its first 400 tokens only, so this is mainly a gap for short AI text hidden inside a long human one.

**What I'd fix, in order:** (1) score the whole text in chunks of 400 tokens and average them, which closes OWN3 and helps EV09; (2) stop splitting on newlines when most lines don't end in punctuation, which is what hard-wrapping looks like (OWN2); (3) normalise lookalike letters to plain Latin before any signal reads the text, or treat a high share of non-Latin letters in an English text as a flag of its own (OWN1). I did not make any of these changes in this stretch, because the point was to attack the system as it stands.

**Limits of this test:** one text per attack and one control per attack, so these show mechanisms and a direction, not rates. All the texts are mine. I did not retest at 0.5/0.5, and the 0.5/0.5 figures for OWN1 above are calculated from the logged scores, not measured.

---

## Per-Creator Rate Limits - Stretch Feature

**What I'm adding:** a check, and one fix, for per-creator rate limiting, plus a note on what moving from per-address to per-creator changes. `rate_limit_key()` in `app.py` already counts a request against its `creator_id` and only falls back to the caller's address when the id is missing or isn't a string, so I'm not rebuilding that. I'm adding:

1. **A test script, `check_creator_limits.py`,** that sends short texts (under 40 words, so no model is loaded) and shows the difference in status codes: two creators behind one address, one creator spelled three ways, one script rotating ids, and a caller with no id at all.
2. **One fix:** the key is normalised (trimmed and case-folded) before it is counted. Today `"Camila"` and `"camila "` are two different callers, so a script can double its allowance by changing capitalisation.
3. **The note** on what per-creator limits change, including the new weakness they create.

My limits stay at 6 per minute and a daily cap (see "Rate Limiting" above). I'm changing who is counted, not how much.

### What the per-creator limit does

Run with `python check_creator_limits.py` (6 requests per minute, bursts of 9, all from this one machine). I ran it twice against the live service: once with the original `app.py` and once after the normalisation fix, restarting nothing in between (the dev server reloads itself). Each run uses fresh creator names, so counts from the earlier run did not carry over.

```
BEFORE (original app.py)                                   AFTER (normalised key)
1. one creator sends 9                                     1. one creator sends 9
   200 200 200 200 200 200 429 429 429                        200 200 200 200 200 200 429 429 429
2. a different creator, same address, sends 1              2. a different creator, same address, sends 1
   200                                                        200
3. creator 1 again, spelled three other ways               3. creator 1 again, spelled three other ways
   200 200 200                                                429 429 429
4. one script, a new creator_id on each of 9               4. one script, a new creator_id on each of 9
   200 200 200 200 200 200 200 200 200                        200 200 200 200 200 200 200 200 200
5. 9 requests with no creator_id                           5. 9 requests with no creator_id
   200 200 200 200 200 200 429 429 429                        200 200 200 200 200 200 429 429 429
6. a creator_id that is not a string, 1 request            6. a creator_id that is not a string, 1 request
   429                                                        429
```

| Case | What it shows |
|---|---|
| 1 | The limit works per creator: the seventh request is the first 429. |
| 2 | A second writer on the same address is unaffected. A per-address limit would have returned 429 here, because case 1 had already used that address's six. This is the one thing per-creator limits fix. (Inferred from case 1, not run separately.) |
| 3 | **The fix.** Before it, `"  WRITER-A… "`, `"Writer-A…"` and `" writer-a…"` each got a fresh allowance, so changing capitalisation tripled the budget. After it, all three count against the original creator and get 429. |
| 4 | **The weakness.** Nine requests with nine different ids all got 200. The limit counts whatever string the caller types, and anyone can type a new one. A per-address limit would have stopped this at six. I did not fix it (see below). |
| 5 | With no id the address is counted, so the sixth request is the last that gets through. |
| 6 | Returned 429 in both runs, but not because of its own count: a non-string id falls back to the address, and case 5 had already used up that address's six. It confirms that it shares the address bucket. |

**What per-creator limits change:**

- **Who it protects.** Writers who share an address (a household, a school, an office, a phone on a shared network) no longer use up each other's six submissions. This is the case where a per-address limit punishes the wrong person, and it matches the reason I gave in "Rate Limiting" for counting creators.
- **Who it stops protecting against.** The scripted caller. A per-address limit holds a script to six requests a minute whatever it calls itself. A per-creator limit holds it to six per name, and it picks the names (case 4). This is the same thing the attack set already does: every row in `attacks.csv` gets its own `creator_id`, so it "looks like a crowd of different callers" and never trips a limit. The 429s in my flood run only appeared because that test used one id on purpose.
- **What that does to my own argument.** In "Rate Limiting" I said my numbers should be "hostile" to a script mapping my thresholds. With per-creator counting they are not: a script that sends one request per fresh id is never limited, on the minute or the day cap, and can probe the thresholds as often as it likes. My numbers are liveable for the writer and not hostile to the script. I wrote that section before testing this.
- **A smaller cost.** Callers with no id (or a non-string id) all share one bucket per address, so anonymous callers on one network get six a minute between them. A caller gains nothing by leaving the id out, which is the reason to keep the fallback.
- **The daily cap has the same hole** as the minute cap, since it is keyed the same way.

**What I'd do next (not done):** keep the per-creator limit and add a much looser per-address limit beside it, say 10 times the per-creator one, so a household has room but one machine inventing ids hits a wall. The real fix is to count something the caller can't choose, such as a signed-in account. I did not add the address backstop here because the stretch asked for per-creator limits, and the right number for it depends on how many writers share an address, which I haven't measured.

**Limits of this test:** one run of each case from a single machine. It shows the behaviour of the key function, not how it holds up under load, and the counts are in memory, so restarting the service resets them. The "Rate Limiting" section above says 120 per day, but `config.py` has `RATE_LIMIT_PER_DAY = 100`. The code is what runs, so 100 is what applies, and the README number needs correcting.

---

## What's Still Broken

**Attacks still getting through (15 of 56 broke after the reweight):**

| Attacks | What's wrong | What I'd do | Why I stopped |
|---|---|---|---|
| **FP02 to FP07** (6 false positives, including FP03, the non-native speaker) | Formal, templated or repetitive human text is predictable to GPT-2 and has even sentences, so both signals say "ai" (combined 0.70 to 0.75 after the reweight). | Stop letting two correlated signals agree their way to an accusation. Options: add a signal that doesn't move with register (for example, how a text compares with the same writer's earlier submissions), or require that a text score "ai" on a measure other than predictability before the label can be "ai". A cheaper stopgap is raising `AI_THRESHOLD` above about 0.75, which would stop all six but also lets almost all the AI text I tested through (0.66 to 0.69). | A new signal is a new component with its own blind spot and needs its own test set, and I only had time for one improvement. The reweight was the change I could make and measure in one pass, and it showed that a weight cannot fix this. |
| **EV01 to EV07, EV09** (8 evasions) | Typos, rare words, broken-up sentences, pasted quotations and punctuation padding each move one signal by enough to push clean AI text (0.66 to 0.69) under 0.65. The margin is 0.04 or less, so almost any edit works. | Widen the margin by making each signal harder to move: normalise punctuation before measuring it, ignore quoted passages, and score paragraphs separately so a human opening can't dilute AI text (EV09). | Each of those is a separate fix to signal two or to the route, and each one would also change how honest human text scores. I did not want to change several things at once and not know which one helped. |
| **EV08** (short AI text) | Under 40 words both signals return 0.5, so short AI text is never caught. | Nothing I'd change. | This is the `MIN_WORDS` trade from the poem failure: with fewer than 40 words the signals can't tell a person from an AI, and an honest "unsure" is better than a guess. |
| **RQ11** | Rate-limited (429) before it was analysed, so it is still inconclusive. | Rerun it alone. | It needs a quiet minute, and nothing suggests the route is at fault. |
| **MF08** (60,000 characters) | Handled, but returns no `warning` field. | Add the length check and `warning` to `app.py::submit`. | Same gap as the criterion 5 miss. It is a small route change that I left alone because it doesn't touch the accusation problem. |

**Criteria still missed:**

- **Criterion 1 (false positives):** met at exactly 1 of 10, with no margin, and it only passes because 9 of the 10 land in "unsure". The 6 of 8 false-positive attacks show what it would score on formal or non-native writing. I'd tighten it by test population (at least 4 of the 10 formal, rubric-style or non-native) before trusting it.
- **Criterion 2 (score spread):** gap 0.116 against a target of 0.4. The two signals together can't separate the classes by that much, because the best one (model) is also the one that accuses formal human text. Getting there needs a better signal, not a better weight.
- **Criterion 3 (label coverage):** the "human" label never appears and "unsure" is now 8 of 12, over the cap. The reweight made this worse. At the current 0.35 `HUMAN_THRESHOLD`, human text would need a combined score below 0.35, and the lowest I saw on any human-written text was 0.374 (and 0.43 to 0.49 on the others I checked). I'd fix the signals first and then revisit the thresholds, because lowering `HUMAN_THRESHOLD` alone would label AI text "human".
- **Criterion 4 (appeals):** unverified. `run_eval.py` never calls `/appeal`. I'd add 10 appeals to the eval and check status and timestamps. I stopped because it was outside the one improvement.
- **Criterion 5 (bad input):** 3 of 4. The long-text `warning` was never implemented (see MF08).

**What the reweight taught me:** a weight can only move a combined score between the two signal scores. When both signals are wrong in the same direction, as on formal or non-native writing, no weighting helps. I should have checked whether the signals agreed on the false positives before choosing a reweight as the improvement. My own diagnosis table said signal two "agrees with signal one instead of checking it", and that predicted this result.

**The trade I'd make if this ran for real:**

I'd go toward fewer wrong accusations: keep the "ai" label hard to earn, raise `AI_THRESHOLD`, and accept that more AI text lands in "unsure" or gets through. The cost is paid by whoever relies on the check: a reader or reviewer who has to treat "unsure" as "unknown" and look at the text themselves, because a false "ai" label lands on a writer, often a non-native speaker, who has to prove they wrote their own words.


<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [x] criteria.md has five numbered criteria, each naming a target
       [x] Each has a reason underneath
       [x] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [x] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [x] POST /appeal changes status and writes to the log
       [x] Signals and Scoring names scoring.py::combine_signals
       [x] Sample Run: a submission AND an appeal, as pasted text
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
