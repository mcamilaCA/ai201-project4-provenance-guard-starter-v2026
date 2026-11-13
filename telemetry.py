"""
Telemetry: one execution record per request, one failure record per error.

    run_id ─┬─ runs.jsonl      what ran, stage timings, model time, tokens, cost
            ├─ failures.jsonl  what broke: stage, type, message, category
            └─ audit.jsonl     the decision itself (run_id is added automatically)

Design rules, because this sits in the request path:

  * It never changes what a route returns, and it never raises into one. A
    failed write is reported once on stderr and then ignored.
  * Code that is being timed doesn't need to know about Flask. `stage()` and
    `record_inference()` are no-ops when no run is active, so detector.py and
    the scripts that import it behave as before.
  * Raw text is never recorded. A run holds timings, counts and ids.

Record schema (`schema_version` 1)

  run:      run_id, started_at, route, method, http_status, outcome,
            duration_ms, input{chars, words, sha256_16}, stages[{name, status, duration_ms,
            inference_ms?, overhead_ms?}], inference[{model, input_tokens,
            tokenize_ms, forward_ms, load_ms, cold_start}], usage, cost,
            failure_categories, context
  failure:  run_id, timestamp, stage, category, error_type, message,
            http_status, context
"""

import contextvars
import hashlib
import json
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

import config

SCHEMA_VERSION = 1

# Failure categories. Anything that doesn't fit lands in internal_error.
TIMEOUT = "timeout"
RATE_LIMIT = "rate_limit"
BAD_RESPONSE = "bad_response"
VALIDATION = "validation_failure"
MODEL_UNAVAILABLE = "model_unavailable"
UPSTREAM = "upstream_unavailable"
CONNECTION = "connection_error"
INTERNAL = "internal_error"

_current = contextvars.ContextVar("provenance_run", default=None)
_write_lock = threading.Lock()
_warned = set()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _ms(seconds: float) -> float:
    return round(seconds * 1000, 3)


def write_record(path, record: dict) -> None:
    """Append one JSON line. Never raises."""
    if not config.TELEMETRY_ENABLED:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _write_lock:
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception as exc:  # noqa: BLE001
        if str(path) not in _warned:
            _warned.add(str(path))
            print(f"[telemetry] couldn't write {path}: {exc}", file=sys.stderr)


def read_records(path) -> list[dict]:
    """Read a telemetry file back, oldest first. Bad lines are skipped."""
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


# ── Classifying errors ───────────────────────────────────────────────────────

def classify(exc: BaseException | None = None, http_status: int | None = None) -> str:
    """
    Map an exception (or, failing that, an HTTP status) to a failure category.

    Exceptions are matched by class name where the class lives in a module
    this file shouldn't import (requests, detector).
    """
    if exc is not None:
        names = {c.__name__ for c in type(exc).__mro__}
        if isinstance(exc, TimeoutError) or any("Timeout" in n for n in names):
            return TIMEOUT
        if "DetectorUnavailable" in names:
            return MODEL_UNAVAILABLE
        if "ConnectionError" in names or isinstance(exc, ConnectionError):
            return CONNECTION
        if isinstance(exc, json.JSONDecodeError):
            return BAD_RESPONSE
        if isinstance(exc, ValueError):
            return VALIDATION
    if http_status is not None:
        if http_status == 429:
            return RATE_LIMIT
        if http_status in (408, 504):
            return TIMEOUT
        if http_status in (502, 503):
            return UPSTREAM
        if 400 <= http_status < 500:
            return VALIDATION
    return INTERNAL


def outcome_for(http_status: int | None) -> str:
    if http_status is None:
        return "error"
    if http_status == 429:
        return "rate_limited"
    if http_status >= 500:
        return "server_error"
    if http_status >= 400:
        return "client_error"
    return "ok"


# ── Cost ─────────────────────────────────────────────────────────────────────

def compute_cost(model: str, input_tokens: int, output_tokens: int,
                 inference_seconds: float) -> dict:
    """
    Turn usage into dollars: token pricing plus an optional machine rate.
    See config.PRICING; with the shipped settings this is 0.0 since the current model is free.
    """
    price = config.PRICING.get(model, config.PRICING["default"])
    token_usd = (input_tokens * price["input_per_mtok"]
                 + output_tokens * price["output_per_mtok"]) / 1_000_000
    compute_usd = inference_seconds / 3600 * config.COMPUTE_USD_PER_HOUR
    return {
        "usd": round(token_usd + compute_usd, 10),
        "token_usd": round(token_usd, 10),
        "compute_usd": round(compute_usd, 10),
        "priced_model": model if model in config.PRICING else "default",
    }


