"""
Operational metrics: aggregate the raw telemetry records.

    python metrics.py                 # report over everything recorded
    python metrics.py --since 3600    # only the last hour
    python metrics.py --json          # the same numbers, machine-readable

The service serves the same numbers at GET /metrics (add ?since=<seconds>).
Nothing here is stored: it is recomputed from logs/runs.jsonl,
logs/failures.jsonl and logs/client_link.jsonl on every call.
"""

import argparse
import json
import math
from collections import Counter
from datetime import datetime, timedelta, timezone

import config
import telemetry


def percentile(values: list[float], p: float) -> float | None:
    """Linear-interpolated percentile, p in 0..100. None for no data."""
    if not values:
        return None
    ordered = sorted(values)
    k = (len(ordered) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo), 3)


def distribution(values: list[float]) -> dict:
    return {
        "count": len(values),
        "mean": round(sum(values) / len(values), 3) if values else None,
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "max": round(max(values), 3) if values else None,
    }


def _after(records: list[dict], key: str, since_seconds: float | None) -> list[dict]:
    if not since_seconds:
        return records
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=since_seconds)).isoformat()
    # ISO-8601 UTC strings sort chronologically.
    return [r for r in records if r.get(key, "") >= cutoff]


def compute(since_seconds: float | None = None) -> dict:
    runs = _after(telemetry.read_records(config.RUNS_LOG), "started_at", since_seconds)
    failures = _after(telemetry.read_records(config.FAILURES_LOG), "timestamp", since_seconds)
    attempts = _after(telemetry.read_records(config.CLIENT_LINK_LOG), "timestamp", since_seconds)

    total = len(runs)
    outcomes = Counter(r["outcome"] for r in runs)
    # Client mistakes and rate limits are the service working as designed; only
    # 5xx counts against availability.
    server_errors = outcomes.get("server_error", 0) + outcomes.get("error", 0)

    # ── per-stage latency, with model time split from the rest ──
    stage_ms, inference_ms, overhead_ms = {}, [], []
    for r in runs:
        for s in r.get("stages", []):
            stage_ms.setdefault(s["name"], []).append(s["duration_ms"])
            if "inference_ms" in s:
                inference_ms.append(s["inference_ms"])
                overhead_ms.append(s["overhead_ms"])
    cold = [i["load_ms"] for r in runs for i in r.get("inference", []) if i.get("cold_start")]

    by_route = {}
    for route in sorted({r["route"] for r in runs}):
        rs = [r for r in runs if r["route"] == route]
        by_route[route] = {
            "count": len(rs),
            "errors": sum(1 for r in rs if r["outcome"] in ("server_error", "error")),
            "duration_ms": distribution([r["duration_ms"] for r in rs]),
        }

    # ── cost ──
    cost_usd = sum(r["cost"]["usd"] for r in runs)
    tokens = sum(r["usage"]["input_tokens"] for r in runs)
    scored = [r for r in runs if r["usage"]["input_tokens"]]

    # ── the API link: server side ──
    status_counts = Counter(str(r["http_status"]) for r in runs)
    link = {
        "status_codes": dict(sorted(status_counts.items())),
        "rate_limit_hits": outcomes.get("rate_limited", 0),
        "availability": round(1 - server_errors / total, 4) if total else None,
        "client": None,
    }
    # ── the API link: client side (retries, timeouts) ──
    if attempts:
        by_outcome = Counter(a["outcome"] for a in attempts)
        link["client"] = {
            "attempts": len(attempts),
            "retries": sum(1 for a in attempts if a.get("attempt", 1) > 1),
            "timeouts": by_outcome.get("timeout", 0),
            "connection_errors": by_outcome.get("connection_error", 0),
            "rate_limited": sum(1 for a in attempts if a.get("status") == 429),
            "success_rate": round(by_outcome.get("ok", 0) / len(attempts), 4),
            "latency_ms": distribution([a["latency_ms"] for a in attempts
                                        if a.get("latency_ms") is not None]),
        }

    # Records written before compute_seconds existed simply don't contribute.
    timed = [r["cost"]["compute_seconds"] for r in scored
             if "compute_seconds" in r["cost"]]
    wall = [t["wall"] for t in timed]
    cpu = [t["cpu"] for t in timed]
    infer = [t["inference"] for t in timed]

    return {
        "window_seconds": since_seconds,
        "requests": {
            "total": total,
            "by_outcome": dict(outcomes),
            "error_rate": round(server_errors / total, 4) if total else None,
            "rejected_rate": round(
                (outcomes.get("client_error", 0) + outcomes.get("rate_limited", 0)) / total, 4
            ) if total else None,
        },
        "latency_ms": {
            "request": distribution([r["duration_ms"] for r in runs]),
            "by_route": by_route,
            "by_stage": {name: distribution(v) for name, v in sorted(stage_ms.items())},
            "model_inference": distribution(inference_ms),
            "model_overhead": distribution(overhead_ms),
            "model_cold_load": distribution(cold),
        },
        "cost": {
            "total_usd": round(cost_usd, 8),
            "per_scored_request_usd": round(cost_usd / len(scored), 8) if scored else None,
            "input_tokens": tokens,
            "scored_requests": len(scored),
            "compute_seconds": {
                "total_wall": round(sum(wall), 4),
                "total_inference": round(sum(infer), 4),
                "total_cpu": round(sum(cpu), 4),
                "per_scored_request": {"wall": distribution(wall),
                                       "inference": distribution(infer),
                                       "cpu": distribution(cpu)},
            },
            "note": "0 unless pricing is set in config.PRICING or "
                    "AI201_COMPUTE_USD_PER_HOUR (the detector is a local model).",
        },
        "failures": {
            "total": len(failures),
            "by_category": dict(Counter(f["category"] for f in failures)),
            "by_stage": dict(Counter(f["stage"] for f in failures)),
        },
        "link": link,
    }


