# AI Use Declaration

For each AI tool or external baseline used, record:

| Tool/source | Where used | Purpose | Verification performed | Licence/attribution |
|---|---|---|---|---|
| TODO | TODO | TODO | TODO | TODO |

## Notes
TODO: describe any open-source baseline or AI-assisted code the team started from, and the team's substantive modifications and decisions on top of it.

## Foundation verification and attribution

| Tool/source | Where used | Purpose | Verification performed | Licence/attribution |
|---|---|---|---|---|
| OpenAI Codex; independent Astra Medium reviewer agents | Local backend foundation batches 1-4, src/, tests/, related docs | Scaffolding, configuration, schema/migrations, health, test and documentation assistance | Dated foundation evidence and independent review logs under evidence/ and docs/reviews/; follow-up workflows explicitly unverified | AI-assisted work; review records distinguish coordinator-run tests from reviewer inspection |
| Django and Python official documentation | Runtime/framework selection and framework patterns | Supported Django 5.2 LTS / Python 3.13 baseline | Exact installed versions and dependency compatibility recorded in foundation evidence | https://docs.djangoproject.com/en/5.2/releases/5.2/ ; https://www.python.org/downloads/ |
| PostgreSQL official documentation and Docker Official Images | Local PostgreSQL and Python containers | Reproducible local runtime | Image digests pinned; PostgreSQL constraints and migrations exercised | https://www.postgresql.org/docs/17/ ; upstream software/image licences apply |

No external application template or another course's implementation was copied. Source dataset provenance and any frontend imagery/font attribution remain separate future records. This entry does not claim human team members performed the agent-run checks.

## ML quality and reproducible evaluation (25 September 2026)

OpenAI Codex coordinated Phase 3 on `erfan/analytics`, with explicitly assigned `gpt-6-astra` / `low` implementation and a separate `gpt-6-astra` / `medium` read-only review gate. Assistance covers offline segmentation, focused tests, analytics CI, aggregate evaluation and supporting documentation. The coordinator owns Git, tracker and review records. Actual verification, review rounds and limitations are recorded in [ml-quality-evaluation](docs/reviews/ml-quality-evaluation.md); assignment of a reviewer alone is not a completed review. Source data remains the attributed synthetic Analytics Engineering release; no teammate-owned dataset was replaced or repriced. These are agent contributions, not claimed human test execution.

## ML batch handoff and recovery (25 September 2026)

OpenAI Codex coordinates Phase 4 on `erfan/analytics`, with explicitly assigned `gpt-6-astra` / `low` implementation and separate fresh-context `gpt-6-astra` / `medium` read-only review. Assistance covers explicit batch provenance, export/import recovery, focused checks and operational documentation. The coordinator owns Git, tracker and review records; subagents do not stage, commit or push. Actual review status, executed checks and limitations are recorded in [ml-batch-handoff](docs/reviews/ml-batch-handoff.md). These are agent contributions, not claimed human test execution; source dataset attribution remains unchanged.

## Production runtime and AWS security preparation (25 September 2026)

OpenAI Codex coordinates Phase 5 on `erfan/analytics`, with explicitly assigned `gpt-6-astra` / `low` implementation and separate fresh-context `gpt-6-astra` / `medium` read-only review. Assistance covers runtime TLS, bootstrap privilege safety, startup secret configuration, packaging, focused verification and the infrastructure handoff. The coordinator owns Git, tracker and review records; subagents do not stage, commit or push. [Runtime review](docs/reviews/runtime-aws-security.md) records actual checks, findings and limitations. This attribution does not claim deployment, verified AWS permissions or human execution of agent-run tests.


## Local integration and ML display (25–26 September 2026)

OpenAI Codex coordinates Phase 6 on `erfan/analytics`, with explicit `gpt-6-astra` / `low` backend implementation and isolated verification, `gpt-5.6-luna` / `max` frontend implementation/visual verification, and a separate fresh-context `gpt-6-astra` / `medium` read-only review gate. Assistance covers truthful ML display, coherent segment reads, local integration checks and release/handoff documentation. Coordinator owns Git, evidence and review records. [Phase 6 review](docs/reviews/ml-local-release-readiness.md) records actual checks, reviewer outcome and limitations; assignments alone are not completed checks. No human team execution, hosted CI or AWS deployment is inferred from agent-run local tests.
