#!/usr/bin/env python3
"""
Produce the numbers for the five unit-9 criteria in criteria.md (U9-1 .. U9-5).

    .venv/bin/python check_unit9.py              # 3 trials (what the criteria ask for)
    .venv/bin/python check_unit9.py --trials 1

What it does, per trial:

  U9-1  a 20-request mixed batch (10 valid submits, 3 refused inputs, 2 requests
        over the rate limit, 3 /ping, 2 /health); counts ids in the headers, the
        run log and the audit log.
  U9-2  triggers failures on purpose: blank text, missing text, the 7th and 8th
        request from one creator inside a minute, and (in a fresh process started
        with a model name that doesn't exist) a model-load failure. Counts the
        records and checks stage, category and status of each.
  U9-3  20 warm /submit requests over real HTTP, each timed with a client-side
        stopwatch and compared to the recorded duration_ms and stage times.
  U9-4  a 21-request batch (16 ok, 3 refused, 2 rate-limited); compares six
        figures from GET /metrics with a recount of the raw log files.
  U9-5  10 fixed texts with telemetry on vs off (same answers?), then 10 valid +
        1 blank request with the telemetry log files made unwritable.

Everything runs against a private copy of the app that writes to a temp folder,
so logs/ is never touched. The service is served over real HTTP (Werkzeug) on a
free local port. The model is loaded once and warmed up before trial 1; the
rate limiter uses a fresh creator_id per trial so counts never carry over.

Output: results/unit9_criteria_<timestamp>.md (and .json).
"""

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp(prefix="unit9_"))

RESPONSE_KEYS = {"content_id", "guess", "confidence", "label", "model_score", "style_score"}
GAP_LIMIT_MS = 15.0
STAGE_COVERAGE = 0.98
BAD_MODEL = "not-a-real-model-xyz"


# ── harness ──────────────────────────────────────────────────────────────────

def point_logs_at(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    config.LOG_DIR = folder
    config.AUDIT_LOG = folder / "audit.jsonl"
    config.RUNS_LOG = folder / "runs.jsonl"
    config.FAILURES_LOG = folder / "failures.jsonl"
    config.CLIENT_LINK_LOG = folder / "client_link.jsonl"
    return folder


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists() or path.is_dir():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def human_texts() -> list[str]:
    import scenarios
    texts = [t for sc in scenarios.SCENARIOS for t in sc.get("texts", [])
             if len(t.split()) >= config.MIN_WORDS]
    if len(texts) < 10:
        sys.exit("Need at least 10 texts of MIN_WORDS words in scenarios.py.")
    return texts


class Service:
    """The real app, served over HTTP in this process, logging to a temp folder."""

    def __init__(self):
        point_logs_at(TMP / "boot")
        import app as appmod
        from werkzeug.serving import make_server
        self.app = appmod.app
        self.app.testing = False
        self.server = make_server("127.0.0.1", 0, self.app, threaded=True)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def post(self, path, body=None):
        import requests
        t0 = time.perf_counter()
        r = requests.post(self.url + path, json=body, timeout=120)
        return r, (time.perf_counter() - t0) * 1000

    def get(self, path):
        import requests
        t0 = time.perf_counter()
        r = requests.get(self.url + path, timeout=120)
        return r, (time.perf_counter() - t0) * 1000


def mixed_batch(svc, texts, creator_prefix, valid_other, refused=3, ping=0, health=0):
    """
    6 valid submits from one creator, then 2 more from it (rate-limited), then
    `valid_other` valid submits from other creators, `refused` bad inputs, and
    optional /ping and /health. Returns one dict per request.
    """
    out = []

    def rec(kind, r, ms):
        out.append({"kind": kind, "status": r.status_code,
                    "rid": r.headers.get("X-Request-ID"), "client_ms": ms})

    flood = f"{creator_prefix}-flood"
    for i in range(config.RATE_LIMIT_PER_MINUTE):
        rec("valid", *svc.post("/submit", {"text": texts[i % len(texts)], "creator_id": flood}))
    for _ in range(2):
        rec("limited", *svc.post("/submit", {"text": texts[0], "creator_id": flood}))
    for i in range(valid_other):
        rec("valid", *svc.post("/submit", {"text": texts[i % len(texts)],
                                           "creator_id": f"{creator_prefix}-u{i}"}))
    bad_bodies = [{"text": "   ", "creator_id": f"{creator_prefix}-bad"},
                  {"creator_id": f"{creator_prefix}-bad"},
                  {"text": 12345, "creator_id": f"{creator_prefix}-bad"}]
    for body in bad_bodies[:refused]:
        rec("refused", *svc.post("/submit", body))
    for _ in range(ping):
        rec("ping", *svc.post("/ping", {"message": "hi"}))
    for _ in range(health):
        rec("health", *svc.get("/health"))
    return out


# ── the five criteria ────────────────────────────────────────────────────────

def u9_1(svc, texts, trial):
    point_logs_at(TMP / f"t{trial}-u1")
    reqs = mixed_batch(svc, texts, f"t{trial}u1", valid_other=4, refused=3, ping=3, health=2)
    assert len(reqs) == 20, len(reqs)
    runs = read_jsonl(config.RUNS_LOG)
    audit_ids = Counter(e.get("run_id") for e in read_jsonl(config.AUDIT_LOG))
    run_counts = Counter(r["run_id"] for r in runs)
    with_header = sum(1 for r in reqs if r["rid"])
    traced = sum(1 for r in reqs if r["rid"] and run_counts[r["rid"]] == 1)
    audited_kinds = [r for r in reqs if r["kind"] in ("valid", "refused", "limited")]
    audited = sum(1 for r in audited_kinds if r["rid"] and audit_ids[r["rid"]] >= 1)
    ok = with_header == 20 and traced == 20 and len(runs) == 20 and audited == 15
    return ok, {"header": f"{with_header}/20", "one run record each": f"{traced}/20",
                "run records in file": len(runs), "audit entries joined": f"{audited}/15"}


def u9_2_bad_model(trial):
    """A model-load failure needs a fresh process: the real app, a model that doesn't exist."""
    out = TMP / f"t{trial}-badmodel.json"
    env = dict(os.environ, AI201_DETECTOR_MODEL=BAD_MODEL, HF_HUB_OFFLINE="1")
    subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker-bad-model",
                    str(out), str(TMP / f"t{trial}-badmodel-logs")],
                   env=env, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=300)
    return json.loads(out.read_text()) if out.exists() else {"error": "worker produced nothing"}


