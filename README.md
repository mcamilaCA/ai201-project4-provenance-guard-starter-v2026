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


# Unit 9 - Request-Level Observability and Failure Diagnostics

## Intention Summary 
| Shape | Execution Path | Proposed Extension | Central Question |
| -- | -- | -- | --|
| A- Deploy & Instrument| Local Execution with Logs |Operational Observability | Can we make the existing service easier to monitor, evaluate, and diagnose without changing its underlying classification behavior? |

## The Shape:

Choice: A- Deploy and Instrument

I want to add structured operational monitoring that records and measures the behavior of the system and existing API connection, this entails performance measurement, structured execution and failure record,  operational metrics and measurement of inference time and computing cost.

*Out of Scopes*
- Changipng model (currently is GPT2)
- Change classification algorithm
- Train a new model

## The change - After Run Results

TLDR: The system did not break.

Every request now gets a `run_id` (returned as the `X-Request-ID` header and written into its audit entry). Each request also leaves a structured record in `logs/runs.jsonl` with stage timings, model time kept separate from overhead, token count, cost and outcome, and failures go to `logs/failures.jsonl` with a category. `metrics.py`, `/metrics`, `/runs` and `/failures` read these back as counts, error rates, latency percentiles and cost. The classification code, scores, labels, response shapes and rate limits are unchanged, and the recording never raises into a route. Cost is $0 because the detector is a local GPT-2 and no pricing is set.

*Attempted Runs:*

The last five requests of the test session, in order. The calls are the ones from the test template, with the response bodies and ids taken from `logs/audit.jsonl` and `logs/runs.jsonl`. `confidence` is `|combined − 0.5| × 2`.

**Run 1 — `run3`, 5th submission of the burst: scored, labeled AI** (`run_id 68b4673d…`, 29.3 ms total, 28.5 ms of it model inference)

```bash
curl -si -X POST http://127.0.0.1:5000/submit -H "Content-Type: application/json" \
  -d '{"creator_id": "run3", "text": "The committee reviewed the proposal carefully and then adjourned for lunch. The committee reviewed the proposal carefully and then adjourned for lunch. The committee reviewed the proposal carefully and then adjourned for lunch. The committee reviewed the proposal carefully and then adjourned for lunch."}'
```

Output (`200`, header `X-Request-ID: 68b4673d8a9241c699d7d7999d0ee6b9`):
```json
{
  "content_id": "0f6417a1-ca48-44cc-9649-572449e2f9f9",
  "guess": "ai",
  "confidence": 0.8808,
  "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
  "model_score": 0.9781,
  "style_score": 0.9242
}
```

Repeated text, so both signals agree it is AI-like (model 0.9781, style 0.9242, combined 0.9404). The run record shows `model_signal` at 28.7 ms with 28.5 ms of inference, so the model dominates and overhead is tiny once it is warm.

**Run 2 — `run3`, 6th submission: scored, same result** (`run_id dca7d5a0…`, 29.4 ms)

```bash
curl -si -X POST http://127.0.0.1:5000/submit -H "Content-Type: application/json" \
  -d '{"creator_id": "run3", "text": "(same text as Run 1)"}'
```

Output (`200`): same scores and label as Run 1, with a new `content_id` (`37bf899a-292f-4989-8c9b-f23b60db6acf`) and `X-Request-ID: dca7d5a025664cf7aeb1ebea2c82af6d`. Identical input gives identical scores, so scoring is deterministic.

**Run 3 — `run3`, 7th submission: rate limited** (`run_id 8ddacc23…`, 0.4 ms, no stages ran)

```bash
curl -si -X POST http://127.0.0.1:5000/submit -H "Content-Type: application/json" \
  -d '{"creator_id": "run3", "text": "(same text as Run 1)"}'
```

Output (`429`, header `X-Request-ID: 8ddacc230bb84d38b68decbd1cea7b2c`):
```json
{
  "error": "rate_limited",
  "limit": "6 per 1 minute",
  "message": "Too many submissions. Try again shortly."
}
```
The limiter (6 per minute) turned it away before the pipeline ran. The refusal still left a trace: a `rejected` entry in `audit.jsonl`, a `rate_limit` record in `failures.jsonl`, and a `rate_limited` run record, all sharing this `run_id`.

**Run 4 — `run3`, 8th submission: rate limited** (`run_id 6ba99cba…`, 0.3 ms)

Same call and same `429` body as Run 3, with `X-Request-ID: 6ba99cba8aed47219f44e5a54e967e6f`. Recorded the same three ways.

**Run 5 — `run1`: short natural paragraph, labeled unsure** (`run_id 3520b692…`, 66.6 ms total, 64.3 ms model inference)

```bash
curl -si -X POST http://127.0.0.1:5000/submit -H "Content-Type: application/json" \
  -d '{"creator_id": "run1", "text": "I walked down to the harbour early, before the fishermen had even started on their nets, and the water was flat and grey. The gulls were quiet for once. My grandfather used to say that the sea keeps its own counsel, and standing there with cold hands and a thermos going lukewarm, I finally understood what he meant by it."}'
```

Output (`200`, header `X-Request-ID: 3520b692609c4580b77416cfa9d131d8`):
```json
{
  "content_id": "f0d9f5ec-b017-497d-9d8a-2517886159ac",
  "guess": "unsure",
  "confidence": 0.0654,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "model_score": 0.5381,
  "style_score": 0.5304
}
```

A different creator, so the limiter did not apply. The signals are near the middle (model 0.5381, style 0.5304, combined 0.5327), which gives the unsure label with low confidence.

**What the five runs show:** valid requests return the same response shape as before, the rate limit still triggers on the 7th request, refused requests are visible rather than silent, and every record from one request can be joined by its `run_id` (`curl "http://127.0.0.1:5000/runs?run_id=<id>"`). Across the whole session `metrics.py` reported an error rate of 0.0 and availability of 1.0.

## Structured Logging and Cost of One Run

### What one run record contains

Every request writes one JSON line to `logs/runs.jsonl`. The named fields:

| Field | Meaning |
|---|---|
| `run_id`, `started_at` | Which request and when (UTC). The same `run_id` is in the audit entry and any failure record |
| `route`, `method`, `http_status`, `outcome` | What was called and how it ended (`ok`, `client_error`, `rate_limited`, `server_error`) |
| `input` | `chars`, `words` and `sha256_16` (a short hash) of the submitted text. **The text itself is never stored**; the hash lets you spot the same text arriving twice |
| output | `context.label` and `context.content_id` here; the guess and all three scores are in `audit.jsonl` under the same `run_id` |
| `duration_ms`, `stages[]` | Total time and time per stage, with `inference_ms` and `overhead_ms` on the model stage |
| `inference[]`, `usage` | Model name, tokens read, tokenize/forward/load time, cold-start flag |
| `cost` | Dollar figure (token pricing plus optional hourly machine rate) and `compute_seconds` (below) |

Failed runs leave a record too, in `logs/failures.jsonl` (stage, error type, message, category, same `run_id`), so a failure never shows up only as an absence.

### What a run costs

The detector is a local model, so there is no API spend and the dollar figure is 0.00. The real cost of a run is **seconds of compute**, so that is what each run record now measures in `cost.compute_seconds`:

- `wall`: the whole request, start to finish (`time.perf_counter`)
- `inference`: the GPT-2 forward pass alone
- `cpu`: CPU seconds the process used (`time.process_time`, all threads)

The existing dollar calculation is unchanged and still sits beside it.

### How I measured it

`python measure_cost.py` runs the real `/submit` route in-process (so it uses the same stages and telemetry as a live request, with logs sent to a temp folder rather than `logs/`). It does one warm-up submission first, to pay the one-time model load, then **10 timed submissions**, one at a time, each a different writing sample of at least 40 words from `scenarios.py`. It reads each run's measured seconds and tokens back from the telemetry record, then writes mean, standard deviation, min, max and every per-run row to `results/cost_measurement_<timestamp>.md`.

### Result (10 runs, this laptop)

| Measure | Mean | Std dev | Min | Max |
|---|---|---|---|---|
| Wall time (s) | 0.0314 | 0.0028 | 0.0273 | 0.0355 |
| Model inference (s) | 0.0306 | 0.0028 | 0.0265 | 0.0346 |
| CPU time (s) | 0.0467 | 0.0053 | 0.0398 | 0.0556 |
| Input tokens | 69.2 | 8.8 | 58 | 86 |

**One scored run costs about 0.03 s of wall time and 0.05 s of CPU, for about 69 tokens.** The model is about 97% of the wall time, so the rest of the pipeline (style signal, scoring, label, audit write) is negligible. CPU is higher than wall because PyTorch uses several threads at once. The one-time cold start (loading GPT-2) was about 2.3 s, measured separately and not included in the average. These numbers belong to this machine at the time of the run; texts shorter than 40 words skip the model and cost almost nothing. To turn seconds into dollars, set `AI201_COMPUTE_USD_PER_HOUR`.

