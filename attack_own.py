#!/usr/bin/env python3
"""
Three attacks of my own, sent to my own service through POST /submit.

    python app.py            # in one terminal
    python attack_own.py     # in another

Each attack is sent next to an unmodified control so a change in score comes from
the edit. Requests are spaced out to stay under the per-minute rate limit.
"""

import json
import sys
import textwrap
import time
import urllib.request
from datetime import datetime

import config

URL = "http://127.0.0.1:5000/submit"
PAUSE = 12  # seconds between requests; the limit is 6 per minute

AI_PARAGRAPH = (
    "Remote work has transformed the modern workplace in significant ways. "
    "First, it offers employees greater flexibility, allowing them to balance "
    "professional and personal responsibilities. Additionally, it reduces "
    "commuting time, which can improve overall well-being. Furthermore, "
    "companies can access a broader talent pool. However, it is important to "
    "consider challenges such as communication barriers and feelings of "
    "isolation. Overall, remote work presents both opportunities and "
    "challenges for organizations."
)

# Attack 1: Latin a, e, o replaced by the Cyrillic letters that look the same.
HOMOGLYPHS = {"a": "а", "e": "е", "o": "о"}


def homoglyph(text: str) -> str:
    return "".join(HOMOGLYPHS.get(c, c) for c in text)


# Attack 2: a human paragraph of my own, plain and a little rambling.
HUMAN_PARAGRAPH = (
    "I keep meaning to clean out the garage but every weekend something else "
    "comes up. Last Saturday it was my brother's car, which wouldn't start, "
    "and then it rained, and then I just sat on the porch with a sandwich "
    "and watched the neighbour's dog chase a squirrel around the same tree "
    "for twenty minutes. Honestly it was the best part of the week. The "
    "garage can wait another month, I guess, and nobody is going to notice "
    "the boxes anyway."
)

# Attack 3: casual human-style text long enough to fill the 400-token window,
# then the AI paragraph last.
CASUAL_OPENING = (
    "So this week was a mess, where do I even start. On Monday the bus never "
    "showed up and I walked the whole way to work in the drizzle, which "
    "would have been fine except I had on the wrong shoes. My feet were "
    "soaked by the time I got to the office and the heating was broken, so I "
    "spent the morning with my socks on the radiator like a kid. Tuesday my "
    "sister called about the family reunion, and of course nobody can agree "
    "on a date, my uncle wants July because of the fishing, my cousin wants "
    "August because of her job, and my mother just keeps saying she doesn't "
    "mind, which means she minds a lot. Wednesday I tried a new recipe, "
    "some kind of lentil stew with way too much cumin, and the whole flat "
    "smelled like a market for two days. My flatmate pretended not to "
    "notice, bless him. Thursday was quiet, I finally fixed the wobbly "
    "chair, I watched a documentary about octopuses that made me cry for "
    "reasons I can't explain, and then I stayed up far too late reading "
    "about the history of tea. Friday the printer died right when I needed "
    "to send a form, so I ended up at the library, where an old man next to "
    "me kept humming the same three notes of some song I almost recognised. "
    "I asked him what it was and he said he had no idea, he had been "
    "humming it since the nineties. Saturday I slept until noon, called my "
    "grandmother, and promised to visit soon, which I say every time. The "
    "weekend was slow, the kind where you wander around the shops without "
    "buying anything and eat a pastry on a bench. I took a long walk along "
    "the canal, counted seven ducks and one very confident swan, and "
    "thought about how small these weeks add up to something. Anyway, "
    "that was my week, nothing special, but I wanted to write it down "
    "before I forgot all of it. Oh, and the swan followed me for a bit, "
    "which was either charming or a threat, I still can't decide, and I "
    "told nobody about it because who would believe me. "
)

ATTACKS = [
    {
        "id": "OWN1",
        "name": "lookalike letters",
        "targets": "signal one (rare tokens) and signal two (words() drops them)",
        "control": ("OWN1_control", AI_PARAGRAPH),
        "attack": ("OWN1_attack", homoglyph(AI_PARAGRAPH)),
    },
    {
        "id": "OWN2",
        "name": "hard-wrapped human text",
        "targets": "signal two (newlines split sentences)",
        "control": ("OWN2_control", HUMAN_PARAGRAPH),
        "attack": ("OWN2_attack", textwrap.fill(HUMAN_PARAGRAPH, width=34)),
    },
    {
        "id": "OWN3",
        "name": "AI text past the token window",
        "targets": "signal one (reads only the first "
        f"{config.DETECTOR_MAX_TOKENS} tokens)",
        "control": ("OWN3_control", AI_PARAGRAPH),
        "attack": ("OWN3_attack", CASUAL_OPENING + AI_PARAGRAPH),
    },
]


def submit(creator: str, text: str) -> dict:
    body = json.dumps({"text": text, "creator_id": creator}).encode()
    req = urllib.request.Request(
        URL, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return {"status": r.status, **json.loads(r.read())}
    except urllib.error.HTTPError as e:
        return {"status": e.code, **json.loads(e.read() or b"{}")}


def combined(r: dict) -> float | None:
    if r.get("model_score") is None:
        return None
    return round(
        config.WEIGHT_MODEL_SIGNAL * r["model_score"]
        + config.WEIGHT_STYLE_SIGNAL * r["style_score"],
        4,
    )


def main() -> int:
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out = config.RESULTS_DIR / f"attack_own_{stamp}.json"
    results = []
    first = True
    for a in ATTACKS:
        row = {"id": a["id"], "name": a["name"], "targets": a["targets"]}
        for kind in ("control", "attack"):
            creator, text = a[kind]
            if not first:
                time.sleep(PAUSE)
            first = False
            r = submit(creator, text)
            r["words"] = len(text.split())
            r["combined"] = combined(r)
            r["sent"] = text[:70]
            row[kind] = r
            print(
                f"{creator:14} {r['status']}  {r.get('guess')}  "
                f"model {r.get('model_score')}  style {r.get('style_score')}  "
                f"combined {r['combined']}"
            )
        results.append(row)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
