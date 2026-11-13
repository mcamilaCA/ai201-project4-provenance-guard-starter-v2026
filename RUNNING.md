# Running Provenance Guard

How to run Provenance Guard, and how it is put together. **Everything you need to start it, check it and read its logs is in the next two sections.**

This is a **web service**. It runs on your machine and you talk to it with
`curl` from another terminal. If you've not built a backend before, that's
assumed — the starter ships one that already answers.

---

## Run it: local, with logs

Provenance Guard runs as a single local process on your own machine. Nothing is deployed to a server and no hosted service is called. Every record it produces stays in `logs/` as plain JSON lines, so the system can be inspected and diagnosed after the fact.

### Start command

From the project folder, with the virtual environment active:

```bash
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
python app.py
```

or without activating it:

```bash
.venv/bin/python app.py
```

It listens on `http://127.0.0.1:5000` (loopback only, so only this machine can reach it) and prints the settings it is using:

```
Provenance Guard on http://127.0.0.1:5000
  detector model:  gpt2
  rate limiting:   ON
  audit log:       .../logs/audit.jsonl
  telemetry:       ON  .../logs/runs.jsonl
```

**`python app.py` does not return: it keeps running and holds that terminal.** Open a **second terminal** for every `curl` below (pasting them into the first one does nothing). Stop the service with `Ctrl+C`. To confirm it is alive, from the second terminal:

When using the site ensure to use a second terminal, NOT the same one you used for the app.py command before

```bash
curl -s http://127.0.0.1:5000/health
curl -X POST http://127.0.0.1:5000/ping -H "Content-Type: application/json" -d '{"message": "hello"}'
```


⚠️ **macOS:** the AirPlay Receiver also listens on port 5000. If `python app.py` says *Address already in use*, or `curl localhost:5000` returns `403` with `Server: AirTunes`, either turn off AirPlay Receiver (System Settings) or start on another port: `PORT=5001 python app.py`. Use `127.0.0.1` rather than `localhost` in curl commands, since `localhost` can resolve to the AirPlay listener.

### Environment needs

| Need | Requirement |
|---|---|
| Python | 3.11, 3.12 or 3.13 (not 3.14). Tested on 3.13 |
| Packages | `pip install -r requirements.txt` (Flask, Flask-Limiter, requests, transformers, torch) |
| Disk | About 9 GB free (torch is most of it). The GPT-2 model itself is about 550 MB |
| Memory | 4 GB RAM minimum |
| Network | Only for the first run, to download GPT-2. After that it runs offline |
| Accounts / keys | None. The model runs locally, so there is no API key and no usage bill |
| OS | Developed on macOS; nothing in the code is platform-specific |

First-time setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python test.py          # checks Python, packages, disk, model and the service
python detector.py      # downloads GPT-2 (~550 MB) and scores a sample
```

The first request after every start is slow (about 3 to 8 seconds) because GPT-2 loads into memory on first use. After that a submission takes tens of milliseconds to about a second. Run `python detector.py` or send one request after starting if you want the model warm before real use.

### Settings (environment variables)

All have defaults, so none are required.

| Variable | Default | Effect |
|---|---|---|
| `HOST` | `127.0.0.1` | Address to listen on. Keep it on loopback for local use |
| `PORT` | `5000` | Port to listen on |
| `AI201_DEBUG` | `1` | Flask debug mode. Switches itself off whenever `HOST` is not loopback |
| `AI201_DETECTOR_MODEL` | `gpt2` | Which Hugging Face model the model signal uses |
| `AI201_TELEMETRY` | `1` | Set to `0` to stop writing `runs`, `failures` and `client_link` logs |
| `AI201_COMPUTE_USD_PER_HOUR` | `0` | Machine cost used to turn model seconds into a dollar figure |

Rate limits (6 per minute, 100 per day, per creator) are set in `config.py`.

### Where the logs go

| File | Written by | Contents |
|---|---|---|
| `logs/audit.jsonl` | every decision, rejection and appeal | the decision record, now with a `run_id` |
| `logs/runs.jsonl` | every request | stage timings, model time vs overhead, tokens, cost, outcome |
| `logs/failures.jsonl` | every failed request | stage, error type, message, category |
| `logs/client_link.jsonl` | `run_eval.py` and `run_attacks.py` | client-side attempts, retries, timeouts |

They are append-only and created on first use. Read them back with `python metrics.py`, or through the running service at `/metrics`, `/runs`, `/failures` and `/log` (details in *Telemetry and metrics* below).

### Limits of this setup

- **One process only.** The rate-limit counters live in memory, so restarting the service resets them, and running several copies would not share them. The model is also loaded once per process.
- **Logs grow without bound.** Nothing rotates or deletes them. `audit.clear()` wipes the audit log; delete the other files by hand if you want a fresh start.
- **Local only.** Binding to anything other than loopback exposes an unauthenticated service. Gunicorn is pinned in `requirements.txt` for a later unit but this setup does not use it.

---

## Check that it works (five minutes)

With the service running in the first terminal, use the second.

**1. The control route.** `/ping` only echoes your message back. If it answers, the service itself is fine:

```bash
curl -X POST http://127.0.0.1:5000/ping -H "Content-Type: application/json" -d '{"message": "hello"}'
```

**2. Score some writing.** `/submit` needs `text` and `creator_id`. Text under 40 words returns an "unsure" result without running the model, so use a paragraph:

```bash
curl -X POST http://127.0.0.1:5000/submit -H "Content-Type: application/json" \
  -d '{"creator_id": "me", "text": "I walked down to the harbour early, before the fishermen had even started on their nets, and the water was flat and grey. The gulls were quiet for once. My grandfather used to say that the sea keeps its own counsel, and standing there with cold hands and a thermos going lukewarm, I finally understood what he meant by it."}'
