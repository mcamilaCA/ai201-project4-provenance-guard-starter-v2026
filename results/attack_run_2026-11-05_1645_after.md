# Attack run — after

- Produced by: `run_attacks.py::main`
- Service: `app.py::submit`
- 56 attacks · 2026-11-05 16:45
- Auto-marked BROKE (5xx, crash, no response): **0**
- Left for you to judge: **56**

The Verdict column is blank where a script can't honestly decide. Whether
an evasion worked depends on where you put your thresholds — read the
`targets` column, look at what came back, and write HELD or BROKE yourself.

Each attack submits as creator_id `attacker_<id>`, and the content_id it
came back with is in the table — either one will match this run against your
audit log when you go looking for the ten entries to paste.

| ID | Family | Targeting | Status | Content ID | Guess | Score | Verdict |
|---|---|---|---|---|---|---|---|
| EV01 | evasion | signal two: typos raise word variety | 200 | `2c12aaa2-2def-4117-8331-59ff087b1c78` | unsure | 0.009 |  |
| EV02 | evasion | signal two: broken-up sentences raise length spread | 200 | `eccc46cc-b8f8-40ec-a5a1-3b58f4aa5d7a` | unsure | 0.077 |  |
| EV03 | evasion | signal two: a pasted quotation changes the shape | 200 | `4247f2c3-ed0d-43b8-8384-e91b6b41192a` | unsure | 0.216 |  |
| EV04 | evasion | signal one: unusual words raise perplexity | 200 | `6bfacab0-a902-4a69-878d-b8860d1e8067` | unsure | 0.273 |  |
| EV05 | evasion | both signals: heavy human editing pass | 200 | `a33c0ffe-b238-4545-8363-ce4450340f9c` | unsure | 0.033 |  |
| EV06 | evasion | signal two: one very long sentence and one very short | 200 | `bf56b678-d568-45a7-a084-e129b3321beb` | unsure | 0.006 |  |
| EV07 | evasion | signal two: padding with punctuation | 200 | `3d3d766a-f398-40e0-a50e-8bef18653231` | unsure | 0.120 |  |
| EV08 | evasion | signal one: text below the token window | 200 | `221db60f-c77d-4b70-827f-39354ce87ddb` | unsure | 0.000 |  |
| EV09 | evasion | both: AI text with a human opening paragraph bolted on | 200 | `6160358a-2b31-4d02-93d7-be3f59f22ac5` | unsure | 0.212 |  |
| EV10 | evasion | signal two: repeated stanza structure | 200 | `d3772c8d-1bb4-41cd-a111-3a46ad6a9743` | ai | 0.785 |  |
| FP01 | false_positive | plain, clear human writing with no flourishes | 200 | `4bf17de7-417d-4a4d-9415-d3f1a1e206fa` | unsure | 0.283 |  |
| FP02 | false_positive | human writing in a formal register | 200 | `698e5e4c-903f-4dba-a2bf-b41c757be69f` | ai | 0.425 |  |
| FP03 | false_positive | a non-native English speaker writing carefully | 200 | `b065a5c4-a3b4-4b42-8604-50f27d11ad26` | ai | 0.444 |  |
| FP04 | false_positive | a student essay written to a rubric | 200 | `4af449d3-f4a5-49bd-a75b-6ca8a75ee538` | ai | 0.394 |  |
| FP05 | false_positive | technical documentation written by a person | 200 | `49ee5dc2-ece8-41bc-8cc2-db5cbc06457d` | ai | 0.494 |  |
| FP06 | false_positive | a person imitating a formal template | 200 | `ea324d6a-a731-40c0-a4d9-1b4262d873ff` | ai | 0.410 |  |
| FP07 | false_positive | human writing that repeats a phrase deliberately | 200 | `e7a24f8f-6bff-4367-a2f4-5a7c73dd1dc6` | ai | 0.456 |  |
| FP08 | false_positive | very short genuine human submission | 200 | `2baf714c-d0c1-45db-8e5a-410f2591c04b` | unsure | 0.000 |  |
| PI01 | prompt_injection | instruction to ignore the check | 200 | `5a9daa74-b096-4d90-b42d-f42750427a98` | unsure | 0.036 |  |
| PI02 | prompt_injection | instruction disguised as a system message | 200 | `0208aad4-c474-46b1-8b66-3640812cf134` | unsure | 0.196 |  |
| PI03 | prompt_injection | instruction wrapped in the writer's voice | 200 | `cbafb19d-9037-4a16-bc1a-342cf79a5ddf` | unsure | 0.084 |  |
| PI04 | prompt_injection | attempt to make the label text hostile | 200 | `803a311f-f108-4d31-bf1f-e297798bd39a` | unsure | 0.101 |  |
| PI05 | prompt_injection | attempt to inject into the audit log | 200 | `6238bb30-f2f4-4d08-878d-81cd257d5beb` | unsure | 0.000 |  |
| PI06 | prompt_injection | instruction plus real human text | 200 | `e79b3c4f-fe18-42a9-9eed-39b080c6eae1` | unsure | 0.224 |  |
| MF01 | malformed | text is only whitespace | 400 | `—` | — | — |  |
| MF02 | malformed | text is a single character | 200 | `43a68a44-2307-4910-a5f2-bc0f906a680b` | unsure | 0.000 |  |
| MF03 | malformed | text is control characters | 200 | `3a29f137-1913-4f9d-a859-65652b1eb55b` | unsure | 0.000 |  |
| MF04 | malformed | text is only punctuation | 200 | `2e7ef859-0940-4d99-b532-c7ff48eab440` | unsure | 0.000 |  |
| MF05 | malformed | text is a very long single word | 200 | `d468ae2f-92c3-42cb-9875-48329968cdca` | unsure | 0.000 |  |
| MF06 | malformed | text is emoji only | 200 | `d9dfff5c-2c69-4ed1-85cb-efacb9290ebb` | unsure | 0.000 |  |
| MF07 | malformed | text is right-to-left script | 200 | `27dee30e-df8d-4c23-9986-ac36e655e9ec` | unsure | 0.000 |  |
| MF08 | malformed | text is 60,000 characters | 200 | `9105f405-4979-49c4-81cc-4e4149fe5843` | ai | 0.515 |  |
| RQ01 | malformed | no text field at all | 400 | `—` | — | — |  |
| RQ02 | malformed | no creator_id | 200 | `9ea5f08e-7a1a-45e8-ad68-2ce58892b673` | unsure | 0.000 |  |
| RQ03 | malformed | text is a number | 400 | `—` | — | — |  |
| RQ04 | malformed | text is a list | 400 | `—` | — | — |  |
| RQ05 | malformed | text is null | 400 | `—` | — | — |  |
| RQ06 | malformed | creator_id is an object | 200 | `373aa568-52b6-40f9-88a9-f2b3484a8c0d` | unsure | 0.000 |  |
| RQ07 | malformed | body is a JSON array, not an object | 400 | `—` | — | — |  |
| RQ08 | malformed | body is unparseable JSON | 400 | `—` | — | — |  |
| RQ09 | malformed | body is empty | 400 | `—` | — | — |  |
| RQ10 | malformed | body is form-encoded, not JSON | 400 | `—` | — | — |  |
| RQ11 | malformed | body is JSON claiming to be plain text | 429 | `—` | — | — |  |
| RQ12 | malformed | deeply nested JSON | 400 | `—` | — | — |  |
| FL01_01 | flood_same_creator | 20 rapid submissions from one creator | 200 | `56ba4ecd-0a00-4cab-aeed-25d993e0e659` | unsure | 0.000 |  |
| FL01_02 | flood_same_creator | 20 rapid submissions from one creator | 200 | `b1caf544-ff9b-4c99-ae4f-d1624bc6475b` | unsure | 0.000 |  |
| FL01_03 | flood_same_creator | 20 rapid submissions from one creator | 200 | `0d6bb50d-e80e-4a76-99a8-ef74af5d5b7a` | unsure | 0.000 |  |
| FL01_04 | flood_same_creator | 20 rapid submissions from one creator | 200 | `0cdc7352-b92a-414c-b43c-c4d6001838fc` | unsure | 0.000 |  |
| FL01_05 | flood_same_creator | 20 rapid submissions from one creator | 200 | `6b1b6585-a7aa-42a3-ba01-15c8a714b6b0` | unsure | 0.000 |  |
| FL01_06 | flood_same_creator | 20 rapid submissions from one creator | 200 | `50727a07-6eae-48b5-a759-7fe125b995b7` | unsure | 0.000 |  |
| FL01_07 | flood_same_creator | 20 rapid submissions from one creator | 429 | `—` | — | — |  |
| FL01_08 | flood_same_creator | 20 rapid submissions from one creator | 429 | `—` | — | — |  |
| FL01_09 | flood_same_creator | 20 rapid submissions from one creator | 429 | `—` | — | — |  |
| FL01_10 | flood_same_creator | 20 rapid submissions from one creator | 429 | `—` | — | — |  |
| FL01_11 | flood_same_creator | 20 rapid submissions from one creator | 429 | `—` | — | — |  |
| FL01_12 | flood_same_creator | 20 rapid submissions from one creator | 429 | `—` | — | — |  |

