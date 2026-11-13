#!/usr/bin/env python3
"""
Checks for the telemetry layer. Runs without the GPT-2 model (the detector is
stubbed) and writes to a temp directory, never to logs/.

    .venv/bin/python test_telemetry.py
"""

import json
import tempfile
import unittest
from pathlib import Path

import config

_tmp = Path(tempfile.mkdtemp())
config.LOG_DIR = _tmp
config.AUDIT_LOG = _tmp / "audit.jsonl"
config.RUNS_LOG = _tmp / "runs.jsonl"
config.FAILURES_LOG = _tmp / "failures.jsonl"
config.CLIENT_LINK_LOG = _tmp / "client_link.jsonl"
config.COMPUTE_USD_PER_HOUR = 36.0   # $0.01 per second of model time

import app as appmod  # noqa: E402
import detector  # noqa: E402
import metrics  # noqa: E402
import telemetry  # noqa: E402

TEXT = " ".join(["The committee reviewed the proposal carefully."] * 12)


def fake_model_signal(text):
    telemetry.record_inference("gpt2", input_tokens=100, forward_s=0.5,
                               tokenize_s=0.01, load_s=0.0)
    return 0.6


class Telemetry(unittest.TestCase):
    def setUp(self):
        for p in (config.AUDIT_LOG, config.RUNS_LOG, config.FAILURES_LOG,
                  config.CLIENT_LINK_LOG):
            p.unlink(missing_ok=True)
        self.client = appmod.app.test_client()
        self._orig = detector.model_signal
        detector.model_signal = fake_model_signal

    def tearDown(self):
        detector.model_signal = self._orig

    def submit(self, body, **kw):
        return self.client.post("/submit", json=body, **kw)

    def test_response_unchanged_and_run_id_ties_records(self):
        r = self.submit({"text": TEXT, "creator_id": "t1"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.json), {"content_id", "guess", "confidence",
                                       "label", "model_score", "style_score"})
        rid = r.headers["X-Request-ID"]
        runs = telemetry.read_records(config.RUNS_LOG)
        self.assertEqual([x["run_id"] for x in runs], [rid])
        self.assertEqual([e["run_id"] for e in appmod.audit.read_entries()], [rid])
        self.assertEqual(runs[0]["context"]["content_id"], r.json["content_id"])

    def test_stages_inference_and_cost(self):
        self.submit({"text": TEXT, "creator_id": "t1"})
        run = telemetry.read_records(config.RUNS_LOG)[0]
        names = [s["name"] for s in run["stages"]]
        self.assertEqual(names, ["model_signal", "style_signal", "combine",
                                 "label", "audit_write"])
        ms = run["stages"][0]
        self.assertEqual(ms["inference_ms"], 500.0)
        self.assertAlmostEqual(ms["inference_ms"] + ms["overhead_ms"], ms["duration_ms"], 2)
        self.assertEqual(run["usage"]["input_tokens"], 100)
        self.assertAlmostEqual(run["cost"]["usd"], 0.005, places=6)  # 0.5s * $36/h
        self.assertEqual(run["outcome"], "ok")

    def test_input_metadata_without_text_and_compute_seconds(self):
        import hashlib
        self.submit({"text": TEXT, "creator_id": "t1"})
        run = telemetry.read_records(config.RUNS_LOG)[0]
        self.assertEqual(run["input"], {
            "chars": len(TEXT), "words": len(TEXT.split()),
            "sha256_16": hashlib.sha256(TEXT.encode()).hexdigest()[:16]})
        self.assertNotIn(TEXT[:30], json.dumps(run))       # the text itself is never stored
        c = run["cost"]["compute_seconds"]
        self.assertEqual(c["inference"], 0.5)
        self.assertGreater(c["wall"], 0)
        self.assertGreaterEqual(c["cpu"], 0)
        self.assertEqual(run["cost"]["usd"], run["cost"]["usd"])  # priced figure still present
        m = metrics.compute()["cost"]["compute_seconds"]
        self.assertEqual(m["total_inference"], 0.5)

    def test_metrics_tolerate_records_without_compute_seconds(self):
        old = {"record_type": "run", "run_id": "x", "started_at": telemetry._now(),
               "route": "/submit", "outcome": "ok", "http_status": 200, "duration_ms": 5,
               "stages": [], "inference": [], "usage": {"input_tokens": 10},
               "cost": {"usd": 0.0}}
        telemetry.write_record(config.RUNS_LOG, old)
        m = metrics.compute()
        self.assertEqual(m["cost"]["compute_seconds"]["total_wall"], 0)

    def test_validation_failure_record(self):
        r = self.submit({"text": "   ", "creator_id": "t1"})
        self.assertEqual(r.status_code, 400)
        f = telemetry.read_records(config.FAILURES_LOG)[0]
        self.assertEqual((f["category"], f["stage"], f["http_status"]),
                         (telemetry.VALIDATION, "validate", 400))
        self.assertEqual(f["message"], "invalid_text")
        self.assertEqual(f["run_id"], r.headers["X-Request-ID"])

    def test_rate_limit_is_recorded_and_still_429(self):
        if not config.RATE_LIMITING_ENABLED:
            self.skipTest("rate limiting off")
        codes = [self.submit({"text": TEXT, "creator_id": "flood"}).status_code
                 for _ in range(config.RATE_LIMIT_PER_MINUTE + 2)]
        self.assertEqual(codes.count(429), 2)
        cats = [f["category"] for f in telemetry.read_records(config.FAILURES_LOG)]
        self.assertEqual(cats.count(telemetry.RATE_LIMIT), 2)
        self.assertEqual(metrics.compute()["link"]["rate_limit_hits"], 2)

    def test_exception_is_classified_and_still_500(self):
        def boom(text):
            raise detector.DetectorUnavailable("no model")
        detector.model_signal = boom
        r = self.submit({"text": TEXT, "creator_id": "t2"})
        self.assertEqual(r.status_code, 500)
        f = telemetry.read_records(config.FAILURES_LOG)
        self.assertEqual(len(f), 1)
        self.assertEqual((f[0]["category"], f[0]["stage"], f[0]["error_type"]),
                         (telemetry.MODEL_UNAVAILABLE, "model_signal", "DetectorUnavailable"))
        run = telemetry.read_records(config.RUNS_LOG)[0]
        self.assertEqual(run["outcome"], "server_error")

    def test_telemetry_endpoints_and_metrics(self):
        self.submit({"text": TEXT, "creator_id": "t3"})
        self.submit({"text": "", "creator_id": "t3"})
        m = self.client.get("/metrics").json
        self.assertEqual(m["requests"]["total"], 2)
        self.assertEqual(m["requests"]["error_rate"], 0.0)
        self.assertEqual(m["failures"]["by_category"], {"validation_failure": 1})
        self.assertEqual(m["latency_ms"]["model_inference"]["p50"], 500.0)
        self.assertEqual(m["link"]["status_codes"], {"200": 1, "400": 1})
        # reading telemetry must not create telemetry
        self.client.get("/runs")
        self.client.get("/failures")
        self.assertEqual(len(telemetry.read_records(config.RUNS_LOG)), 2)
        rid = telemetry.read_records(config.RUNS_LOG)[0]["run_id"]
        one = self.client.get(f"/runs?run_id={rid}").json
        self.assertEqual(len(one["runs"]), 1)
        self.assertEqual(len(one["audit"]), 1)

    def test_other_routes_still_work(self):
        self.assertEqual(self.client.post("/ping", json={"message": "hi"}).json["you_sent"], "hi")
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/log").status_code, 200)

    def test_write_failure_never_breaks_a_request(self):
        (_tmp / "blocker").write_text("")
        config.RUNS_LOG = _tmp / "blocker" / "x.jsonl"   # parent is a file
        try:
            self.assertEqual(self.submit({"text": TEXT, "creator_id": "t4"}).status_code, 200)
        finally:
            config.RUNS_LOG = _tmp / "runs.jsonl"

    def test_telemetry_off_switch(self):
        config.TELEMETRY_ENABLED = False
        try:
            r = self.submit({"text": TEXT, "creator_id": "t5"})
            self.assertEqual(r.status_code, 200)
            self.assertNotIn("X-Request-ID", r.headers)
            self.assertFalse(config.RUNS_LOG.exists())
        finally:
            config.TELEMETRY_ENABLED = True

    def test_classify(self):
        import requests
        c = telemetry.classify
        self.assertEqual(c(requests.exceptions.ReadTimeout()), telemetry.TIMEOUT)
        self.assertEqual(c(requests.exceptions.ConnectionError()), telemetry.CONNECTION)
        self.assertEqual(c(json.JSONDecodeError("x", "", 0)), telemetry.BAD_RESPONSE)
        self.assertEqual(c(ValueError("short")), telemetry.VALIDATION)
        self.assertEqual(c(http_status=429), telemetry.RATE_LIMIT)
        self.assertEqual(c(http_status=503), telemetry.UPSTREAM)
        self.assertEqual(c(RuntimeError()), telemetry.INTERNAL)

    def test_percentiles(self):
        self.assertEqual(metrics.percentile([1, 2, 3, 4], 50), 2.5)
        self.assertIsNone(metrics.percentile([], 50))