```

You get back `content_id`, `guess`, `confidence`, `label`, `model_score` and `style_score`. The first call after a start takes several seconds while GPT-2 loads.

**3. Appeal it** (use the `content_id` from step 2):

```bash
curl -X POST http://127.0.0.1:5000/appeal -H "Content-Type: application/json" \
  -d '{"content_id": "<content_id>", "reasoning": "I wrote this myself."}'
```

**4. See what was recorded:**

```bash
curl "http://127.0.0.1:5000/log?limit=3"
python metrics.py
```

**Rate limit:** each `creator_id` may submit 6 per minute and 100 per day. The 7th request in a minute returns `429`, and that refusal is still logged.

> **On Windows, use `curl.exe` and keep it on one line.**
>
> In PowerShell, `curl` is an alias for a different tool and the commands above
> fail with `Cannot bind parameter 'Headers'`. The `\` line breaks don't work
> there either. This does:
>
> ```powershell
> curl.exe -X POST http://127.0.0.1:5000/ping -H "Content-Type: application/json" -d '{\"message\": \"hello\"}'
> ```
>
> Git Bash needs no change.

**Leave `/ping` alone.** When something breaks later, check `/ping` still answers: if it does, the problem is in the handler; if it doesn't, it's the service itself.

---

## The routes

| Route | What it does |
|---|---|
| `POST /ping` | The control route. Echoes your message |
| `GET /health` | Is the service up, is the model loaded |
| `POST /submit` | Scores text; returns label, confidence and both signal scores |
| `POST /appeal` | Records a writer's appeal; the item becomes `under_review` |
| `GET /content/<id>` | One item's current status |
| `GET /log` | The audit log (`?limit=N`) |
| `GET /metrics` | Counts, error rates, latency percentiles, cost (`?since=<seconds>`) |
| `GET /runs` | Execution records (`?limit=N`, `?run_id=<id>`) |
| `GET /failures` | Failure records (`?limit=N`, `?category=<name>`) |

---

## Every command

| Command | What it does |
|---|---|
| `python test.py` | Checks your environment |
| `python app.py` | Runs the service |
| `python metrics.py` | Operational metrics from the telemetry logs (`--since 3600`, `--json`) |
| `python measure_cost.py` | Measures the compute cost of one run over 10 runs; writes `results/cost_measurement_*.md` |
| `python check_unit9.py` | Runs the unit-9 criteria (U9-1 to U9-5) three times, triggers failures on purpose, writes `results/unit9_criteria_*.md` |
| `python test_telemetry.py` | Self-check for the telemetry layer (no model needed) |
| `python detector.py` | Downloads the model and scores a sample — **run before class** |
| `python detector.py "some text"` | Score one piece of text from the terminal |
| `python stylometry.py "some text"` | Your style measures, on one piece of text |
| `python run_attacks.py --set <folder>` | The attack set — **unit 8** |
| `python run_attacks.py --flood 15` | Push past your rate limit and print the status codes — **unit 8** |
| `python run_eval.py --label before` | Your five criteria, three trials — **unit 8** |

---

## Which piece goes with which milestone

### Unit 7 — the build

| Milestone | What you're doing | Where |
|---|---|---|
| 1 | Trace a submission on paper | Nothing to run |
| 2 | Write your criteria | `criteria.md` — all five are yours |
| 3 | The route, one signal, the log | `app.py::submit`, `detector.py`, `audit.py` |
| 4 | Second signal, combine, score | `stylometry.py`, `scoring.py::combine_signals` |
| 5 | Labels and the appeal path | `scoring.py::score_to_label`, `app.py::appeal` |
| 6 | Write it up | `README.md` |

### Unit 8 — the test

| Milestone | What you're doing | Where |
|---|---|---|
| 1 | Rate limiting and the full log | `config.py`, the decorator in `app.py` |
| 2 | Run the attack set | `run_attacks.py` |
| 3 | Run your own criteria | `scenarios.py`, `run_eval.py` |
| 4 | Verdicts and diagnoses | `README.md` |
| 5 | Fix one thing, re-run | `run_attacks.py --label after` |
| 6 | What's still broken | `README.md` |

---

## Building `/submit` in three passes

The ordering is deliberate. It's how you tell a broken route from a broken
signal.

**Milestone 3.** Return a hardcoded response. Confirm `curl` gets it back
**before** you add any logic. Then pull `text` and `creator_id` out. Then call
one signal. Then log it.

**Milestone 4.** Add the second signal. Combine them. Log both scores.

**Milestone 5.** Turn the score into a label.

> Test each signal from a terminal on its own before wiring it in. If you skip
> that you'll spend an hour not knowing whether the route or the signal is
> lying to you.

---

## Turning on rate limiting (unit 8)

> **Already done in this repo:** rate limiting is on and the decorator is active, so you don't need to do this to run the system. The steps are kept for reference.

Three steps:

1. In `config.py`, set `RATE_LIMITING_ENABLED = True` — or run with
   `AI201_RATE_LIMITS=1`.
2. Choose your numbers there.
3. In `app.py`, uncomment the `@limiter.limit(...)` line above `submit`.

Then push past your limit and watch for `429`:

```bash
python run_attacks.py --flood 15
```

That sends 15 submissions from one `creator_id` and prints the run of status
codes — `200 200 200 ... 429 429` — which is exactly what your README's **Rate
Limiting** section asks you to paste. It also writes `results/flood_<date>.md`.

The attack set can't do this for you. Every attack row submits under its own
`creator_id`, so a full attack run looks like forty-odd different callers and
never trips a limit however long it is.

No `429` at all? Either your limit is above 15 a minute, or rate limiting is
still off. `GET /health` reports which.

Rejections are logged for you. **An attack that shows up only as an absence is
one you'll never find** — a thousand requests that got a `429` and left no
trace look exactly like a quiet afternoon.

---

## Running it somewhere else (unit 9)

Unit 9 asks you to deploy one of your systems. **Read this before you pick
which one** — for this project the answer is already decided, and it isn't the
hosted one.

Flask's built-in server says "development server" on startup because that's
what it is. A real one comes from `gunicorn`, which is in
`requirements.txt` and unused until now:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

Two settings do the work, and both read the environment:

| Variable | Default | What it does |
|---|---|---|
| `HOST` | `127.0.0.1` | Loopback — your machine only. A host needs `0.0.0.0`, or nothing outside the box can reach the service and it looks like the app is down |
| `PORT` | `5000` | Most hosts hand you a port in `PORT` and expect you to bind exactly that one |
| `AI201_DEBUG` | `1` | Debug mode. Off automatically whenever `HOST` isn't loopback — an interactive debugger on a public address is a stranger's Python prompt inside your process |

Nothing about your local workflow changes. With no variables set you get
`http://127.0.0.1:5000` and every `curl` above still works.