def _fmt(d: dict | None) -> str:
    if not d or not d["count"]:
        return "no data"
    return (f"n={d['count']}  mean={d['mean']}  p50={d['p50']}  "
            f"p95={d['p95']}  p99={d['p99']}  max={d['max']}")


def report(m: dict) -> str:
    r, lat, link = m["requests"], m["latency_ms"], m["link"]
    lines = [
        "PROVENANCE GUARD — OPERATIONAL METRICS",
        f"window: {'last ' + str(int(m['window_seconds'])) + 's' if m['window_seconds'] else 'all recorded'}",
        "",
        f"Requests      {r['total']}   by outcome: {r['by_outcome']}",
        f"Error rate    {r['error_rate']}   (5xx / total)    "
        f"rejected rate {r['rejected_rate']}   (4xx + 429 / total)",
        "",
        "Latency (ms)",
        f"  request          {_fmt(lat['request'])}",
    ]
    for name, d in lat["by_stage"].items():
        lines.append(f"  stage {name:<18}{_fmt(d)}")
    lines += [
        f"  model inference  {_fmt(lat['model_inference'])}",
        f"  model overhead   {_fmt(lat['model_overhead'])}   (stage time minus model time)",
        f"  model cold load  {_fmt(lat['model_cold_load'])}",
        "",
        "Cost",
        f"  total ${m['cost']['total_usd']}   input tokens {m['cost']['input_tokens']}   "
        f"scored requests {m['cost']['scored_requests']}",
        f"  compute seconds, per scored request  wall: {_fmt(m['cost']['compute_seconds']['per_scored_request']['wall'])}",
        f"                                       cpu:  {_fmt(m['cost']['compute_seconds']['per_scored_request']['cpu'])}",
        f"  ({m['cost']['note']})",
        "",
        f"Failures      {m['failures']['total']}   by category: {m['failures']['by_category']}",
        f"              by stage: {m['failures']['by_stage']}",
        "",
        "API link",
        f"  status codes {link['status_codes']}   rate-limit hits {link['rate_limit_hits']}   "
        f"availability {link['availability']}",
    ]
    if link["client"]:
        c = link["client"]
        lines.append(f"  client side: {c['attempts']} attempts, {c['retries']} retries, "
                     f"{c['timeouts']} timeouts, {c['connection_errors']} connection errors, "
                     f"success {c['success_rate']}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Aggregate telemetry records.")
    parser.add_argument("--since", type=float, default=None,
                        help="only records from the last N seconds")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    m = compute(args.since)
    print(json.dumps(m, indent=2) if args.json else report(m))


if __name__ == "__main__":
    main()
