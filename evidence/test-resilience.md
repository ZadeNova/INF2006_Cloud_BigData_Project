# Scalability / resilience / recovery test

**Status:** PLANNED on AWS. The expected results were written on 8 October 2026, before any cloud run. The measurements come from the load harness; the full case tables (objective, setup, command, expected, actual, artefact path) are in [test-performance.md](test-performance.md), and this file is the index the brief's test 4 points to. Procedure: [docs/plans/evidence-session.md](../docs/plans/evidence-session.md).

| Case | What it shows | Expected (fixed beforehand) | Variant A | Variant B | Case table |
|---|---|---|---|---|---|
| RES-03a scale-out | Load step to a second healthy unit, without a person | Alarm a few minutes after the load step; second unit healthy about 3 to 4 minutes later on A, sooner on B (no instance boot); scale-in after the load falls | | | [test-performance.md RES-03a](test-performance.md#res-03a-scale-out-1-to-2-units) |
| RES-03b replacement | One of two units removed under 100 users; time to two healthy again and the error window | Detection about 30 s after the kill; replacement dominated by boot time; a short error burst or none (graceful removal drains first) | | | [test-performance.md RES-03b](test-performance.md#res-03b-replacement-of-a-killed-unit) |
| RES-04 session continuity | Logged-in visitors keep their session and cart when the unit that served them is removed (no stickiness; sessions are in the database) | Visits that span the kill continue without a new login and without an error, apart from requests in flight at the kill | | | Analysed after the session from the RES-03b request log (`requests-*.csv`) |

Both variants use the same harness schedule, the same capacity pins and a graceful removal (ADR-017): A asks the Auto Scaling group to terminate the instance, B stops one task. The replacement test is therefore a planned removal, not a sudden crash; the report says so.

Local foundation evidence only (12 September 2026): [DB outage/readiness recovery and preserved migration metadata after container recreation](../docs/reviews/foundation-batch-4.md). No AWS scaling, cross-instance authenticated session/cart or interrupted-checkout recovery test has run.


## Phase 6 local scope — 25–26 September 2026

[Local release verification](../docs/reviews/ml-local-release-readiness.md) includes existing PostgreSQL concurrency/recovery regressions and a new real reader/loader race ensuring a segment summary and sample agree during replacement. No supported Locust/load-smoke workload exists in the repository, so load, AWS capacity/Auto Scaling and deployed recovery remain unrun. The planned signature demos in [testing](../docs/TESTING.md#signature-evidence-demos) still require implementation and cloud execution; ordinary authenticated HTTP checks are not a load benchmark.