### This project will not fit a free host

Say it plainly, because the arithmetic is the point:

| What has to be in memory | Roughly |
|---|---|
| `torch` | ~200–800 MB depending on the build |
| the `gpt2` weights | ~550 MB on disk, loaded into RAM to score |
| Flask, gunicorn, your code | the rest |
| **A free tier gives you** | **512 MB** |

That's over budget before a single request arrives — and a free host has no
persistent disk, so the 550 MB download starts again after every idle
spin-down. There is no configuration that fixes this. The model is the size it
is.

**So pair 4 extensions take Path B — local, with logs.** That is the expected
answer for this project, not a fallback and not a failure. Working out that a
system doesn't fit its host *before* you spend an evening watching it get
killed is the skill unit 9 is actually testing. Write the arithmetic above in
your write-up; that's the deliverable.

---

## Where everything lives

| File | What it does |
|---|---|
| `config.py` | Every setting: thresholds, weights, rate limits, the model |
| `app.py` | The service and all its routes |
| `detector.py` | Signal one — the local model. Given to you |
| `stylometry.py` | Signal two |
| `scoring.py` | Combining and labelling |
| `audit.py` | The audit log writer |
| `telemetry.py` | Run ids, stage timings, failure records, cost |
| `metrics.py` | Aggregates the telemetry logs |
| `link_client.py` | Records client-side attempts, retries and timeouts |
| `measure_cost.py` | The ten-run cost measurement |
| `run_attacks.py` | Runs the attack set — **unit 8** |
| `run_eval.py` | Runs your criteria three times — **unit 8** |
| `scenarios.py` | What your test runs. **You fill this in** |
| `criteria.md` | Your five criteria. **You write all five** |
| `logs/` | `audit.jsonl`, `runs.jsonl`, `failures.jsonl`, `client_link.jsonl`. **Commit them** |
| `results/` | Attack runs and run logs. **Commit them** |