# ── A run ────────────────────────────────────────────────────────────────────

class Run:
    def __init__(self, route: str, method: str = "", run_id: str | None = None):
        self.run_id = run_id or uuid.uuid4().hex
        self.route = route
        self.method = method
        self.started_at = _now()
        self._t0 = time.perf_counter()
        self._cpu0 = time.process_time()
        self.input: dict | None = None
        self.stages: list[dict] = []
        self.inference: list[dict] = []
        self.failures: list[dict] = []
        self.context: dict = {}

    def add_failure(self, stage: str, exc: BaseException | None = None,
                    category: str | None = None, message: str | None = None,
                    http_status: int | None = None, **context) -> dict:
        record = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "failure",
            "run_id": self.run_id,
            "timestamp": _now(),
            "route": self.route,
            "stage": stage,
            "category": category or classify(exc, http_status),
            "error_type": type(exc).__name__ if exc is not None else None,
            "message": (message if message is not None else str(exc))[:300],
            "http_status": http_status,
            "context": context,
        }
        self.failures.append(record)
        return record

    def finish(self, http_status: int | None) -> dict:
        """Close the run, write its records, and return the run record."""
        duration = time.perf_counter() - self._t0
        cpu_seconds = time.process_time() - self._cpu0

        # A 4xx/5xx with no exception behind it (a refused input, a 429) is
        # still a failure worth a record.
        if not self.failures and (http_status is None or http_status >= 400):
            self.add_failure(
                stage=self.context.get("failed_stage", "request"),
                category=None, http_status=http_status,
                message=str(self.context.get("error_code", f"HTTP {http_status}")),
            )
        for f in self.failures:
            if f["http_status"] is None:
                f["http_status"] = http_status
            write_record(config.FAILURES_LOG, f)

        model = self.inference[-1]["model"] if self.inference else None
        in_tokens = sum(i["input_tokens"] for i in self.inference)
        forward_s = sum(i["forward_ms"] for i in self.inference) / 1000
        record = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "run",
            "run_id": self.run_id,
            "started_at": self.started_at,
            "route": self.route,
            "method": self.method,
            "http_status": http_status,
            "outcome": outcome_for(http_status),
            "duration_ms": _ms(duration),
            "input": self.input,
            "stages": self.stages,
            "inference": self.inference,
            "usage": {"model": model, "input_tokens": in_tokens,
                      "output_tokens": 0, "source": "local" if model else None},
            "cost": {
                **(compute_cost(model, in_tokens, 0, forward_s) if model else
                   {"usd": 0.0, "token_usd": 0.0, "compute_usd": 0.0,
                    "priced_model": None}),
                # Measured, not priced: seconds of compute this request used.
                #   wall      the whole request, start to finish
                #   inference the model's forward pass alone
                #   cpu       CPU time the process burned meanwhile (all
                #             threads; includes other requests running at the
                #             same moment, so it is exact for a single caller)
                "compute_seconds": {
                    "wall": round(duration, 6),
                    "inference": round(forward_s, 6),
                    "cpu": round(cpu_seconds, 6),
                },
            },
            "failure_categories": sorted({f["category"] for f in self.failures}),
            "context": {k: v for k, v in self.context.items()
                        if k in ("content_id", "label")},
        }
        write_record(config.RUNS_LOG, record)
        return record


def current_run() -> Run | None:
    return _current.get()


def current_run_id() -> str | None:
    run = _current.get()
    return run.run_id if run else None


@contextmanager
def run(route: str, method: str = "", run_id: str | None = None):
    """
    Use outside Flask (scripts, tests):

        with telemetry.run("batch") as r:
            ...
    """
    r = Run(route, method, run_id)
    token = _current.set(r)
    status = 200
    try:
        yield r
    except Exception as exc:
        if not r.failures:
            r.add_failure("run", exc)
        status = 500
        raise
    finally:
        _current.reset(token)
        r.finish(status)