class LinkClient(unittest.TestCase):
    def setUp(self):
        config.CLIENT_LINK_LOG.unlink(missing_ok=True)

    def test_retry_timeout_and_logging(self):
        import requests
        import link_client

        class R:
            def __init__(self, code, headers=None):
                self.status_code, self.headers = code, headers or {}

        seq = [requests.exceptions.ReadTimeout("slow"),
               R(429, {"Retry-After": "0"}),
               R(200, {"X-Request-ID": "abc"})]

        def fake(method, url, **kw):
            item = seq.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        orig, requests.request = requests.request, fake
        try:
            resp = link_client.request("POST", "http://x/submit", retries=2, backoff=0)
        finally:
            requests.request = orig
        self.assertEqual(resp.status_code, 200)
        recs = telemetry.read_records(config.CLIENT_LINK_LOG)
        self.assertEqual([r["outcome"] for r in recs], ["timeout", "http_error", "ok"])
        self.assertEqual(recs[-1]["request_id"], "abc")
        link = metrics.compute()["link"]["client"]
        self.assertEqual((link["attempts"], link["retries"], link["timeouts"], link["rate_limited"]),
                         (3, 2, 1, 1))

    def test_default_is_no_retry_and_same_exception(self):
        import requests
        import link_client

        def fake(method, url, **kw):
            raise requests.exceptions.ConnectionError("down")

        orig, requests.request = requests.request, fake
        try:
            with self.assertRaises(requests.exceptions.ConnectionError):
                link_client.request("GET", "http://x/health")
        finally:
            requests.request = orig


if __name__ == "__main__":
    unittest.main(verbosity=2)