## Instrumentation

Every request appends one structured record to `logs/runs.jsonl`, and every failed request appends one to `logs/failures.jsonl`. Both are JSON lines I read back with `python metrics.py`, `/runs` and `/failures`. Nothing is printed to the terminal instead of logged.

The entries below are real lines copied unedited from those files. They were produced by sending ten submissions to the running service (`instrumentation-1` to `instrumentation-10`, ten different writing samples from `scenarios.py`, one request each) and one refused input. Fields to look for: `run_id` and `started_at`; `input` (length and hash, never the text); `outcome` and `http_status`; `duration_ms` and per-stage `stages`, where the model stage splits into `inference_ms` (model call alone) and `overhead_ms` (everything else); `usage` (tokens); `cost` (dollars plus measured `compute_seconds`); and `context` (the label and `content_id` returned).

### Ten successful runs (`logs/runs.jsonl`)

```json
{"schema_version": 1, "record_type": "run", "run_id": "b4e9e137a6c44143a10675e0c097dbb7", "started_at": "2026-11-13T04:44:48.623+00:00", "route": "/submit", "method": "POST", "http_status": 200, "outcome": "ok", "duration_ms": 7155.039, "input": {"chars": 815, "words": 139, "sha256_16": "6171cfca8d19792b"}, "stages": [{"name": "model_signal", "status": "ok", "duration_ms": 7153.715, "inference_ms": 994.043, "overhead_ms": 6159.672}, {"name": "style_signal", "status": "ok", "duration_ms": 0.254}, {"name": "combine", "status": "ok", "duration_ms": 0.002}, {"name": "label", "status": "ok", "duration_ms": 0.001}, {"name": "audit_write", "status": "ok", "duration_ms": 0.498}], "inference": [{"model": "gpt2", "input_tokens": 173, "tokenize_ms": 4.922, "forward_ms": 994.043, "load_ms": 5534.739, "cold_start": true}], "usage": {"model": "gpt2", "input_tokens": 173, "output_tokens": 0, "source": "local"}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": "gpt2", "compute_seconds": {"wall": 7.155039, "inference": 0.994043, "cpu": 1.708722}}, "failure_categories": [], "context": {"content_id": "c88ea7ac-3919-4594-b5a1-233b5eb8640b", "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you."}}
{"schema_version": 1, "record_type": "run", "run_id": "b7482800dbd043ac8b4f7b6dafad905f", "started_at": "2026-11-13T04:44:55.781+00:00", "route": "/submit", "method": "POST", "http_status": 200, "outcome": "ok", "duration_ms": 40.189, "input": {"chars": 436, "words": 67, "sha256_16": "eb3d58ad5172a284"}, "stages": [{"name": "model_signal", "status": "ok", "duration_ms": 39.414, "inference_ms": 39.03, "overhead_ms": 0.384}, {"name": "style_signal", "status": "ok", "duration_ms": 0.109}, {"name": "combine", "status": "ok", "duration_ms": 0.002}, {"name": "label", "status": "ok", "duration_ms": 0.001}, {"name": "audit_write", "status": "ok", "duration_ms": 0.327}], "inference": [{"model": "gpt2", "input_tokens": 74, "tokenize_ms": 0.34, "forward_ms": 39.03, "load_ms": 0.0, "cold_start": false}], "usage": {"model": "gpt2", "input_tokens": 74, "output_tokens": 0, "source": "local"}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": "gpt2", "compute_seconds": {"wall": 0.040189, "inference": 0.03903, "cpu": 0.058964}}, "failure_categories": [], "context": {"content_id": "c679a59b-e560-4347-893e-cbddb8752efb", "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you."}}
{"schema_version": 1, "record_type": "run", "run_id": "23329f5ab334499ebbbc0377f044535f", "started_at": "2026-11-13T04:44:55.823+00:00", "route": "/submit", "method": "POST", "http_status": 200, "outcome": "ok", "duration_ms": 35.356, "input": {"chars": 309, "words": 55, "sha256_16": "c4ed25c4ca10a244"}, "stages": [{"name": "model_signal", "status": "ok", "duration_ms": 34.705, "inference_ms": 34.418, "overhead_ms": 0.287}, {"name": "style_signal", "status": "ok", "duration_ms": 0.089}, {"name": "combine", "status": "ok", "duration_ms": 0.001}, {"name": "label", "status": "ok", "duration_ms": 0.001}, {"name": "audit_write", "status": "ok", "duration_ms": 0.2}], "inference": [{"model": "gpt2", "input_tokens": 61, "tokenize_ms": 0.243, "forward_ms": 34.418, "load_ms": 0.0, "cold_start": false}], "usage": {"model": "gpt2", "input_tokens": 61, "output_tokens": 0, "source": "local"}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": "gpt2", "compute_seconds": {"wall": 0.035356, "inference": 0.034418, "cpu": 0.048743}}, "failure_categories": [], "context": {"content_id": "ebc1dfd1-a0dc-42f3-872d-66737ec38a40", "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result."}}
{"schema_version": 1, "record_type": "run", "run_id": "3e5a2ae48cc241ec9896291ec78a23f8", "started_at": "2026-11-13T04:44:55.860+00:00", "route": "/submit", "method": "POST", "http_status": 200, "outcome": "ok", "duration_ms": 36.456, "input": {"chars": 437, "words": 73, "sha256_16": "40a279717c8ac97d"}, "stages": [{"name": "model_signal", "status": "ok", "duration_ms": 35.87, "inference_ms": 35.571, "overhead_ms": 0.299}, {"name": "style_signal", "status": "ok", "duration_ms": 0.097}, {"name": "combine", "status": "ok", "duration_ms": 0.002}, {"name": "label", "status": "ok", "duration_ms": 0.001}, {"name": "audit_write", "status": "ok", "duration_ms": 0.197}], "inference": [{"model": "gpt2", "input_tokens": 86, "tokenize_ms": 0.264, "forward_ms": 35.571, "load_ms": 0.0, "cold_start": false}], "usage": {"model": "gpt2", "input_tokens": 86, "output_tokens": 0, "source": "local"}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": "gpt2", "compute_seconds": {"wall": 0.036456, "inference": 0.035571, "cpu": 0.057359}}, "failure_categories": [], "context": {"content_id": "82074d62-0221-4d38-8f68-f752196d3ebe", "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you."}}
{"schema_version": 1, "record_type": "run", "run_id": "e86c2fad253a43cbaad938ed3f8ec2f0", "started_at": "2026-11-13T04:44:55.898+00:00", "route": "/submit", "method": "POST", "http_status": 200, "outcome": "ok", "duration_ms": 30.909, "input": {"chars": 254, "words": 46, "sha256_16": "db0f2521d505c17e"}, "stages": [{"name": "model_signal", "status": "ok", "duration_ms": 30.34, "inference_ms": 30.101, "overhead_ms": 0.239}, {"name": "style_signal", "status": "ok", "duration_ms": 0.083}, {"name": "combine", "status": "ok", "duration_ms": 0.001}, {"name": "label", "status": "ok", "duration_ms": 0.0}, {"name": "audit_write", "status": "ok", "duration_ms": 0.173}], "inference": [{"model": "gpt2", "input_tokens": 58, "tokenize_ms": 0.206, "forward_ms": 30.101, "load_ms": 0.0, "cold_start": false}], "usage": {"model": "gpt2", "input_tokens": 58, "output_tokens": 0, "source": "local"}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": "gpt2", "compute_seconds": {"wall": 0.030909, "inference": 0.030101, "cpu": 0.042945}}, "failure_categories": [], "context": {"content_id": "e2992d6a-be73-4d7a-8b3c-0471a92756a4", "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you."}}
{"schema_version": 1, "record_type": "run", "run_id": "d84df6bb8d184fa7a429d1c57451d860", "started_at": "2026-11-13T04:44:55.930+00:00", "route": "/submit", "method": "POST", "http_status": 200, "outcome": "ok", "duration_ms": 36.39, "input": {"chars": 381, "words": 67, "sha256_16": "8521169ca371f1f6"}, "stages": [{"name": "model_signal", "status": "ok", "duration_ms": 35.802, "inference_ms": 35.541, "overhead_ms": 0.261}, {"name": "style_signal", "status": "ok", "duration_ms": 0.104}, {"name": "combine", "status": "ok", "duration_ms": 0.001}, {"name": "label", "status": "ok", "duration_ms": 0.0}, {"name": "audit_write", "status": "ok", "duration_ms": 0.2}], "inference": [{"model": "gpt2", "input_tokens": 81, "tokenize_ms": 0.227, "forward_ms": 35.541, "load_ms": 0.0, "cold_start": false}], "usage": {"model": "gpt2", "input_tokens": 81, "output_tokens": 0, "source": "local"}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": "gpt2", "compute_seconds": {"wall": 0.03639, "inference": 0.035541, "cpu": 0.053936}}, "failure_categories": [], "context": {"content_id": "cdb56c95-03e0-41fd-90b4-fecfc65b6e52", "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you."}}
{"schema_version": 1, "record_type": "run", "run_id": "6087efa4715943e38537343c73054fb7", "started_at": "2026-11-13T04:44:55.967+00:00", "route": "/submit", "method": "POST", "http_status": 200, "outcome": "ok", "duration_ms": 32.933, "input": {"chars": 301, "words": 56, "sha256_16": "aa64862e571c02ae"}, "stages": [{"name": "model_signal", "status": "ok", "duration_ms": 32.393, "inference_ms": 32.154, "overhead_ms": 0.239}, {"name": "style_signal", "status": "ok", "duration_ms": 0.095}, {"name": "combine", "status": "ok", "duration_ms": 0.001}, {"name": "label", "status": "ok", "duration_ms": 0.001}, {"name": "audit_write", "status": "ok", "duration_ms": 0.182}], "inference": [{"model": "gpt2", "input_tokens": 66, "tokenize_ms": 0.207, "forward_ms": 32.154, "load_ms": 0.0, "cold_start": false}], "usage": {"model": "gpt2", "input_tokens": 66, "output_tokens": 0, "source": "local"}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": "gpt2", "compute_seconds": {"wall": 0.032933, "inference": 0.032154, "cpu": 0.047335}}, "failure_categories": [], "context": {"content_id": "71429f54-5971-43b8-9897-66b71dd32498", "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you."}}
{"schema_version": 1, "record_type": "run", "run_id": "d0ed470b711d43cbbfc8ba7c1f0cf245", "started_at": "2026-11-13T04:44:56.002+00:00", "route": "/submit", "method": "POST", "http_status": 200, "outcome": "ok", "duration_ms": 32.909, "input": {"chars": 316, "words": 55, "sha256_16": "d5887b34690f29ba"}, "stages": [{"name": "model_signal", "status": "ok", "duration_ms": 32.369, "inference_ms": 32.101, "overhead_ms": 0.268}, {"name": "style_signal", "status": "ok", "duration_ms": 0.085}, {"name": "combine", "status": "ok", "duration_ms": 0.001}, {"name": "label", "status": "ok", "duration_ms": 0.0}, {"name": "audit_write", "status": "ok", "duration_ms": 0.176}], "inference": [{"model": "gpt2", "input_tokens": 67, "tokenize_ms": 0.236, "forward_ms": 32.101, "load_ms": 0.0, "cold_start": false}], "usage": {"model": "gpt2", "input_tokens": 67, "output_tokens": 0, "source": "local"}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": "gpt2", "compute_seconds": {"wall": 0.032909, "inference": 0.032101, "cpu": 0.047815}}, "failure_categories": [], "context": {"content_id": "311d8046-a122-4028-bee7-efca37c32595", "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you."}}
{"schema_version": 1, "record_type": "run", "run_id": "b50a82543ead403794db4743db180a63", "started_at": "2026-11-13T04:44:56.036+00:00", "route": "/submit", "method": "POST", "http_status": 200, "outcome": "ok", "duration_ms": 32.767, "input": {"chars": 286, "words": 58, "sha256_16": "cb7d53a482c15b3b"}, "stages": [{"name": "model_signal", "status": "ok", "duration_ms": 32.202, "inference_ms": 31.946, "overhead_ms": 0.256}, {"name": "style_signal", "status": "ok", "duration_ms": 0.086}, {"name": "combine", "status": "ok", "duration_ms": 0.001}, {"name": "label", "status": "ok", "duration_ms": 0.001}, {"name": "audit_write", "status": "ok", "duration_ms": 0.205}], "inference": [{"model": "gpt2", "input_tokens": 69, "tokenize_ms": 0.217, "forward_ms": 31.946, "load_ms": 0.0, "cold_start": false}], "usage": {"model": "gpt2", "input_tokens": 69, "output_tokens": 0, "source": "local"}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": "gpt2", "compute_seconds": {"wall": 0.032767, "inference": 0.031946, "cpu": 0.047638}}, "failure_categories": [], "context": {"content_id": "d53bd395-1342-435c-8288-cea716b4dd50", "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you."}}
{"schema_version": 1, "record_type": "run", "run_id": "3be92c0fb03b4793994089e560ee7730", "started_at": "2026-11-13T04:44:56.070+00:00", "route": "/submit", "method": "POST", "http_status": 200, "outcome": "ok", "duration_ms": 32.806, "input": {"chars": 283, "words": 53, "sha256_16": "43ce281102b86257"}, "stages": [{"name": "model_signal", "status": "ok", "duration_ms": 32.295, "inference_ms": 32.022, "overhead_ms": 0.273}, {"name": "style_signal", "status": "ok", "duration_ms": 0.079}, {"name": "combine", "status": "ok", "duration_ms": 0.001}, {"name": "label", "status": "ok", "duration_ms": 0.001}, {"name": "audit_write", "status": "ok", "duration_ms": 0.173}], "inference": [{"model": "gpt2", "input_tokens": 67, "tokenize_ms": 0.242, "forward_ms": 32.022, "load_ms": 0.0, "cold_start": false}], "usage": {"model": "gpt2", "input_tokens": 67, "output_tokens": 0, "source": "local"}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": "gpt2", "compute_seconds": {"wall": 0.032806, "inference": 0.032022, "cpu": 0.04743}}, "failure_categories": [], "context": {"content_id": "c3d78f46-7ee7-4548-ae99-5eb41a68e9ec", "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you."}}
```