@contextmanager
def stage(name: str):
    """
    Time one stage of the pipeline. Re-raises whatever goes wrong inside it,
    after recording the failure against this stage.
    """
    r = _current.get()
    if r is None:
        yield
        return
    t0 = time.perf_counter()
    inf_start = len(r.inference)
    status = "ok"
    try:
        yield
    except Exception as exc:
        status = "error"
        r.add_failure(name, exc)
        r.context["failed_stage"] = name
        raise
    finally:
        entry = {"name": name, "status": status,
                 "duration_ms": _ms(time.perf_counter() - t0)}
        new = r.inference[inf_start:]
        if new:
            # Model time vs everything else the stage did (tokenising, model
            # loading, glue). This is the split that tells you whether a slow
            # stage is slow because of the model or because of us.
            inference_ms = round(sum(i["forward_ms"] for i in new), 3)
            entry["inference_ms"] = inference_ms
            entry["overhead_ms"] = round(entry["duration_ms"] - inference_ms, 3)
        r.stages.append(entry)


def record_input(text) -> None:
    """
    Note what was submitted without storing it: length and a short SHA-256
    prefix. The hash lets you spot the same text arriving twice; it can't be
    turned back into the text. No-op outside a run or for non-strings.
    """
    r = _current.get()
    if r is None or not isinstance(text, str):
        return
    r.input = {
        "chars": len(text),
        "words": len(text.split()),
        "sha256_16": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
    }


def mark_stage(name: str) -> None:
    """Say which stage a refusal (no exception) belongs to. No-op outside a run."""
    r = _current.get()
    if r is not None:
        r.context["failed_stage"] = name


def record_inference(model: str, input_tokens: int, forward_s: float,
                     tokenize_s: float = 0.0, load_s: float = 0.0,
                     cold_start: bool = False) -> None:
    """Called by the code that runs the model. No-op outside a run."""
    r = _current.get()
    if r is None:
        return
    r.inference.append({
        "model": model,
        "input_tokens": int(input_tokens),
        "tokenize_ms": _ms(tokenize_s),
        "forward_ms": _ms(forward_s),
        "load_ms": _ms(load_s),
        "cold_start": cold_start,
    })


# ── Flask wiring ─────────────────────────────────────────────────────────────

# Reading telemetry shouldn't generate telemetry.
UNTRACKED_PATHS = ("/metrics", "/runs", "/failures")


def init_app(app) -> None:
    """
    Give every request a run_id and an execution record.

    Call this BEFORE anything else registers a before_request hook (the rate
    limiter does), so a request the limiter turns away still has a run.
    """
    from flask import g, request

    @app.before_request
    def _telemetry_begin():
        g.telemetry_run = None
        if not config.TELEMETRY_ENABLED or request.path.startswith(UNTRACKED_PATHS):
            return
        rule = request.url_rule.rule if request.url_rule else "<unmatched>"
        r = Run(route=rule, method=request.method,
                run_id=request.headers.get("X-Request-ID") or None)
        g.telemetry_run = r
        _current.set(r)

    @app.after_request
    def _telemetry_response(response):
        r = getattr(g, "telemetry_run", None)
        if r is not None:
            g.telemetry_status = response.status_code
            response.headers["X-Request-ID"] = r.run_id
            try:
                if (response.mimetype == "application/json"
                        and not response.direct_passthrough
                        and (response.content_length or 0) < 65536):
                    body = json.loads(response.get_data())
                    if isinstance(body, dict):
                        for key in ("content_id", "label"):
                            if isinstance(body.get(key), str):
                                r.context[key] = body[key]
                        if isinstance(body.get("error"), str):
                            r.context["error_code"] = body["error"]
            except Exception:  # noqa: BLE001
                pass
        return response

    @app.teardown_request
    def _telemetry_end(exc):
        r = getattr(g, "telemetry_run", None)
        if r is None:
            return
        try:
            status = getattr(g, "telemetry_status", None)
            if status is None and exc is not None:
                status = 500
                if not r.failures:
                    r.add_failure("request", exc)
            r.finish(status)
        except Exception as err:  # noqa: BLE001
            print(f"[telemetry] couldn't finish run: {err}", file=sys.stderr)
        finally:
            g.telemetry_run = None
            _current.set(None)
