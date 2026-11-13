# Cost of one run — measured 2026-11-12_2241

The detector runs locally (gpt2), so there is no API spend. The cost measured is **seconds of compute per scored run**, plus tokens read.

## Method
- `measure_cost.py` drove the real `/submit` route in-process, 10 timed runs, one at a time, after one warm-up run.
- Warm-up (not counted) paid the one-time model load: **2.23 s** cold start.
- Texts: distinct writing samples of at least 40 words from `scenarios.py`, so the model really runs.
- wall = whole request (`time.perf_counter`); inference = GPT-2 forward pass alone; cpu = process CPU seconds (`time.process_time`, all threads).
- Machine: macOS-27.0.1-arm64-arm-64bit-Mach-O, Python 3.13.13.
- Dollar cost is 0.00 with the shipped pricing; it would be seconds × your hourly rate (`AI201_COMPUTE_USD_PER_HOUR`).

## Result (10 runs)

| Measure | Mean | Std dev | Min | Max |
|---|---|---|---|---|
| Wall time (s) | 0.0314 | 0.0028 | 0.0273 | 0.0355 |
| Model inference (s) | 0.0306 | 0.0028 | 0.0265 | 0.0346 |
| CPU time (s) | 0.0467 | 0.0053 | 0.0398 | 0.0556 |
| Input tokens | 69.2 | 8.8 | 58.0 | 86.0 |

**One run costs about 0.031 s of wall time (0.031 s in the model, 0.047 s of CPU) for about 69 tokens.**

## Per-run data

| Run | Words | Tokens | Wall s | Inference s | CPU s |
|---|---|---|---|---|---|
| 1 | 67 | 74 | 0.0345 | 0.0335 | 0.0532 |
| 2 | 55 | 61 | 0.0278 | 0.0270 | 0.0407 |
| 3 | 73 | 86 | 0.0355 | 0.0346 | 0.0556 |
| 4 | 46 | 58 | 0.0273 | 0.0265 | 0.0398 |
| 5 | 67 | 81 | 0.0335 | 0.0327 | 0.0512 |
| 6 | 56 | 66 | 0.0314 | 0.0307 | 0.0458 |
| 7 | 55 | 67 | 0.0320 | 0.0313 | 0.0468 |
| 8 | 58 | 69 | 0.0316 | 0.0309 | 0.0463 |
| 9 | 53 | 67 | 0.0318 | 0.0311 | 0.0464 |
| 10 | 53 | 63 | 0.0282 | 0.0275 | 0.0412 |