### One failed run: rejected input

A submission whose `text` was only spaces (`creator_id` `instrumentation-rejected`) was refused with `400 invalid_text`. It left a run record, with `outcome: client_error`, no stages and no model time:

```json
{"schema_version": 1, "record_type": "run", "run_id": "dc1c16c16c584140a14029b2f151e0f2", "started_at": "2026-11-13T04:44:56.104+00:00", "route": "/submit", "method": "POST", "http_status": 400, "outcome": "client_error", "duration_ms": 0.295, "input": {"chars": 3, "words": 0, "sha256_16": "0aad7da77d2ed59c"}, "stages": [], "inference": [], "usage": {"model": null, "input_tokens": 0, "output_tokens": 0, "source": null}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": null, "compute_seconds": {"wall": 0.000295, "inference": 0.0, "cpu": 0.000299}}, "failure_categories": ["validation_failure"], "context": {}}
```

and a failure record with the stage, category and message, sharing the same `run_id`:

```json
{"schema_version": 1, "record_type": "failure", "run_id": "dc1c16c16c584140a14029b2f151e0f2", "timestamp": "2026-11-13T04:44:56.104+00:00", "route": "/submit", "stage": "validate", "category": "validation_failure", "error_type": null, "message": "invalid_text", "http_status": 400, "context": {}}
```

The failure path was exercised with other failures earlier in testing: a rate-limited request (`429`, category `rate_limit`) and a wrong-method request (`405`) both appear in `logs/failures.jsonl`. A simulated model-load failure (`DetectorUnavailable`, category `model_unavailable`, recorded against the `model_signal` stage) is covered in `test_telemetry.py`. No timeout or unhandled `500` has occurred in the live service, so those categories are tested but have no live example.

## What It Costs

**The number: one scored run costs about 0.031 s of wall-clock time, 0.047 s of CPU time and reads about 69 tokens. The dollar cost is 0.00.** The detector is a local GPT-2, so there is no API spend. The real cost is seconds of compute, so that is what I measured.

**How I measured it:** `python measure_cost.py` sent 10 submissions through the real `/submit` route (in-process, logs in a temp folder), one at a time, each a different writing sample of at least 40 words, after one warm-up run that paid the one-time model load. For each run it read back the seconds the telemetry recorded: wall time with `time.perf_counter`, model-only time around the GPT-2 forward pass, and process CPU time with `time.process_time`. It averaged the ten. Full per-run table: `results/cost_measurement_2026-11-12_2241.md`.

| Measure | Mean (10 runs) | Std dev | Min | Max |
|---|---|---|---|---|
| Wall time (s) | 0.0314 | 0.0028 | 0.0273 | 0.0355 |
| Model inference (s) | 0.0306 | 0.0028 | 0.0265 | 0.0346 |
| CPU time (s) | 0.0467 | 0.0053 | 0.0398 | 0.0556 |
| Input tokens | 69.2 | 8.8 | 58 | 86 |

The model call is about 97% of wall time. Not counted in the average: the one-time model load on the first request after a start (2.3 s in this measurement; 4.3 s and 2.5 s in two earlier sessions). The figures are for this laptop; CPU exceeds wall because PyTorch uses several threads. Texts under 40 words skip the model and cost almost nothing. To convert seconds to dollars, set `AI201_COMPUTE_USD_PER_HOUR`.

### What it would cost for a hundred people a day