def u9_2(svc, texts, trial):
    point_logs_at(TMP / f"t{trial}-u2")
    reqs = mixed_batch(svc, texts, f"t{trial}u2", valid_other=0, refused=2)
    failures = read_jsonl(config.FAILURES_LOG)
    expect = {"refused": (400, "validate", "validation_failure"),
              "limited": (429, "request", "rate_limit")}
    by_rid = Counter(f["run_id"] for f in failures)
    matched = 0
    detail = []
    for r in reqs:
        if r["kind"] not in expect:
            continue
        status, stage, category = expect[r["kind"]]
        recs = [f for f in failures if f["run_id"] == r["rid"]]
        good = (r["status"] == status and by_rid[r["rid"]] == 1 and recs
                and recs[0]["stage"] == stage and recs[0]["category"] == category
                and recs[0]["http_status"] == status and recs[0]["message"])
        matched += bool(good)
        detail.append(f"{r['kind']}:{r['status']}:{'ok' if good else 'WRONG'}")
    extra = len(failures) - 4          # nothing beyond the 4 deliberate failures
    bm = u9_2_bad_model(trial)
    bm_good = (bm.get("status") == 500 and bm.get("records") == 1 and bm.get("stage") == "model_signal"
               and bm.get("category") == "model_unavailable" and bm.get("run_id_matches")
               and bm.get("message"))
    matched += bool(bm_good)
    ok = matched == 5 and extra == 0
    return ok, {"matched": f"{matched}/5", "extra records": extra,
                "model-load failure": bm if not bm_good else "500 / model_signal / model_unavailable",
                "batch": " ".join(detail)}


