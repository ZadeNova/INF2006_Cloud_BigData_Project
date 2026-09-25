# Scalability / resilience / recovery test

- **Objective:** TODO
- **Setup:** TODO
- **Command/steps:** TODO
- **Expected result:** TODO
- **Actual result:** TODO
- **Date:** TODO
- **Artefact path:** TODO

Local foundation evidence only (12 September 2026): [DB outage/readiness recovery and preserved migration metadata after container recreation](../docs/reviews/foundation-batch-4.md). No AWS scaling, cross-instance authenticated session/cart or interrupted-checkout recovery test has run.


## Phase 6 local scope — 25–26 September 2026

[Local release verification](../docs/reviews/ml-local-release-readiness.md) includes existing PostgreSQL concurrency/recovery regressions and a new real reader/loader race ensuring a segment summary and sample agree during replacement. No supported Locust/load-smoke workload exists in the repository, so load, AWS capacity/Auto Scaling and deployed recovery remain unrun. The planned signature demos in [testing](../docs/TESTING.md#signature-evidence-demos) still require implementation and cloud execution; ordinary authenticated HTTP checks are not a load benchmark.