**Assumptions (mine, not measured):** each person submits 5 texts a day, and a machine costs $0.10 an hour (an illustrative rate, not a quote; the shipped setting is $0, see `AI201_COMPUTE_USD_PER_HOUR`). The per-run figures are the measured ones above.

```
runs per day         = 100 people x 5 texts                      = 500 runs
wall-clock compute   = 500 runs x 0.0314 s                      = 15.7 s per day
CPU compute          = 500 runs x 0.0467 s                      = 23.35 s per day
tokens read          = 500 runs x 69.2 tokens                   = 34,600 tokens per day
dollars (own rate)   = 15.7 s / 3600 s per hour x $0.10 per hour = $0.00044 per day  ($0.013 per 30 days)
```

**In one sentence: a hundred people submitting five texts each is 500 runs and about 16 seconds of compute a day, which at $0.10 an hour is about $0.0004 a day (under two cents a month), and $0 on my own laptop.**

Two things the multiplication shows, so the small number isn't misleading:

- **The rate limit sets the ceiling.** `config.py` allows up to 100 submissions per creator per day, so the worst case for 100 people is 100 x 100 = 10,000 runs x 0.0314 s = 314 s = 5.2 minutes of compute, which is $0.0087 a day at the same rate. Still small, because every run is about 31 ms.
- **The cost that matters is keeping the model loaded, not running it.** A service that has to be up all day costs by the hour whether or not anyone submits: 24 h x $0.10 = $2.40 a day ($72 per 30 days), about 5,500 times the compute the runs actually use. Add the 2 to 4 second cold load after every restart, and the GPT-2 model plus torch needing far more than a free host's 512 MB (see `RUNNING.md`), and the bill for a hundred people is set by the always-on machine, not by the 0.0314 s per run.

## How Each Unit 9 Criterion Is Run

The five criteria (U9-1 to U9-5) are in `criteria.md`. This section says what has to be run to produce the number for each one. `python check_unit9.py` runs all of it, three times, and writes the numbers to `results/unit9_criteria_<timestamp>.md` (and `.json`). A criterion is met only if all 3 trials pass.

**Setup common to all five.** The script serves a private copy of the real app over HTTP on a free local port and sends its logs to a temp folder, so `logs/` is not touched. It loads the model and warms it up once before trial 1 (not counted). Each trial uses a fresh `creator_id`, so rate-limit counts never carry over.

| Criterion | What is run, per trial | Total across 3 trials |
|---|---|---|
| **U9-1** traceability | One 20-request batch: 6 valid submits from one creator, 2 more from that creator (these are the rate-limited ones), 4 valid submits from other creators, 3 refused inputs (spaces only, no `text` field, `text` that is a number), 3 `/ping`, 2 `/health`. Then read each response's `X-Request-ID`, count it in `runs.jsonl`, and look for it in `audit.jsonl` | 60 requests |
| **U9-2** failure records | Failures are **triggered on purpose**: 2 refused inputs, and 8 submits from one creator so the 7th and 8th get a `429`. Then a separate process is started with `AI201_DETECTOR_MODEL=not-a-real-model-xyz` and sent one valid 40+ word text, forcing a real model-load failure (`500`). The failure file must hold exactly the expected records, no extras, each with the right stage, category and status | 15 deliberate failures |
| **U9-3** timing | 20 `/submit` requests over real HTTP after the warm-up, one at a time, each with a different text. A client stopwatch around the whole HTTP call is compared with the recorded `duration_ms`, and the stage durations are summed | 60 timed requests, reported as a distribution |
| **U9-4** metrics | One 21-request batch (6 valid + 2 rate-limited from one creator, 10 valid from others, 3 refused). Then `GET /metrics`, and the same six figures recounted in plain Python from `runs.jsonl` and `failures.jsonl` | 63 requests |
| **U9-5** telemetry never in the way | (a) 10 fixed texts, each submitted twice, telemetry on then off (`AI201_TELEMETRY=0`), comparing every field of the two responses except the new `content_id`. (b) `runs.jsonl` and `failures.jsonl` made into directories so every telemetry write fails, then 10 valid submits and 1 blank-text submit | 63 requests |

**Why this much.** U9-2 needs failures, so the script causes each kind itself rather than waiting for one. U9-3 is about latency, so it uses 20 requests per trial (60 in all) and reports min, mean, p50, p95, p99 and max of the gap between the two clocks, not one number. The model-load failure runs in its own process because the model is cached in memory once loaded, so it can't be broken from inside a process that already loaded it.

### Result of the run (3 trials)

| Criterion | Trial 1 | Trial 2 | Trial 3 | Verdict |
|---|---|---|---|---|
| U9-1 traceability: 20/20 headers, 20/20 run records, 15/15 audit entries | PASS | PASS | PASS | **MET** |
| U9-2 failure records: 5/5 exactly one correct record | PASS | PASS | PASS | **MET** |
| U9-3 timing: 20/20 within 15 ms and stages ≥ 98% | PASS | PASS | PASS | **MET** |
| U9-4 metrics: 6/6 figures equal the recount | PASS | PASS | PASS | **MET** |
| U9-5 telemetry never in the way: 10/10 and 11/11 | PASS | PASS | PASS | **MET** |

Numbers behind the timing cell: the client clock was 0.96 to 2.27 ms above the recorded time (15 ms allowed), the stages covered at least 98.7% of each request (98% required), and the model call was at least 99% of the model stage. Request latency over the 60 timed requests: mean 36.3 ms, p50 33.1, p95 57.2, p99 66.3, max 73.2.

Two things worth knowing about this result. First, the stage-coverage margin is thin: the lowest value, 98.7%, passed a 98% threshold by under one point, so a small amount of new untimed work in the request path would make U9-3 fail. Second, I checked that the script can report a miss: tightening the gap limit to 0.5 ms, or the coverage to 99.9%, makes U9-3 fail 0 of 20, as it should.

### Real output behind each criterion

Everything below is copied, unedited, from trial 1 of the run above. The lines come from the log files that trial wrote and from `results/unit9_criteria_2026-11-12_2309.json`. The run wrote its logs to a temp folder, so a copy of trial 1's files is kept in `results/unit9_2026-11-12_2309_trial1_logs/` and every line can be checked against its source (`t1-u1/` for U9-1, `t1-u2/` and `t1-badmodel-logs/` for U9-2, `t1-u3/` for U9-3, `t1-u4/` for U9-4, `t1-u5a/` and `t1-u5b/` for U9-5; `.gitkeep` files stand in for the two directories U9-5 creates in place of the telemetry logs). Long files are cut to a few representative lines, and each block says how many there were.

#### **U9-1: Traceability — MET**

- *Function:* `u9_1`  *File:* `check_unit9.py` — sends the 20-request batch and counts the ids
- *Function:* `Run.finish`  *File:* `telemetry.py` — writes each run record, through `write_record`
- *Function:* `_append`  *File:* `audit.py` — writes each audit entry and copies the `run_id` into it

Trial 1's batch produced 20 run records and 15 audit entries. Three of the 20 run records are shown (a valid submit, a rate-limited request, a refused input). The audit entries that follow them carry the same `run_id`, which is the join this criterion checks. The last block is what `u9_1` reported.

```json
{"schema_version": 1, "record_type": "run", "run_id": "2fe3c66c04c543ddb7b2c4ba436c0931", "started_at": "2026-11-13T05:09:45.991+00:00", "route": "/submit", "method": "POST", "http_status": 200, "outcome": "ok", "duration_ms": 56.606, "input": {"chars": 815, "words": 139, "sha256_16": "6171cfca8d19792b"}, "stages": [{"name": "model_signal", "status": "ok", "duration_ms": 55.869, "inference_ms": 55.525, "overhead_ms": 0.344}, {"name": "style_signal", "status": "ok", "duration_ms": 0.137}, {"name": "combine", "status": "ok", "duration_ms": 0.001}, {"name": "label", "status": "ok", "duration_ms": 0.001}, {"name": "audit_write", "status": "ok", "duration_ms": 0.284}], "inference": [{"model": "gpt2", "input_tokens": 173, "tokenize_ms": 0.297, "forward_ms": 55.525, "load_ms": 0.0, "cold_start": false}], "usage": {"model": "gpt2", "input_tokens": 173, "output_tokens": 0, "source": "local"}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": "gpt2", "compute_seconds": {"wall": 0.056606, "inference": 0.055525, "cpu": 0.096898}}, "failure_categories": [], "context": {"content_id": "d155d481-c9d5-4909-9364-5ce77a24b749", "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you."}}
{"schema_version": 1, "record_type": "run", "run_id": "134cdc1b3f6b4763adbdb0a53ead7f75", "started_at": "2026-11-13T05:09:46.217+00:00", "route": "/submit", "method": "POST", "http_status": 429, "outcome": "rate_limited", "duration_ms": 0.282, "input": null, "stages": [], "inference": [], "usage": {"model": null, "input_tokens": 0, "output_tokens": 0, "source": null}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": null, "compute_seconds": {"wall": 0.000282, "inference": 0.0, "cpu": 0.000294}}, "failure_categories": ["rate_limit"], "context": {}}
{"schema_version": 1, "record_type": "run", "run_id": "500229f073394afe874e4a96c79dc774", "started_at": "2026-11-13T05:09:46.373+00:00", "route": "/submit", "method": "POST", "http_status": 400, "outcome": "client_error", "duration_ms": 0.256, "input": {"chars": 3, "words": 0, "sha256_16": "0aad7da77d2ed59c"}, "stages": [], "inference": [], "usage": {"model": null, "input_tokens": 0, "output_tokens": 0, "source": null}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": null, "compute_seconds": {"wall": 0.000256, "inference": 0.0, "cpu": 0.000269}}, "failure_categories": ["validation_failure"], "context": {}}
```