def u9_3(svc, texts, trial):
    point_logs_at(TMP / f"t{trial}-u3")
    rows = []
    for i in range(20):
        r, client_ms = svc.post("/submit", {"text": texts[i % len(texts)],
                                            "creator_id": f"t{trial}u3-{i}"})
        assert r.status_code == 200, r.status_code
        rec = next(x for x in read_jsonl(config.RUNS_LOG) if x["run_id"] == r.headers["X-Request-ID"])
        stage_sum = sum(s["duration_ms"] for s in rec["stages"])
        rows.append({"gap": client_ms - rec["duration_ms"], "coverage": stage_sum / rec["duration_ms"],
                     "duration": rec["duration_ms"],
                     "inference_share": rec["stages"][0].get("inference_ms", 0) / rec["stages"][0]["duration_ms"]})
    gaps = [row["gap"] for row in rows]
    good_gap = sum(1 for g in gaps if abs(g) <= GAP_LIMIT_MS)
    good_cov = sum(1 for row in rows if row["coverage"] >= STAGE_COVERAGE)
    ok = good_gap == 20 and good_cov == 20
    return ok, {"within 15 ms": f"{good_gap}/20", "stages >= 98%": f"{good_cov}/20",
                "gap ms (min/mean/max)": f"{min(gaps):.2f} / {statistics.mean(gaps):.2f} / {max(gaps):.2f}",
                "min stage coverage": f"{min(r['coverage'] for r in rows):.4f}",
                "model share of model_signal stage (min)": f"{min(r['inference_share'] for r in rows):.3f}"}, \
        [row["duration"] for row in rows]


def u9_4(svc, texts, trial):
    point_logs_at(TMP / f"t{trial}-u4")
    mixed_batch(svc, texts, f"t{trial}u4", valid_other=10, refused=3)
    runs = read_jsonl(config.RUNS_LOG)
    failures = read_jsonl(config.FAILURES_LOG)
    m = svc.get("/metrics")[0].json()
    link_rate = m["link"]["rate_limit_hits"]
    checks = {
        "total requests": (m["requests"]["total"], len(runs), 21),
        "by outcome": (m["requests"]["by_outcome"], dict(Counter(r["outcome"] for r in runs)),
                       {"ok": 16, "client_error": 3, "rate_limited": 2}),
        "rate-limit hits": (link_rate, sum(1 for r in runs if r["http_status"] == 429), 2),
        "total failures": (m["failures"]["total"], len(failures), 5),
        "input tokens": (m["cost"]["input_tokens"], sum(r["usage"]["input_tokens"] for r in runs), None),
        "request p50 ms": (m["latency_ms"]["request"]["p50"],
                           round(statistics.median(r["duration_ms"] for r in runs), 3), None),
    }
    matched = 0
    detail = {}
    for name, (reported, recount, expected) in checks.items():
        same = reported == recount and (expected is None or recount == expected)
        matched += same
        detail[name] = f"reported {reported} | recount {recount}" + ("" if same else "  <-- MISMATCH")
    return matched == 6, {"matched": f"{matched}/6", **detail}


def u9_5(svc, texts, trial):
    # (a) same answers with telemetry on and off
    point_logs_at(TMP / f"t{trial}-u5a")
    same = 0
    for i, text in enumerate(texts[:10]):
        answers = []
        for flag in (True, False):
            config.TELEMETRY_ENABLED = flag
            r, _ = svc.post("/submit", {"text": text, "creator_id": f"t{trial}u5-{i}-{flag}"})
            body = r.json()
            body.pop("content_id", None)
            answers.append((r.status_code, body))
        same += answers[0] == answers[1] and set(answers[0][1]) | {"content_id"} == RESPONSE_KEYS
    config.TELEMETRY_ENABLED = True

    # (b) telemetry log files unwritable: make them directories
    folder = point_logs_at(TMP / f"t{trial}-u5b")
    config.RUNS_LOG = folder / "runs_is_a_dir"
    config.FAILURES_LOG = folder / "failures_is_a_dir"
    config.RUNS_LOG.mkdir()
    config.FAILURES_LOG.mkdir()
    good = 0
    for i in range(10):
        r, _ = svc.post("/submit", {"text": texts[i], "creator_id": f"t{trial}u5b-{i}"})
        good += r.status_code == 200 and set(r.json()) == RESPONSE_KEYS
    r, _ = svc.post("/submit", {"text": "   ", "creator_id": f"t{trial}u5b-blank"})
    good += r.status_code == 400
    ok = same == 10 and good == 11
    return ok, {"same answers on/off": f"{same}/10", "correct with telemetry files unwritable": f"{good}/11"}


# ── worker: model-load failure in a fresh process ────────────────────────────

