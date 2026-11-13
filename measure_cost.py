#!/usr/bin/env python3
"""
Measure what one scored run costs, in seconds of compute.

    .venv/bin/python measure_cost.py              # 10 runs (default)
    .venv/bin/python measure_cost.py --runs 20

The detector is a local model, so there is no API bill. The real cost of a run
is the compute it uses, and that is what this measures.

How it measures
  * It drives the real app in-process (Flask's test client), so every run goes
    through the same /submit route, stages and telemetry as a live request.
    Logs go to a temporary folder, so your logs/ are not touched.
  * One warm-up submission first. It pays the one-time model load (reported
    separately as the cold start) so it doesn't distort the average.
  * Then N timed submissions, one at a time, each a different text of at least
    MIN_WORDS words taken from scenarios.py (shorter texts skip the model and
    would measure nothing).
  * Per run it reads back what telemetry recorded:
        wall       whole request, start to finish (time.perf_counter)
        inference  the GPT-2 forward pass alone
        cpu        CPU seconds the process used (time.process_time)
        tokens     tokens the model read
  * It reports mean, standard deviation, min and max, and writes the result to
    results/cost_measurement_<timestamp>.md.

Caveats: numbers are specific to this machine and its load at the time;
`cpu` counts all threads, so close other heavy programs while it runs.
"""

import argparse
import json
import platform
import statistics
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import config

_tmp = Path(tempfile.mkdtemp(prefix="cost_measure_"))
config.LOG_DIR = _tmp
config.AUDIT_LOG = _tmp / "audit.jsonl"
config.RUNS_LOG = _tmp / "runs.jsonl"
config.FAILURES_LOG = _tmp / "failures.jsonl"
config.CLIENT_LINK_LOG = _tmp / "client_link.jsonl"

import app as appmod  # noqa: E402
import scenarios  # noqa: E402
import telemetry  # noqa: E402


def pick_texts(n):
    texts = [t for sc in scenarios.SCENARIOS for t in sc.get("texts", [])
             if len(t.split()) >= config.MIN_WORDS]
    if not texts:
        sys.exit("No texts of at least MIN_WORDS words in scenarios.py.")
    return [texts[i % len(texts)] for i in range(n)]


def stats(values):
    return {
        "mean": statistics.mean(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--runs", type=int, default=10)
    args = parser.parse_args()

    client = appmod.app.test_client()
    texts = pick_texts(args.runs + 1)

    print("Warm-up run (loads the model; not counted)...")
    r = client.post("/submit", json={"text": texts[0], "creator_id": "cost-warmup"})
    if r.status_code != 200:
        sys.exit(f"Warm-up failed: {r.status_code} {r.get_data(as_text=True)[:200]}")

    for i, text in enumerate(texts[1:], 1):
        r = client.post("/submit", json={"text": text, "creator_id": f"cost-{i}"})
        print(f"  run {i:>2}/{args.runs}: HTTP {r.status_code}")
        if r.status_code != 200:
            sys.exit("A timed run failed; the measurement would be wrong.")

    runs = telemetry.read_records(config.RUNS_LOG)
    warm, timed = runs[0], runs[1:]
    rows = []
    for rec in timed:
        c = rec["cost"]["compute_seconds"]
        rows.append({"wall": c["wall"], "inference": c["inference"], "cpu": c["cpu"],
                     "tokens": rec["usage"]["input_tokens"],
                     "words": rec["input"]["words"]})
    s = {k: stats([row[k] for row in rows]) for k in ("wall", "inference", "cpu", "tokens")}
    cold_load_s = sum(i["load_ms"] for i in warm["inference"]) / 1000

    when = datetime.now().strftime("%Y-%m-%d_%H%M")
    lines = [
        f"# Cost of one run — measured {when}",
        "",
        f"The detector runs locally ({config.DETECTOR_MODEL}), so there is no API spend. "
        "The cost measured is **seconds of compute per scored run**, plus tokens read.",
        "",
        "## Method",
        f"- `measure_cost.py` drove the real `/submit` route in-process, {args.runs} timed runs, "
        "one at a time, after one warm-up run.",
        f"- Warm-up (not counted) paid the one-time model load: **{cold_load_s:.2f} s** cold start.",
        "- Texts: distinct writing samples of at least "
        f"{config.MIN_WORDS} words from `scenarios.py`, so the model really runs.",
        "- wall = whole request (`time.perf_counter`); inference = GPT-2 forward pass alone; "
        "cpu = process CPU seconds (`time.process_time`, all threads).",
        f"- Machine: {platform.platform()}, Python {platform.python_version()}.",
        "- Dollar cost is 0.00 with the shipped pricing; it would be seconds × your hourly rate "
        "(`AI201_COMPUTE_USD_PER_HOUR`).",
        "",
        f"## Result ({args.runs} runs)",
        "",
        "| Measure | Mean | Std dev | Min | Max |",
        "|---|---|---|---|---|",
    ]
    for label, key, unit, fmt in (("Wall time (s)", "wall", "s", "{:.4f}"),
                                  ("Model inference (s)", "inference", "s", "{:.4f}"),
                                  ("CPU time (s)", "cpu", "s", "{:.4f}"),
                                  ("Input tokens", "tokens", "", "{:.1f}")):
        v = s[key]
        cells = " | ".join(fmt.format(v[k]) for k in ("mean", "stdev", "min", "max"))
        lines.append(f"| {label} | {cells} |")
    lines += [
        "",
        f"**One run costs about {s['wall']['mean']:.3f} s of wall time "
        f"({s['inference']['mean']:.3f} s in the model, {s['cpu']['mean']:.3f} s of CPU) "
        f"for about {s['tokens']['mean']:.0f} tokens.**",
        "",
        "## Per-run data",
        "",
        "| Run | Words | Tokens | Wall s | Inference s | CPU s |",
        "|---|---|---|---|---|---|",
    ]
    for i, row in enumerate(rows, 1):
        lines.append(f"| {i} | {row['words']} | {row['tokens']} | {row['wall']:.4f} | "
                     f"{row['inference']:.4f} | {row['cpu']:.4f} |")
    report = "\n".join(lines) + "\n"

    config.RESULTS_DIR.mkdir(exist_ok=True)
    out = config.RESULTS_DIR / f"cost_measurement_{when}.md"
    out.write_text(report, encoding="utf-8")
    print("\n" + report)
    print(f"Written to {out}")


if __name__ == "__main__":
    main()