```json
{"timestamp": "2026-11-13T05:09:46+00:00", "content_id": "d155d481-c9d5-4909-9364-5ce77a24b749", "creator_id": "t1u1-flood", "guess": "unsure", "model_score": 0.4578, "style_score": 0.6731, "combined_score": 0.6085, "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.", "status": "decided", "run_id": "2fe3c66c04c543ddb7b2c4ba436c0931"}
{"timestamp": "2026-11-13T05:09:46+00:00", "creator_id": "t1u1-flood", "event": "rejected", "status": "rejected", "reason": "rate_limited", "limit": "6 per 1 minute", "run_id": "134cdc1b3f6b4763adbdb0a53ead7f75"}
{"timestamp": "2026-11-13T05:09:46+00:00", "creator_id": "t1u1-bad", "event": "rejected", "status": "rejected", "reason": "invalid_text", "run_id": "500229f073394afe874e4a96c79dc774"}
```

```json
{"trial": 1, "pass": true, "detail": {"header": "20/20", "one run record each": "20/20", "run records in file": 20, "audit entries joined": "15/15"}}
```

#### **U9-2: Failure records — MET**

- *Function:* `u9_2`  *File:* `check_unit9.py` — deliberately causes the failures (2 refused inputs, 2 rate-limited requests) and checks each record
- *Function:* `u9_2_bad_model`  *File:* `check_unit9.py` — starts a fresh process with a model name that does not exist
- *Function:* `worker_bad_model`  *File:* `check_unit9.py` — runs inside that process and sends one valid text
- *Function:* `Run.add_failure`  *File:* `telemetry.py` — creates each failure record (called from `stage` for exceptions, and from `Run.finish` for refusals and 429s)
- *Function:* `_load`  *File:* `detector.py` — raises `DetectorUnavailable`, the real error behind the model-load failure

The batch's failure file held exactly 4 lines, two `429` and two `400`. The model-load run produced exactly 1 line (the `message` is cut at 300 characters by `add_failure`), followed by what the worker reported about the response. The last block is what `u9_2` reported.

```json
{"schema_version": 1, "record_type": "failure", "run_id": "75a6ec1bc6bd47edb54a28beb4abbe49", "timestamp": "2026-11-13T05:09:46.595+00:00", "route": "/submit", "stage": "request", "category": "rate_limit", "error_type": null, "message": "rate_limited", "http_status": 429, "context": {}}
{"schema_version": 1, "record_type": "failure", "run_id": "669b97c28ba941cfb0aa06dc958ce901", "timestamp": "2026-11-13T05:09:46.597+00:00", "route": "/submit", "stage": "request", "category": "rate_limit", "error_type": null, "message": "rate_limited", "http_status": 429, "context": {}}
{"schema_version": 1, "record_type": "failure", "run_id": "e515e37a5768450481a9a257053fdd47", "timestamp": "2026-11-13T05:09:46.597+00:00", "route": "/submit", "stage": "validate", "category": "validation_failure", "error_type": null, "message": "invalid_text", "http_status": 400, "context": {}}
{"schema_version": 1, "record_type": "failure", "run_id": "8804f28117e24046b1e2655531f54510", "timestamp": "2026-11-13T05:09:46.598+00:00", "route": "/submit", "stage": "validate", "category": "validation_failure", "error_type": null, "message": "invalid_text", "http_status": 400, "context": {}}
```

```json
{"schema_version": 1, "record_type": "failure", "run_id": "f4ceb66acb644b6da40e2b4560fd2f43", "timestamp": "2026-11-13T05:09:47.794+00:00", "route": "/submit", "stage": "model_signal", "category": "model_unavailable", "error_type": "DetectorUnavailable", "message": "Couldn't load 'not-a-real-model-xyz': We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files.\nCheck your internet connection or see how to run the library in offline mode at 'https://huggingface.co/docs/transformers/installation#offline-mode'.\nT", "http_status": 500, "context": {}}
{"status": 500, "records": 1, "stage": "model_signal", "category": "model_unavailable", "error_type": "DetectorUnavailable", "run_id_matches": true, "message": true, "model": "not-a-real-model-xyz"}
```

```json
{"trial": 1, "pass": true, "detail": {"matched": "5/5", "extra records": 0, "model-load failure": "500 / model_signal / model_unavailable", "batch": "limited:429:ok limited:429:ok refused:400:ok refused:400:ok"}}
```

#### **U9-3: Timing — MET**

- *Function:* `u9_3`  *File:* `check_unit9.py` — sends 20 warm requests and compares a client stopwatch with the recorded time
- *Function:* `stage`  *File:* `telemetry.py` — times each stage and works out the overhead
- *Function:* `perplexity`  *File:* `detector.py` — times the model call itself and reports it through `telemetry.py::record_inference`