def worker_bad_model(out_path, log_dir):
    point_logs_at(Path(log_dir))
    import app as appmod
    appmod.app.testing = False
    client = appmod.app.test_client()
    text = " ".join(["The committee reviewed the proposal carefully."] * 12)
    r = client.post("/submit", json={"text": text, "creator_id": "bad-model"})
    failures = read_jsonl(config.FAILURES_LOG)
    f = failures[0] if failures else {}
    Path(out_path).write_text(json.dumps({
        "status": r.status_code, "records": len(failures), "stage": f.get("stage"),
        "category": f.get("category"), "error_type": f.get("error_type"),
        "run_id_matches": f.get("run_id") == r.headers.get("X-Request-ID"),
        "message": bool(f.get("message")), "model": config.DETECTOR_MODEL}))


# ── main ─────────────────────────────────────────────────────────────────────

def dist(values):
    s = sorted(values)

    def pct(p):
        k = (len(s) - 1) * p / 100
        lo, hi = int(k), min(int(k) + 1, len(s) - 1)
        return s[lo] + (s[hi] - s[lo]) * (k - lo)
    return (f"n={len(s)}  mean={statistics.mean(s):.1f}  p50={pct(50):.1f}  "
            f"p95={pct(95):.1f}  p99={pct(99):.1f}  max={s[-1]:.1f}")


def main():
    if "--worker-bad-model" in sys.argv:
        i = sys.argv.index("--worker-bad-model")
        return worker_bad_model(sys.argv[i + 1], sys.argv[i + 2])

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--trials", type=int, default=3)
    args = parser.parse_args()

    texts = human_texts()
    svc = Service()
    print("Warming the model (one request, not counted)...")
    point_logs_at(TMP / "warmup")
    svc.post("/submit", {"text": texts[0], "creator_id": "warmup"})

    criteria = [
        ("U9-1", "every request traced: 20/20 headers, 20/20 run records, 15/15 audit entries", u9_1),
        ("U9-2", "5/5 failures leave exactly one correct record", u9_2),
        ("U9-3", "20/20 requests: recorded time within 15 ms of client clock, stages >= 98%", u9_3),
        ("U9-4", "6/6 /metrics figures equal a recount of the raw logs", u9_4),
        ("U9-5", "10/10 same answers on/off; 11/11 correct with telemetry unwritable", u9_5),
    ]
    results = {cid: [] for cid, _, _ in criteria}
    durations = []
    for trial in range(1, args.trials + 1):
        print(f"\nTrial {trial}")
        for cid, _, fn in criteria:
            out = fn(svc, texts, trial)
            ok, detail = out[0], out[1]
            if len(out) > 2:
                durations += out[2]
            results[cid].append({"trial": trial, "pass": ok, "detail": detail})
            print(f"  {cid}: {'PASS' if ok else 'FAIL'}  {detail if not ok else ''}")

    when = datetime.now().strftime("%Y-%m-%d_%H%M")
    lines = [f"# Unit 9 criteria run — {when}", "",
             f"{args.trials} trial(s), against a private copy of the service on {platform.platform()}, "
             f"Python {platform.python_version()}. Logs went to a temp folder, not `logs/`.", "",
             "| Criterion | Target | " + " | ".join(f"Trial {t}" for t in range(1, args.trials + 1)) + " | Verdict |",
             "|---|---|" + "---|" * args.trials + "---|"]
    for cid, target, _ in criteria:
        marks = [("PASS" if r["pass"] else "FAIL") for r in results[cid]]
        lines.append(f"| {cid} | {target} | " + " | ".join(marks) + " | "
                     + ("**MET**" if all(r["pass"] for r in results[cid]) else "**MISSED**") + " |")
    lines += ["", "## Numbers behind each cell", ""]
    for cid, target, _ in criteria:
        lines.append(f"### {cid} — {target}")
        for r in results[cid]:
            lines.append(f"- Trial {r['trial']} ({'PASS' if r['pass'] else 'FAIL'}):")
            for k, v in r["detail"].items():
                lines.append(f"  - {k}: {v}")
        lines.append("")
    if durations:
        lines += ["## Latency distribution (U9-3 requests, recorded `duration_ms`)", "",
                  f"{dist(durations)}", ""]
    report = "\n".join(lines) + "\n"
    config.RESULTS_DIR.mkdir(exist_ok=True)
    out = config.RESULTS_DIR / f"unit9_criteria_{when}.md"
    out.write_text(report, encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("\n" + report)
    print(f"Written to {out}")
    sys.exit(0 if all(r["pass"] for rs in results.values() for r in rs) else 1)


if __name__ == "__main__":
    main()