---

## By family

| Family | Attacks | Auto-BROKE | Left to judge |
|---|---|---|---|
| `evasion` | 10 | 0 | 10 |
| `false_positive` | 8 | 0 | 8 |
| `flood_same_creator` | 12 | 0 | 12 |
| `malformed` | 20 | 0 | 20 |
| `prompt_injection` | 6 | 0 | 6 |

> The **false_positive** family is the one to look at hardest. Those are
> written to be genuine human writing that reads as machine-like. Every one
> your service calls AI is a real writer it would have accused.

---

## What came back

The detail behind the table. Paste the interesting failures into your
README — the ones that show something, not the ten easiest.

### EV01 — `evasion`

*Targeting:* signal two: typos raise word variety

```json
{
  "id": "EV01",
  "status": 200,
  "content_id": "2c12aaa2-2def-4117-8331-59ff087b1c78",
  "creator_id": "attacker_EV01",
  "guess": "unsure",
  "confidence": 0.009,
  "model_score": 0.1635,
  "style_score": 0.6506,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### EV02 — `evasion`

*Targeting:* signal two: broken-up sentences raise length spread

```json
{
  "id": "EV02",
  "status": 200,
  "content_id": "eccc46cc-b8f8-40ec-a5a1-3b58f4aa5d7a",
  "creator_id": "attacker_EV02",
  "guess": "unsure",
  "confidence": 0.077,
  "model_score": 0.5943,
  "style_score": 0.5146,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### EV03 — `evasion`

*Targeting:* signal two: a pasted quotation changes the shape

```json
{
  "id": "EV03",
  "status": 200,
  "content_id": "4247f2c3-ed0d-43b8-8384-e91b6b41192a",
  "creator_id": "attacker_EV03",
  "guess": "unsure",
  "confidence": 0.2164,
  "model_score": 0.6662,
  "style_score": 0.5834,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### EV04 — `evasion`

*Targeting:* signal one: unusual words raise perplexity

```json
{
  "id": "EV04",
  "status": 200,
  "content_id": "6bfacab0-a902-4a69-878d-b8860d1e8067",
  "creator_id": "attacker_EV04",
  "guess": "unsure",
  "confidence": 0.2732,
  "model_score": 0.6114,
  "style_score": 0.6474,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### EV05 — `evasion`

*Targeting:* both signals: heavy human editing pass

```json
{
  "id": "EV05",
  "status": 200,
  "content_id": "a33c0ffe-b238-4545-8363-ce4450340f9c",
  "creator_id": "attacker_EV05",
  "guess": "unsure",
  "confidence": 0.0328,
  "model_score": 0.3212,
  "style_score": 0.5532,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### EV06 — `evasion`

*Targeting:* signal two: one very long sentence and one very short

```json
{
  "id": "EV06",
  "status": 200,
  "content_id": "bf56b678-d568-45a7-a084-e129b3321beb",
  "creator_id": "attacker_EV06",
  "guess": "unsure",
  "confidence": 0.0058,
  "model_score": 0.5727,
  "style_score": 0.4647,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### EV07 — `evasion`

*Targeting:* signal two: padding with punctuation

```json
{
  "id": "EV07",
  "status": 200,
  "content_id": "3d3d766a-f398-40e0-a50e-8bef18653231",
  "creator_id": "attacker_EV07",
  "guess": "unsure",
  "confidence": 0.1204,
  "model_score": 0.6278,
  "style_score": 0.5313,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### EV08 — `evasion`

*Targeting:* signal one: text below the token window

```json
{
  "id": "EV08",
  "status": 200,
  "content_id": "221db60f-c77d-4b70-827f-39354ce87ddb",
  "creator_id": "attacker_EV08",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### EV09 — `evasion`

*Targeting:* both: AI text with a human opening paragraph bolted on

```json
{
  "id": "EV09",
  "status": 200,
  "content_id": "6160358a-2b31-4d02-93d7-be3f59f22ac5",
  "creator_id": "attacker_EV09",
  "guess": "unsure",
  "confidence": 0.2118,
  "model_score": 0.6834,
  "style_score": 0.5727,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### EV10 — `evasion`

*Targeting:* signal two: repeated stanza structure

```json
{
  "id": "EV10",
  "status": 200,
  "content_id": "d3772c8d-1bb4-41cd-a111-3a46ad6a9743",
  "creator_id": "attacker_EV10",
  "guess": "ai",
  "confidence": 0.7854,
  "model_score": 0.979,
  "style_score": 0.8557,
  "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
  "error": null,
  "verdict": ""
}
```

### FP01 — `false_positive`

*Targeting:* plain, clear human writing with no flourishes

```json
{
  "id": "FP01",
  "status": 200,
  "content_id": "4bf17de7-417d-4a4d-9415-d3f1a1e206fa",
  "creator_id": "attacker_FP01",
  "guess": "unsure",
  "confidence": 0.2834,
  "model_score": 0.6175,
  "style_score": 0.6521,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### FP02 — `false_positive`

*Targeting:* human writing in a formal register

```json
{
  "id": "FP02",
  "status": 200,
  "content_id": "698e5e4c-903f-4dba-a2bf-b41c757be69f",
  "creator_id": "attacker_FP02",
  "guess": "ai",
  "confidence": 0.4246,
  "model_score": 0.7387,
  "style_score": 0.701,
  "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
  "error": null,
  "verdict": ""
}
```

### FP03 — `false_positive`

*Targeting:* a non-native English speaker writing carefully

```json
{
  "id": "FP03",
  "status": 200,
  "content_id": "b065a5c4-a3b4-4b42-8604-50f27d11ad26",
  "creator_id": "attacker_FP03",
  "guess": "ai",
  "confidence": 0.4436,
  "model_score": 0.8051,
  "style_score": 0.6861,
  "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
  "error": null,
  "verdict": ""
}
```

### FP04 — `false_positive`

*Targeting:* a student essay written to a rubric

```json
{
  "id": "FP04",
  "status": 200,
  "content_id": "4af449d3-f4a5-49bd-a75b-6ca8a75ee538",
  "creator_id": "attacker_FP04",
  "guess": "ai",
  "confidence": 0.3944,
  "model_score": 0.8329,
  "style_score": 0.6391,
  "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
  "error": null,
  "verdict": ""
}
```

### FP05 — `false_positive`

*Targeting:* technical documentation written by a person

```json
{
  "id": "FP05",
  "status": 200,
  "content_id": "49ee5dc2-ece8-41bc-8cc2-db5cbc06457d",
  "creator_id": "attacker_FP05",
  "guess": "ai",
  "confidence": 0.4942,
  "model_score": 0.8005,
  "style_score": 0.7242,
  "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
  "error": null,
  "verdict": ""
}
```

### FP06 — `false_positive`

*Targeting:* a person imitating a formal template

```json
{
  "id": "FP06",
  "status": 200,
  "content_id": "ea324d6a-a731-40c0-a4d9-1b4262d873ff",
  "creator_id": "attacker_FP06",
  "guess": "ai",
  "confidence": 0.41,
  "model_score": 0.8814,
  "style_score": 0.6294,
  "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
  "error": null,
  "verdict": ""
}
```

### FP07 — `false_positive`

*Targeting:* human writing that repeats a phrase deliberately

```json
{
  "id": "FP07",
  "status": 200,
  "content_id": "e7a24f8f-6bff-4367-a2f4-5a7c73dd1dc6",
  "creator_id": "attacker_FP07",
  "guess": "ai",
  "confidence": 0.4564,
  "model_score": 0.8816,
  "style_score": 0.6624,
  "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
  "error": null,
  "verdict": ""
}
```

### FP08 — `false_positive`

*Targeting:* very short genuine human submission

```json
{
  "id": "FP08",
  "status": 200,
  "content_id": "2baf714c-d0c1-45db-8e5a-410f2591c04b",
  "creator_id": "attacker_FP08",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### PI01 — `prompt_injection`

*Targeting:* instruction to ignore the check

```json
{
  "id": "PI01",
  "status": 200,
  "content_id": "5a9daa74-b096-4d90-b42d-f42750427a98",
  "creator_id": "attacker_PI01",
  "guess": "unsure",
  "confidence": 0.0358,
  "model_score": 0.4625,
  "style_score": 0.5416,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### PI02 — `prompt_injection`

*Targeting:* instruction disguised as a system message

```json
{
  "id": "PI02",
  "status": 200,
  "content_id": "0208aad4-c474-46b1-8b66-3640812cf134",
  "creator_id": "attacker_PI02",
  "guess": "unsure",
  "confidence": 0.1956,
  "model_score": 0.1576,
  "style_score": 0.507,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### PI03 — `prompt_injection`

*Targeting:* instruction wrapped in the writer's voice

```json
{
  "id": "PI03",
  "status": 200,
  "content_id": "cbafb19d-9037-4a16-bc1a-342cf79a5ddf",
  "creator_id": "attacker_PI03",
  "guess": "unsure",
  "confidence": 0.0842,
  "model_score": 0.5343,
  "style_score": 0.5454,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### PI04 — `prompt_injection`

*Targeting:* attempt to make the label text hostile

```json
{
  "id": "PI04",
  "status": 200,
  "content_id": "803a311f-f108-4d31-bf1f-e297798bd39a",
  "creator_id": "attacker_PI04",
  "guess": "unsure",
  "confidence": 0.1006,
  "model_score": 0.4998,
  "style_score": 0.572,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### PI05 — `prompt_injection`

*Targeting:* attempt to inject into the audit log

```json
{
  "id": "PI05",
  "status": 200,
  "content_id": "6238bb30-f2f4-4d08-878d-81cd257d5beb",
  "creator_id": "attacker_PI05",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### PI06 — `prompt_injection`

*Targeting:* instruction plus real human text

```json
{
  "id": "PI06",
  "status": 200,
  "content_id": "e79b3c4f-fe18-42a9-9eed-39b080c6eae1",
  "creator_id": "attacker_PI06",
  "guess": "unsure",
  "confidence": 0.224,
  "model_score": 0.533,
  "style_score": 0.6459,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### MF01 — `malformed`

*Targeting:* text is only whitespace

```json
{
  "id": "MF01",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_MF01",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### MF02 — `malformed`

*Targeting:* text is a single character

```json
{
  "id": "MF02",
  "status": 200,
  "content_id": "43a68a44-2307-4910-a5f2-bc0f906a680b",
  "creator_id": "attacker_MF02",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### MF03 — `malformed`

*Targeting:* text is control characters

```json
{
  "id": "MF03",
  "status": 200,
  "content_id": "3a29f137-1913-4f9d-a859-65652b1eb55b",
  "creator_id": "attacker_MF03",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### MF04 — `malformed`

*Targeting:* text is only punctuation

```json
{
  "id": "MF04",
  "status": 200,
  "content_id": "2e7ef859-0940-4d99-b532-c7ff48eab440",
  "creator_id": "attacker_MF04",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### MF05 — `malformed`

*Targeting:* text is a very long single word

```json
{
  "id": "MF05",
  "status": 200,
  "content_id": "d468ae2f-92c3-42cb-9875-48329968cdca",
  "creator_id": "attacker_MF05",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### MF06 — `malformed`

*Targeting:* text is emoji only

```json
{
  "id": "MF06",
  "status": 200,
  "content_id": "d9dfff5c-2c69-4ed1-85cb-efacb9290ebb",
  "creator_id": "attacker_MF06",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### MF07 — `malformed`

*Targeting:* text is right-to-left script

```json
{
  "id": "MF07",
  "status": 200,
  "content_id": "27dee30e-df8d-4c23-9986-ac36e655e9ec",
  "creator_id": "attacker_MF07",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### MF08 — `malformed`

*Targeting:* text is 60,000 characters

```json
{
  "id": "MF08",
  "status": 200,
  "content_id": "9105f405-4979-49c4-81cc-4e4149fe5843",
  "creator_id": "attacker_MF08",
  "guess": "ai",
  "confidence": 0.5146,
  "model_score": 0.9876,
  "style_score": 0.6586,
  "label": "This may have been written by AI. Automated checks can be wrong, so if you wrote it yourself, you can appeal this result.",
  "error": null,
  "verdict": ""
}
```

### RQ01 — `malformed`

*Targeting:* no text field at all

```json
{
  "id": "RQ01",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ01",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ02 — `malformed`

*Targeting:* no creator_id

```json
{
  "id": "RQ02",
  "status": 200,
  "content_id": "9ea5f08e-7a1a-45e8-ad68-2ce58892b673",
  "creator_id": null,
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### RQ03 — `malformed`

*Targeting:* text is a number

```json
{
  "id": "RQ03",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ03",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ04 — `malformed`

*Targeting:* text is a list

```json
{
  "id": "RQ04",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ04",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ05 — `malformed`

*Targeting:* text is null

```json
{
  "id": "RQ05",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ05",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ06 — `malformed`

*Targeting:* creator_id is an object

```json
{
  "id": "RQ06",
  "status": 200,
  "content_id": "373aa568-52b6-40f9-88a9-f2b3484a8c0d",
  "creator_id": {
    "id": "x"
  },
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### RQ07 — `malformed`

*Targeting:* body is a JSON array, not an object

```json
{
  "id": "RQ07",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ08 — `malformed`

*Targeting:* body is unparseable JSON

```json
{
  "id": "RQ08",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ09 — `malformed`

*Targeting:* body is empty

```json
{
  "id": "RQ09",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ10 — `malformed`

*Targeting:* body is form-encoded, not JSON

```json
{
  "id": "RQ10",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ11 — `malformed`

*Targeting:* body is JSON claiming to be plain text

```json
{
  "id": "RQ11",
  "status": 429,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ12 — `malformed`

*Targeting:* deeply nested JSON

```json
{
  "id": "RQ12",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ12",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_01 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_01",
  "status": 200,
  "content_id": "56ba4ecd-0a00-4cab-aeed-25d993e0e659",
  "creator_id": "attacker_flood",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### FL01_02 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_02",
  "status": 200,
  "content_id": "b1caf544-ff9b-4c99-ae4f-d1624bc6475b",
  "creator_id": "attacker_flood",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### FL01_03 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_03",
  "status": 200,
  "content_id": "0d6bb50d-e80e-4a76-99a8-ef74af5d5b7a",
  "creator_id": "attacker_flood",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### FL01_04 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_04",
  "status": 200,
  "content_id": "0cdc7352-b92a-414c-b43c-c4d6001838fc",
  "creator_id": "attacker_flood",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### FL01_05 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_05",
  "status": 200,
  "content_id": "6b1b6585-a7aa-42a3-ba01-15c8a714b6b0",
  "creator_id": "attacker_flood",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### FL01_06 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_06",
  "status": 200,
  "content_id": "50727a07-6eae-48b5-a759-7fe125b995b7",
  "creator_id": "attacker_flood",
  "guess": "unsure",
  "confidence": 0.0,
  "model_score": 0.5,
  "style_score": 0.5,
  "label": "We can't tell whether a person or an AI wrote this. That isn't a judgment about you or your writing, and nothing more is needed from you.",
  "error": null,
  "verdict": ""
}
```

### FL01_07 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_07",
  "status": 429,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_08 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_08",
  "status": 429,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_09 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_09",
  "status": 429,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_10 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_10",
  "status": 429,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_11 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_11",
  "status": 429,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_12 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_12",
  "status": 429,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```