Two of the 20 timed run records are shown. Compare `duration_ms` with the stage durations, and `inference_ms` plus `overhead_ms` with the `model_signal` stage. The last block is what `u9_3` reported, including the gap between the client stopwatch and `duration_ms` over all 20 requests (the script keeps that summary, not each request's client time).

```json
{"schema_version": 1, "record_type": "run", "run_id": "1dfb079353fb431b89c36f624aed7108", "started_at": "2026-11-13T05:09:48.036+00:00", "route": "/submit", "method": "POST", "http_status": 200, "outcome": "ok", "duration_ms": 61.456, "input": {"chars": 815, "words": 139, "sha256_16": "6171cfca8d19792b"}, "stages": [{"name": "model_signal", "status": "ok", "duration_ms": 60.496, "inference_ms": 59.986, "overhead_ms": 0.51}, {"name": "style_signal", "status": "ok", "duration_ms": 0.169}, {"name": "combine", "status": "ok", "duration_ms": 0.003}, {"name": "label", "status": "ok", "duration_ms": 0.001}, {"name": "audit_write", "status": "ok", "duration_ms": 0.269}], "inference": [{"model": "gpt2", "input_tokens": 173, "tokenize_ms": 0.458, "forward_ms": 59.986, "load_ms": 0.0, "cold_start": false}], "usage": {"model": "gpt2", "input_tokens": 173, "output_tokens": 0, "source": "local"}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": "gpt2", "compute_seconds": {"wall": 0.061456, "inference": 0.059986, "cpu": 0.105823}}, "failure_categories": [], "context": {"content_id": "41366487-a248-4210-b40d-02a6cbbd3cfd", "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you."}}
{"schema_version": 1, "record_type": "run", "run_id": "85379cbc2fad495498018808a604504f", "started_at": "2026-11-13T05:09:48.099+00:00", "route": "/submit", "method": "POST", "http_status": 200, "outcome": "ok", "duration_ms": 33.431, "input": {"chars": 436, "words": 67, "sha256_16": "eb3d58ad5172a284"}, "stages": [{"name": "model_signal", "status": "ok", "duration_ms": 32.879, "inference_ms": 32.648, "overhead_ms": 0.231}, {"name": "style_signal", "status": "ok", "duration_ms": 0.093}, {"name": "combine", "status": "ok", "duration_ms": 0.001}, {"name": "label", "status": "ok", "duration_ms": 0.001}, {"name": "audit_write", "status": "ok", "duration_ms": 0.184}], "inference": [{"model": "gpt2", "input_tokens": 74, "tokenize_ms": 0.196, "forward_ms": 32.648, "load_ms": 0.0, "cold_start": false}], "usage": {"model": "gpt2", "input_tokens": 74, "output_tokens": 0, "source": "local"}, "cost": {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0, "priced_model": "gpt2", "compute_seconds": {"wall": 0.033431, "inference": 0.032648, "cpu": 0.050494}}, "failure_categories": [], "context": {"content_id": "49031d5d-56a7-4bad-b74e-c0a464c748eb", "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you."}}
```

```json
{"trial": 1, "pass": true, "detail": {"within 15 ms": "20/20", "stages >= 98%": "20/20", "gap ms (min/mean/max)": "0.97 / 1.19 / 2.27", "min stage coverage": "0.9891", "model share of model_signal stage (min)": "0.991"}}
```

#### **U9-4: Metrics against a recount — MET**

- *Function:* `u9_4`  *File:* `check_unit9.py` — sends the 21-request batch, calls `/metrics`, and recounts the raw files in plain Python
- *Function:* `get_metrics`  *File:* `app.py` — serves `GET /metrics`
- *Function:* `compute`  *File:* `metrics.py` — does the aggregation

The script compared the two in memory and did not save the `/metrics` response, so the first block is `metrics.py::compute()` run afterwards on that trial's own `runs.jsonl` and `failures.jsonl` (21 and 5 lines). The second block is what `u9_4` reported.

```json
{
 "requests": {
  "total": 21,
  "by_outcome": {
   "ok": 16,
   "rate_limited": 2,
   "client_error": 3
  },
  "error_rate": 0.0,
  "rejected_rate": 0.2381
 },
 "failures": {
  "total": 5,
  "by_category": {
   "rate_limit": 2,
   "validation_failure": 3
  },
  "by_stage": {
   "request": 2,
   "validate": 3
  }
 },
 "cost.input_tokens": 1335,
 "link.rate_limit_hits": 2,
 "link.status_codes": {
  "200": 16,
  "400": 3,
  "429": 2
 },
 "latency_ms.request": {
  "count": 21,
  "mean": 26.053,
  "p50": 31.695,
  "p95": 53.413,
  "p99": 55.287,
  "max": 55.756
 }
}
```

```json
{"trial": 1, "pass": true, "detail": {"matched": "6/6", "total requests": "reported 21 | recount 21", "by outcome": "reported {'client_error': 3, 'ok': 16, 'rate_limited': 2} | recount {'ok': 16, 'rate_limited': 2, 'client_error': 3}", "rate-limit hits": "reported 2 | recount 2", "total failures": "reported 5 | recount 5", "input tokens": "reported 1335 | recount 1335", "request p50 ms": "reported 31.695 | recount 31.695"}}
```

#### **U9-5: Telemetry never in the way — MET**

- *Function:* `u9_5`  *File:* `check_unit9.py` — runs both parts of the check
- *Function:* `_append`  *File:* `audit.py` — adds a `run_id` to an audit entry only when a run is active
- *Function:* `current_run_id`  *File:* `telemetry.py` — tells `_append` whether a run is active
- *Function:* `write_record`  *File:* `telemetry.py` — swallows the write error when the telemetry files are unwritable

Part (a): the first two texts, each submitted with telemetry on (`creator_id` ending `-True`) and then off (`-False`). The scores, guess and label are identical, and only the telemetry-on entries carry a `run_id`. The file held 20 entries; 4 are shown. Part (b): the folder listing shows the two telemetry files replaced by directories, so every telemetry write fails, yet the audit file still has all 11 entries; the first (a valid submit) and the last (the blank-text refusal) are shown. The last block is what `u9_5` reported.

```json
{"timestamp": "2026-11-13T05:09:49+00:00", "content_id": "1ea390bb-2549-46a4-8712-25cb136657ef", "creator_id": "t1u5-0-True", "guess": "unsure", "model_score": 0.4578, "style_score": 0.6731, "combined_score": 0.6085, "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.", "status": "decided", "run_id": "c6c3c277f974438f93a6aabc02d076a5"}
{"timestamp": "2026-11-13T05:09:49+00:00", "content_id": "a092f79a-0b1b-4371-b58c-935116e3dec1", "creator_id": "t1u5-0-False", "guess": "unsure", "model_score": 0.4578, "style_score": 0.6731, "combined_score": 0.6085, "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.", "status": "decided"}
{"timestamp": "2026-11-13T05:09:49+00:00", "content_id": "ea350642-b86e-4509-a0fd-52aecc1b2474", "creator_id": "t1u5-1-True", "guess": "unsure", "model_score": 0.338, "style_score": 0.6666, "combined_score": 0.568, "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.", "status": "decided", "run_id": "bc31ef5ba29e40af95d6b50fcc7d939f"}
{"timestamp": "2026-11-13T05:09:49+00:00", "content_id": "941fb309-0522-4446-9685-a313e90c27c2", "creator_id": "t1u5-1-False", "guess": "unsure", "model_score": 0.338, "style_score": 0.6666, "combined_score": 0.568, "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.", "status": "decided"}
```

```
['audit.jsonl', 'failures_is_a_dir', 'runs_is_a_dir']
```

```json
{"timestamp": "2026-11-13T05:09:50+00:00", "content_id": "e05d6b7a-8a50-4b6e-bd4e-717a71c34830", "creator_id": "t1u5b-0", "guess": "unsure", "model_score": 0.4578, "style_score": 0.6731, "combined_score": 0.6085, "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.", "status": "decided", "run_id": "7b8c3110d11b4ad2ac4b939a4cd129cd"}
{"timestamp": "2026-11-13T05:09:50+00:00", "creator_id": "t1u5b-blank", "event": "rejected", "status": "rejected", "reason": "invalid_text", "run_id": "4701ea385fb74c6da7fa89f5a60699f3"}
```

```json
{"trial": 1, "pass": true, "detail": {"same answers on/off": "10/10", "correct with telemetry files unwritable": "11/11"}}
```

### Verdicts: MET or MISSED (original run, U9-3 at 15 ms)

Each verdict is against the target written in `criteria.md`, and a criterion counts as MET only if all 3 trials of the recorded run held it (`results/unit9_criteria_2026-11-12_2309.md`).

| Criterion | Target | Trial 1 | Trial 2 | Trial 3 | Verdict |
|---|---|---|---|---|---|
| U9-1 Traceability | 20/20 headers, 20/20 run records, 15/15 audit entries | 20, 20, 15 | 20, 20, 15 | 20, 20, 15 | **MET** |
| U9-2 Failure records | 5/5 exactly one correct record | 5/5 | 5/5 | 5/5 | **MET** |
| U9-3 Timing | 20/20 within 15 ms **and** 20/20 stage coverage ≥ 98% | 20/20, 20/20 | 20/20, 20/20 | 20/20, 20/20 | **MET** (see below) |
| U9-4 Metrics vs recount | 6/6 exact | 6/6 | 6/6 | 6/6 | **MET** |
| U9-5 Telemetry never in the way | 10/10 same answers and 11/11 correct with telemetry unwritable | 10/10, 11/11 | 10/10, 11/11 | 10/10, 11/11 | **MET** |

**Misses: none, so there is no failure to diagnose and no pattern across misses to name.**

**One MET I don't fully trust: U9-3's 98% stage coverage.** After the recorded run I re-ran the same procedure to see how much room the targets had (`results/unit9_u9-3_margin_check_2026-11-13.md`). In 60 new requests, one fell to 97.98% coverage, which would have been a miss. A further 120 requests had none below 98.5%. So about 1 request in 240 crossed the line, and with 60 requests per run that gives roughly a 1-in-5 chance that a re-run of the full 3 trials misses U9-3. The mechanism is fixed time outside the timed stages: about 0.25 ms per request (the median over 120 requests, range 0.22 to 0.39 ms). I measured that figure but not its breakdown; from reading `app.py::submit` the work outside every `telemetry.stage` is reading the JSON body, building the response and the Flask and rate-limiter hooks, so that is my inference, not something I timed. On a 28 ms request that is about 1%, and about 0.3 ms of extra jitter crosses 2%. The stage is not one of the pipeline stages but the request handling around them. The recorded run met the target and I am not changing the verdict, but the 98% target had under one point of margin, so I'd call it passing by luck, not by design.

**Were my targets set low? Yes, in two ways.**

1. **I set them after looking.** I measured the system first (gap 1.0 to 5.1 ms, coverage 99.5%+, telemetry on and off identical) and then chose targets with headroom, so the system could hardly miss them. They are real checks (tightening U9-3 made it fail 0 of 20, which shows the script can report a miss), but they were never going to teach me much by passing.
2. **The 100% criteria are rules, not tests of a margin.** U9-1, U9-2, U9-4 and U9-5 are already at the maximum, so they can't be tightened. What they lack is breadth. U9-2 exercises only 3 of the 8 failure categories (`validation_failure`, `rate_limit`, `model_unavailable`). `timeout`, `bad_response`, `connection_error`, `upstream_unavailable` and `internal_error` have no live example, and `link_client.py` (retries and timeouts) is not covered by any criterion.

**The criterion I'd tighten: U9-3's gap target, from 15 ms to 5 ms.** The largest gap I measured was 2.27 ms in the recorded run and 2.02 ms in the re-run, so 15 ms is about 7 times the real maximum and would let a missing stage of several milliseconds through. At 5 ms the same 60 requests still pass 60/60 (59/60 at 2 ms), so 5 ms is tight enough to catch a real fault without failing on noise; my first probe saw a single 5.1 ms outlier, so it could still fail occasionally, and that is the point of tightening. For the coverage half of U9-3 the fix is the other way round: the target is already at the edge, so rather than loosen it I'd put the request handling around the stages inside a timed stage, so the untimed 0.25 ms is measured, and then raise the target to 99%.

**What I'd add:** a criterion for the one thing no run shows yet: a client request that exceeds its timeout leaves a `client_link.jsonl` record with outcome `timeout` and, with `retries=2`, exactly 3 attempt records, in 5 of 5 trials.

### U9-3 revised: gap limit tightened from 15 ms to 5 ms

**What changed.** In `check_unit9.py` the constant `GAP_LIMIT_MS` went from `15.0` to `5.0` (a `--gap-limit` flag keeps the old value reproducible: `python check_unit9.py --gap-limit 15`). Nothing else changed: not the other four criteria, not the 98% stage-coverage half of U9-3, and not the service. The text of U9-3 in `criteria.md` is **unchanged** and still says 15 ms; this section is the documentation of the revision.

**U9-3, revised.** Over 20 warm `/submit` requests sent over real HTTP in each of 3 trials, the recorded `duration_ms` is within **5 ms** of the client-measured time for every request, and the stage durations add up to at least 98% of `duration_ms` for every request. Target: 20 of 20 on both, in each trial.

**Why revised.** This was not a miss. U9-3 passed at 15 ms with a worst gap of 2.27 ms, which means the limit was about 7 times the largest gap the system produces, so it could not catch a timing fault of any size below 15 ms. Tightening a target the system already met is allowed; loosening one it missed is not.

**Why 5 ms and not stricter or looser.** The system's own gap ran 0.90 to 2.27 ms over 120 requests (the recorded run and this re-run). A typical request takes 28 to 33 ms, so 5 ms is about 15% of the time a writer waits: an unaccounted gap bigger than that means the timing record is missing about a sixth of the request. Looser fails that job: 15 ms let an 8 ms untimed delay through, with 0 of 20 caught. Stricter fails on noise: at 2 ms the earlier margin check passed only 59 of 60 requests with nothing wrong, and 3 ms leaves almost no headroom over the largest normal gap.

**Verdict: MET**, in all 3 trials (20/20 within 5 ms and 20/20 stage coverage ≥ 98% each time), with the numbers below.

#### Updated criteria table (all five, U9-3 revised)

Targets are the ones in `criteria.md`, except U9-3, which uses the revised 5 ms gap. Results are from the re-run of 2026-11-13 13:23 (`results/unit9_criteria_2026-11-13_1323.md`), 3 trials. A criterion is MET only if all 3 trials hold it.

| Criterion | Target | Why this target | Trial 1 | Trial 2 | Trial 3 | Verdict |
|---|---|---|---|---|---|---|
| **U9-1** Every request can be traced from response to log | 20 of 20 responses carry an `X-Request-ID`; the 20 ids appear exactly once in `runs.jsonl`; 15 of 15 audit entries carry the same `run_id` | The `run_id` is the join key between three files, so it is a rule, not a probability; one untraceable request is the one I'd be searching for | PASS | PASS | PASS | **MET** |
| **U9-2** Every refused or failed request leaves exactly one correct failure record | 5 of 5 deliberate failures (2 bad inputs, 2 rate-limited, 1 model-load failure) leave exactly one record with the right stage and category, and no extras | A failure that shows up only as an absence is never found, and the category matters because `metrics.py` counts only 5xx as errors | PASS | PASS | PASS | **MET** |
| **U9-3 (revised)** Recorded timings agree with an independent clock | 20 of 20 warm requests with recorded `duration_ms` within **5 ms** of the client stopwatch (was 15 ms) **and** stage durations adding up to at least 98% of `duration_ms` | Measured gap is 0.90 to 2.27 ms and a typical request is 28 to 33 ms; 5 ms catches an 8 ms untimed delay that 15 ms missed (0 of 20 vs 20 of 20), and 2 ms fails on noise | PASS | PASS | PASS | **MET** (coverage margin thin) |
| **U9-4** `/metrics` reproduces a recount of the raw logs | 6 of 6 figures exact (total, outcomes, rate-limit hits, failures, input tokens, p50) | `metrics.py` stores nothing and recomputes from the files, so any difference is a bug; a tolerance would hide rare events like 2 rate-limit hits | PASS | PASS | PASS | **MET** |
| **U9-5** Telemetry never changes or blocks a response | 10 of 10 same answers with telemetry on and off, and 11 of 11 correct with the telemetry files unwritable | A writer's verdict must not depend on a measurement tool, and a full disk must not turn a submission into a 500 | PASS | PASS | PASS | **MET** |

**Miss count: 0 of 5.** The one caveat is U9-3's coverage half: it passed in all 3 trials (lowest 98.92%) but with under one point of margin, and an earlier margin check saw one request in 240 fall below 98%, so a future re-run could miss it.

#### Before and after, side by side

Same procedure, same machine, same 5 criteria, 3 trials each. **Before:** gap limit 15 ms, run of 2026-11-12 23:09 (`results/unit9_criteria_2026-11-12_2309.md`). **After:** gap limit 5 ms, run of 2026-11-13 13:23 (`results/unit9_criteria_2026-11-13_1323.md`).

| Criterion | Before (15 ms): T1 / T2 / T3 | After (5 ms): T1 / T2 / T3 | Verdict before | Verdict after |
|---|---|---|---|---|
| U9-1 traceability | PASS / PASS / PASS | PASS / PASS / PASS | MET | MET |
| U9-2 failure records | PASS / PASS / PASS | PASS / PASS / PASS | MET | MET |
| **U9-3 timing** | PASS / PASS / PASS (limit 15 ms) | PASS / PASS / PASS (limit 5 ms) | MET | MET |
| U9-4 metrics vs recount | PASS / PASS / PASS | PASS / PASS / PASS | MET | MET |
| U9-5 telemetry never in the way | PASS / PASS / PASS | PASS / PASS / PASS | MET | MET |

The numbers behind U9-3:

| | Before T1 | Before T2 | Before T3 | After T1 | After T2 | After T3 |
|---|---|---|---|---|---|---|
| Requests within the gap limit | 20/20 | 20/20 | 20/20 | 20/20 | 20/20 | 20/20 |
| Gap ms (min / mean / max) | 0.97 / 1.19 / 2.27 | 1.11 / 1.28 / 1.94 | 0.96 / 1.12 / 2.12 | 1.01 / 1.14 / 2.24 | 0.95 / 1.08 / 1.90 | 0.90 / 1.06 / 2.03 |
| Largest gap as a share of the limit | 15% | 13% | 14% | 45% | 38% | 41% |
| Requests with stage coverage ≥ 98% | 20/20 | 20/20 | 20/20 | 20/20 | 20/20 | 20/20 |
| Lowest stage coverage | 98.91% | 98.74% | 99.06% | 98.92% | 99.02% | 99.12% |

Request latency over the 60 timed requests (ms): before mean 36.3, p50 33.1, p95 57.2, p99 66.3, max 73.2; after mean 33.5, p50 32.0, p95 37.4, p99 69.0, max 73.8.

#### Numbers for all five criteria, before and after

The counts behind every PASS in both result sets, taken from `results/unit9_criteria_2026-11-12_2309.json` (before, gap limit 15 ms) and `results/unit9_criteria_2026-11-13_1323.json` (after, gap limit 5 ms). U9-1, U9-2 and U9-5 are identical because the service and those checks did not change; U9-4's p50 differs between runs because latency does.

| Criterion | Before T1 | Before T2 | Before T3 | After T1 | After T2 | After T3 |
|---|---|---|---|---|---|---|
| **U9-1** headers / run records / audit joined | 20/20 / 20/20 / 15/15 | 20/20 / 20/20 / 15/15 | 20/20 / 20/20 / 15/15 | 20/20 / 20/20 / 15/15 | 20/20 / 20/20 / 15/15 | 20/20 / 20/20 / 15/15 |
| **U9-2** records matched / extra records | 5/5 / 0 | 5/5 / 0 | 5/5 / 0 | 5/5 / 0 | 5/5 / 0 | 5/5 / 0 |
| **U9-3** gap and coverage (limit 15 ms before, 5 ms after) | 20/20 within limit; coverage 20/20 (min 98.91%); gap max 2.27 ms | 20/20 within limit; coverage 20/20 (min 98.74%); gap max 1.94 ms | 20/20 within limit; coverage 20/20 (min 99.06%); gap max 2.12 ms | 20/20 within limit; coverage 20/20 (min 98.92%); gap max 2.24 ms | 20/20 within limit; coverage 20/20 (min 99.02%); gap max 1.90 ms | 20/20 within limit; coverage 20/20 (min 99.12%); gap max 2.03 ms |
| **U9-4** figures matching / tokens / p50 | 6/6; tokens 1335; p50 31.695 ms | 6/6; tokens 1335; p50 33.71 ms | 6/6; tokens 1335; p50 32.345 ms | 6/6; tokens 1335; p50 31.574 ms | 6/6; tokens 1335; p50 31.718 ms | 6/6; tokens 1335; p50 31.64 ms |
| **U9-5** same answers / correct when unwritable | 10/10 / 11/11 | 10/10 / 11/11 | 10/10 / 11/11 | 10/10 / 11/11 | 10/10 / 11/11 | 10/10 / 11/11 |

#### Does the tighter limit catch anything the old one missed?

I injected an untimed delay ahead of the telemetry hook (so the client sees it and the recorded duration does not) and scored both limits on 20 requests each (`results/unit9_u9-3_gap_sensitivity_2026-11-13.md`):

| Untimed delay injected | Gap seen (mean) | Caught by 15 ms | Caught by 5 ms |
|---|---|---|---|
| 0 ms (normal) | 1.12 ms | 0/20 | 0/20 |
| 3 ms | 4.75 ms | 0/20 | 0/20 |
| 8 ms | 11.01 ms | 0/20 | **20/20** |
| 12 ms | 15.85 ms | 18/20 | 20/20 |
| 20 ms | 25.34 ms | 20/20 | 20/20 |

#### Did it help?

**As a test, yes. As an improvement to the system, no, and it came with a cost.**

- **What got better:** U9-3 can now catch an untimed delay of about 5 ms or more. An 8 ms delay, about a quarter of a typical request, was invisible to the old limit (0 of 20 caught) and caught every time by the new one (20 of 20). A criterion that could not have failed for a fault that size now can.
- **What did not change:** every result. All five criteria were MET before and after, and the gaps are the same within noise (largest 2.27 ms before, 2.24 ms after), as they should be because the service did not change. Tightening the target did not make the system better and did not find a bug.
- **The trade: headroom fell from about 7 times to about 2 times.** The largest gap went from 15% of the limit to 45% of it. That makes U9-3 more likely to fail for no reason. Across every U9-3-style request I have measured (the first probe, the recorded run, the margin check and this re-run, about 200 in all), one had a gap over 5 ms: 5.12 ms, in the very first probe. At that rate a full 60-request run has very roughly a one in four chance of a false miss from the gap alone. That is a small sample, so treat it as a rough size and not a number to quote.
- **What did not get better:** the 98% stage-coverage half of U9-3, which I flagged as passing by luck, is untouched. It passed here (lowest 98.92%) but with the same under-one-point margin, so it can still fail a re-run. Between the two halves, U9-3 is now the most fragile of the five criteria.
- **A blind spot remains:** a 3 ms untimed delay produced a mean gap of 4.75 ms and was caught by neither limit. The 5 ms limit does not see faults smaller than about 4 ms.

**Net:** a better criterion measuring the same system, with a higher chance of failing on noise. If I wanted to keep tightening, the next step is not a smaller number. It is putting the 0.25 ms of untimed request handling inside a timed stage, so the coverage half has real margin, before touching the gap again.

## What's Still Broken: Unit 9

**Criteria still missed: none.** All five unit-9 criteria (U9-1 to U9-5) were MET in all 3 trials, in the original run and again after tightening U9-3's gap to 5 ms. So there is no miss to diagnose, and I'm not going to pretend one into existence. What follows is what is still open in the extension, what I'd do about each item, and why I stopped. The classifier problems from unit 8 (15 of 56 attacks still getting through, the missing "human" label) are in the earlier "What's Still Broken" and are unchanged: unit 9 did not fix them or make them worse, and U9-5 shows the answers are identical with telemetry on and off.

### The target that was set too low

**U9-3's 98% stage-coverage target, which I'd tighten to 99%.** Today the system does not reliably meet 99%: in the margin check (`results/unit9_u9-3_margin_check_2026-11-13.md`) 56 of 60 requests reached 99% and only 1 of 60 reached 99.5%, and one request in 240 fell below the current 98%. So 98% sits just under what the system actually does, which is why it passed in the recorded run with under a point to spare, and why a re-run could miss it. Raising it to 99% would fail right now. It only becomes a sensible target after the system fix in the first row below, and then I'd expect to hold 99% comfortably (that is a prediction; I haven't measured it).

