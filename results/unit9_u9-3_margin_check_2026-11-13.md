# U9-3 margin check — 2026-11-13

Run after the recorded 3-trial run, to see how much room U9-3's targets had.
Method: the same procedure as `check_unit9.py::u9_3` (warm `/submit` requests
over real HTTP, different text and `creator_id` each time, client stopwatch vs
recorded `duration_ms`, stage durations summed), run from a throwaway script
that is not kept in the repo, scored against several limits. Raw output:

## Pass 1: 60 requests (3 x 20)

```
60 requests: gap ms min 0.95 mean 1.12 max 2.02 | coverage min 0.9798 mean 0.9916
gap limit 15 ms: 60/60 within
gap limit 10 ms: 60/60 within
gap limit  5 ms: 60/60 within
gap limit  3 ms: 60/60 within
gap limit  2 ms: 59/60 within
coverage >= 0.98: 59/60
coverage >= 0.99: 56/60
coverage >= 0.995: 1/60
400-token text, 30 runs: p50 103.5 p95 111.0 max 119.4 ms
```

## Pass 2: 120 requests (6 x 20), looking for the cause

```
120 requests; coverage < 0.98: 0 | < 0.985: 0
worst 6 (coverage, request ms, untimed ms, words, model_signal stage ms, its overhead ms):
  0.9864   29.04  0.394   46   28.38  0.237
  0.9893   29.28  0.312   55   28.70  0.247
  0.9900   28.52  0.286   53   27.99  0.193
  0.9901   28.40  0.280   53   27.87  0.243
  0.9903   27.52  0.268   46   27.00  0.189
  0.9905   27.70  0.263   46   27.22  0.183
untimed ms: min 0.221 median 0.250 max 0.394
request ms for the 6 shortest: [27.489, 27.522, 27.539, 27.603, 27.702, 27.772]
```

Reading: 1 request in 240 (pass 1: 1 of 60, pass 2: 0 of 120, recorded run: 0
of 60) fell below 98% coverage. Time outside the timed stages is about 0.25 ms
per request, so a 28 ms request sits near 99% and it takes about 0.3 ms of extra
jitter to cross 98%.
