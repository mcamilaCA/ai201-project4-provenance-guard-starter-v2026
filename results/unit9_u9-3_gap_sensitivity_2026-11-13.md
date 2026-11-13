# U9-3 gap sensitivity — 2026-11-13

Question: what size of untimed delay does each gap limit catch?

Method: a throwaway script (not kept in the repo) ran the same procedure as
`check_unit9.py::u9_3` (20 warm `/submit` requests over real HTTP, client
stopwatch vs recorded `duration_ms`). Before each batch it inserted a
`before_request` hook ahead of the telemetry hook that sleeps for a fixed time
on `/submit`. That time happens before the telemetry clock starts, so it is a
fault the client sees but the recorded duration does not, which is exactly
what the gap check is meant to catch. The hook was removed after each batch.
Raw output:

```
untimed delay injected before telemetry starts:  0 ms | gap min/mean/max  0.99/ 1.12/ 1.58 | caught by 15 ms limit:  0/20 | caught by 5 ms limit:  0/20
untimed delay injected before telemetry starts:  3 ms | gap min/mean/max  4.08/ 4.75/ 4.91 | caught by 15 ms limit:  0/20 | caught by 5 ms limit:  0/20
untimed delay injected before telemetry starts:  8 ms | gap min/mean/max 10.21/11.01/11.25 | caught by 15 ms limit:  0/20 | caught by 5 ms limit: 20/20
untimed delay injected before telemetry starts: 12 ms | gap min/mean/max 13.52/15.85/18.03 | caught by 15 ms limit: 18/20 | caught by 5 ms limit: 20/20
untimed delay injected before telemetry starts: 20 ms | gap min/mean/max 21.49/25.34/28.47 | caught by 15 ms limit: 20/20 | caught by 5 ms limit: 20/20
```