Two other things I'd say plainly about how low the targets were:

- **I set all five after measuring the system**, with headroom, so none of them was likely to be missed. Tightening U9-3 from 15 ms to 5 ms is the one place that was corrected, and it did expose something the old limit hid (an 8 ms untimed delay: 0 of 20 caught at 15 ms, 20 of 20 at 5 ms).
- **U9-1, U9-2, U9-4 and U9-5 are already at 100% or exact, so they can't be tightened.** What they lack is breadth, which is the third row below.

### What is still open

| What's open | Mechanism | What I'd do | Why I stopped |
|---|---|---|---|
| **U9-3 coverage margin is thin** (lowest 97.98% seen once; 98.92% in the re-run) | About 0.25 ms per request (median over 120, range 0.22 to 0.39 ms) happens outside every `telemetry.stage`: reading the JSON body, building the response and the Flask hooks. That is inferred from `app.py::submit`; I measured the 0.25 ms but not its parts. On a 28 ms request it is about 1%, and about 0.3 ms of jitter crosses 2% | Put the parsing and response-building inside timed stages (for example `parse` and `respond`), then raise the target to 99% | The revision I was asked to make was the gap limit only. Adding stages changes the record schema and the stage list that U9-1 and U9-3 check, so I left it for a deliberate change |
| **Gap blind spot below about 4 ms** | A 3 ms untimed delay gave a mean gap of 4.75 ms, just under the 5 ms limit, and neither limit caught it | Nothing cheap. Seeing smaller gaps would need a second clock on every request | A tighter limit fails on noise: at 2 ms the margin check passed only 59 of 60 requests with nothing wrong, so 5 ms is already near the floor |
| **U9-2 only exercises 3 of 8 failure categories** | The batch produces `validation_failure`, `rate_limit` and `model_unavailable`. `timeout`, `bad_response`, `connection_error`, `upstream_unavailable` and `internal_error` have never been produced on a live request, and `link_client.py` (retries, timeouts) is only covered by unit tests with a faked `requests`, not by any criterion | Add the criterion proposed earlier: a client request that exceeds its timeout leaves a `client_link.jsonl` record with outcome `timeout`, and with `retries=2` leaves exactly 3 attempt records, in 5 of 5 trials | I wrote the five criteria before this gap was obvious and didn't add a sixth. I didn't run out of time; it is simply not done |
| **A wrong-method request is filed as `validation_failure`** | `telemetry.py::classify` maps any 4xx it has no better rule for to `validation_failure`, so a `405` (a wrong method, not bad input) shares a category with a blank-text `400`. It is recorded at stage `request` | Add a separate `client_error` category for 404 and 405 | It doesn't affect `metrics.py`, which counts only 5xx as errors, so I treated it as cosmetic. It does blur the failure counts |
| **First request after every start is slow** (2.3 to 4.3 s) | The model loads on first use, not at startup (`/health` shows `detector_loaded: false` until then). The cost measurement excludes it, so the 0.031 s per run hides that someone waits several seconds | Call `detector.warm_up()` when the service starts | It would change startup behaviour and I was told to leave the system as it is. It is also a cost: the first writer after each restart pays it |
| **Token pricing is never exercised** | The dollar figure is 0.00 because the model is local. The compute-rate half is tested (`test_telemetry.py` checks 0.5 s at $36 an hour gives $0.005); the per-token `PRICING` rates are not tested at all, because every shipped rate is 0.0 and no hosted model has ever been priced | Add a test with a made-up per-token price and check `compute_cost` against a hand calculation | There is no hosted model to price, so it would be a test of arithmetic, not of the system. It is a small test I simply haven't written |
| **Logs and metrics don't scale** | The telemetry files are append-only and never rotated, and `metrics.compute` reads and parses all three files on every `/metrics` call, so its cost grows with the file | Rotate by day and read only the requested window | Nothing here is big (the log is a few hundred lines) and I haven't measured it at scale, so I don't know where it starts to hurt |

### The pattern

Three of these are one problem. The coverage margin, the sub-4 ms blind spot and the miscategorised `405` all live in the stage `request`: the catch-all I use for everything that happens outside the pipeline stages (the 429s, the 405, and the untimed 0.25 ms). The pipeline stages (`model_signal`, `style_signal`, `combine`, `label`, `audit_write`) are timed and categorised well; the edges around them are not. That is one weakness of the instrumentation with three symptoms, and the first row's fix (timing the parsing and the response) would remove two of the three.

### If I had another unit

I would time the request parsing and response building in their own stages (`parse` and `respond`), re-run the three trials, and then raise U9-3's coverage target from 98% to 99%. I'd do that first because it is the only open item where a number I already rely on can fail for no good reason (U9-3 has roughly a one-in-five chance of a false miss on a re-run), and it removes two of the three symptoms that share the `request` stage, while every other item adds coverage rather than repairing a measurement I'm already using.
