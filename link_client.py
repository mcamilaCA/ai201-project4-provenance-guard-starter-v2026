"""
Client side of the API link: a drop-in for `requests.request` that records
every attempt (status, latency, retries, timeouts, rate-limit hits) to
logs/client_link.jsonl.

    import link_client
    response = link_client.request("POST", f"{url}/submit", json=body, timeout=90)

Defaults change nothing: no retries, and the same exceptions as `requests`
(Timeout, ConnectionError). Pass `retries=2` to retry timeouts, connection
errors and 429/502/503/504 with exponential backoff (a Retry-After header
wins over the backoff). Each attempt logs the server's X-Request-ID, which
is the run_id of the matching record in runs.jsonl.
"""

import time

import config
import telemetry

RETRY_STATUSES = (429, 502, 503, 504)


def _log(method, url, attempt, outcome, latency_ms, response=None, error=None):
    telemetry.write_record(config.CLIENT_LINK_LOG, {
        "schema_version": telemetry.SCHEMA_VERSION,
        "record_type": "link_attempt",
        "timestamp": telemetry._now(),
        "method": method,
        "url": url,
        "attempt": attempt,
        "outcome": outcome,          # ok | http_error | timeout | connection_error
        "status": response.status_code if response is not None else None,
        "latency_ms": latency_ms,
        "request_id": response.headers.get("X-Request-ID") if response is not None else None,
        "retry_after": response.headers.get("Retry-After") if response is not None else None,
        "error": error,
    })


def request(method, url, retries=0, backoff=1.0, retry_statuses=RETRY_STATUSES, **kwargs):
    import requests

    attempt = 0
    while True:
        attempt += 1
        t0 = time.perf_counter()
        response = None
        try:
            response = requests.request(method, url, **kwargs)
        except requests.exceptions.Timeout as exc:
            _log(method, url, attempt, "timeout", None, error=str(exc)[:200])
            failure = exc
        except requests.exceptions.ConnectionError as exc:
            _log(method, url, attempt, "connection_error", None, error=str(exc)[:200])
            failure = exc
        else:
            latency = round((time.perf_counter() - t0) * 1000, 3)
            ok = response.status_code < 400
            _log(method, url, attempt, "ok" if ok else "http_error", latency, response)
            if ok or response.status_code not in retry_statuses or attempt > retries:
                return response
            failure = None

        if attempt > retries:
            raise failure
        delay = backoff * 2 ** (attempt - 1)
        if response is not None:
            try:
                delay = max(delay, float(response.headers.get("Retry-After", 0)))
            except ValueError:
                pass
        time.sleep(delay)