---

## The two blind spots, up front

Both signals have one, and unit 8's attack set is built out of them. You have
to name them yourself in Milestone 1 — but knowing they exist now saves you
from being surprised.

**Signal one** measures how *predictable* your text is. Predictability isn't
authorship. What it really rewards is common words in short, ordinary
sentences — someone writing in a second language and staying with vocabulary
they're sure of, a younger writer, anyone writing plainly on purpose. Writing
like that scores about as machine-like as machine writing does. (Dense, ornate
prose often goes the other way and reads as human, because rare words are what
a language model fails to predict.) So the writers this signal is most likely
to accuse are the ones with the least room to argue back. That is the false
positive the whole project is about, and it's structural rather than a bug.

**Signal two** cannot read. It has no idea what the text says. Anything that
changes the shape without changing the substance moves it — typos, broken-up
sentences, a pasted quotation. That is very cheap to do on purpose.

---

## When something goes wrong

| What you see | What it means |
|---|---|
| `404` from curl | Is the server running? Is the path exactly what you typed? |
| `Cannot bind parameter 'Headers'` | You're in PowerShell, where `curl` is a different tool. Use `curl.exe`, on one line |
| Request body arrives empty | curl needs `-H "Content-Type: application/json"` |
| `Address already in use` | An earlier `app.py` is still running, or (macOS) AirPlay Receiver holds port 5000. Stop the old one, or run `PORT=5001 python app.py` |
| `curl` prints nothing | The service isn't running, or you pasted the curl lines into the terminal that is running `app.py`. Use a second terminal, and drop `-s` so errors show |
| `403` with `Server: AirTunes` | macOS AirPlay, not this service. Use `127.0.0.1` rather than `localhost`, or change `PORT` |
| The first submission takes 10+ seconds | Signal one is loading the model into memory. Later ones take a second or two |
| *Every* submission takes 10+ seconds | Something is reloading the model each call. `GET /health` shows `detector_loaded` — if it goes back to `false`, look for a reload in your handler |
| `DetectorUnavailable` | Run `python detector.py` once to download the model |
| `/appeal` seems to do nothing | Does the `content_id` you sent actually exist in the log? A typo there fails silently |
| Every request gets through, no `429` ever | The decorator is uncommented but limiting is still off. Set `RATE_LIMITING_ENABLED` in `config.py` |
| Flask-Limiter warns about storage | Shouldn't happen — `storage_uri` is preconfigured. If you changed it, put it back |
| All three of your labels never appear | Your ranges have a gap. `scoring.label_ranges()` prints them |

If the route won't respond, go back to `/ping`. If that answers, the problem is
in your handler.

---

## A note on committing

At least four new commits in unit 7, four more in unit 8.

`logs/` and `results/` are deliberately **not** in `.gitignore`. Your audit log
is evidence, and the entries you paste into your README are what unit 8 grades.

**Do not delete and recreate this repository.** You submit the same URL both
units.

---

## Telemetry and metrics

Every request gets a `run_id` (returned as the `X-Request-ID` header, and written
into its `audit.jsonl` entry). Records go beside the audit log as JSON lines:

| File | One line per | Holds |
|---|---|---|
| `logs/runs.jsonl` | request | stage timings, model time vs overhead, tokens, cost, outcome |
| `logs/failures.jsonl` | failure | stage, error type, message, category (`timeout`, `rate_limit`, `bad_response`, `validation_failure`, `model_unavailable`, …) |
| `logs/client_link.jsonl` | client attempt | status, latency, retries, timeouts (from `run_eval.py` / `run_attacks.py`) |

Read them back:

```bash
python metrics.py [--since 3600] [--json]     # counts, error rates, p50/p95/p99, cost, API-link health
curl "http://127.0.0.1:5000/metrics?since=3600"
curl "http://127.0.0.1:5000/runs?limit=10"
curl "http://127.0.0.1:5000/runs?run_id=<id>"  # one request: run + failures + audit entries
curl "http://127.0.0.1:5000/failures?category=rate_limit"
```

Cost is $0 by default because the detector runs locally; set `config.PRICING`
or `AI201_COMPUTE_USD_PER_HOUR` to price it. `AI201_TELEMETRY=0` turns recording
off. Self-check: `python test_telemetry.py`.
