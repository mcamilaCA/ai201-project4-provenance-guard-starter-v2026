#!/usr/bin/env python3
"""
Shows what per-creator rate limiting does, using status codes.

    python app.py                    # in one terminal (restart it first so the
                                     # counts start from zero)
    python check_creator_limits.py   # in another

Every request is short (under 40 words), so the model never loads and each
one returns fast. Every name is made fresh on each run, so earlier runs don't
leave counts behind that change the result. All requests come from this
machine, i.e. one address.
"""

import json
import time
import urllib.request
import uuid

import config

URL = "http://127.0.0.1:5000/submit"
RUN = uuid.uuid4().hex[:6]
TEXT = "A short note, well under forty words."
LIMIT = config.RATE_LIMIT_PER_MINUTE


def send(payload) -> int:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def burst(label: str, payloads: list) -> list[int]:
    codes = [send(p) for p in payloads]
    print(f"{label}\n    {' '.join(map(str, codes))}")
    return codes


def sub(creator):
    return {"text": TEXT, "creator_id": creator}


def main() -> None:
    n = LIMIT + 3
    a, b = f"writer-a-{RUN}", f"writer-b-{RUN}"
    print(f"limit: {LIMIT} per minute, {n} requests per burst, run {RUN}\n")

    burst(f"1. one creator ({a}) sends {n}", [sub(a)] * n)
    burst(f"2. a different creator ({b}), same address, sends 1", [sub(b)])

    spellings = [f"  {a.upper()} ", a.title(), f" {a}"]
    burst("3. creator 1 again, spelled three other ways (case and spaces)",
          [sub(s) for s in spellings])

    burst(f"4. one script sends {n} requests, a new creator_id on each",
          [sub(f"rotate-{RUN}-{i}") for i in range(n)])

    burst(f"5. {n} requests with no creator_id (counted by address)",
          [{"text": TEXT}] * n)
    burst("6. a creator_id that is not a string, 1 request (also by address)",
          [{"text": TEXT, "creator_id": {"x": 1}}])
    time.sleep(0)


if __name__ == "__main__":
    main()
