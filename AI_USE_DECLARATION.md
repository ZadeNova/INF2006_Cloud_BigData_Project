# AI Use Declaration

Group 21. This file declares every AI tool, external library, asset and dataset the project used,
where it was used, how the team verified the result, and its licence. No external application
template or another course's implementation was copied. The application is AI-assisted code written
by the team, not an open-source baseline; third-party libraries, assets and data are listed below.
The report summarises this declaration in section 8. The dated records in the appendix give
the detail behind the summary.

## AI tools

AI coding assistants were used extensively, as assistants for setting up the cloud infrastructure
and local environment, writing and debugging code, writing tests, drafting documentation and
reviewing changes. The team chose the problem, scope, architecture and dataset, made the design
decisions, and approved a plan before each AI-assisted change.

| Tool/source | Where used | Purpose | Verification performed | Licence/attribution |
|---|---|---|---|---|
| OpenAI Codex, with `gpt-6-astra` and `gpt-5.6-luna` agents | Local Docker and PostgreSQL foundation, dataset import, operator dashboard, ML batch handoff and display, production runtime security (`src/`, `analytics/`, `tests/`, `docs/`) | Setting up the local environment, implementing and debugging backend features, writing tests; separate read-only agents as reviewers | Test suite and focused checks on each change; written review records in [docs/reviews/](docs/reviews/) | AI-assisted work, declared here |
| Claude Code (Claude Opus 5, Opus 5.5, Sonnet 5, Sonnet 5.5) | AWS infrastructure in Terraform for both variants ([src/infrastructure/](src/infrastructure/)), load test harness ([tests/load/](tests/load/README.md)), ML hold-out evaluation and fixes (`analytics/`), catalogue and cart features, evidence records and documentation | Setting up the cloud infrastructure, debugging deployment, configuration and code issues, writing scripts and tests, drafting documentation and reviewing changes | Plans written before each change (`docs/plans/`); Terraform plans reviewed before apply; test suite; deployed tests on AWS recorded in [evidence/](evidence/README.md); database cross-checks | AI-assisted work, declared here; commits made by Claude Code carry a `Co-Authored-By` trailer, but only 22 of the 201 commits do, so the history under-reports AI assistance and this declaration is the record |
| GitHub Copilot | First version of the optional ML customer segmentation workflow (24 September 2026) | Code assistance | Later reviewed and revised in the ML review rounds ([docs/reviews/ml-quality-evaluation.md](docs/reviews/ml-quality-evaluation.md)) | AI-assisted work, declared here |
| Gemini (Google) | Dashboard description during the FUNC-02 browser walkthrough | Structuring a written description of what the dashboard showed | Each value cross-checked against the database (FUNC-02 step 7 in [evidence/test-functional.md](evidence/test-functional.md)) | AI-assisted wording |
| Claude Code and OpenAI Codex agents | The report (Google Doc), including the 9 October audit revisions to sections 2, 6 and 7 | Drafting and revising report text from the evidence records | The two developers (Lim Chee Long and Muhammad Erfan Bin Mohan) checked its numbers and paths against [evidence/](evidence/README.md) and the manifest; all members have read it, and the primary developer gives the final approval | AI-assisted work, declared here |
| Claude Code and OpenAI Codex (`gpt-5.6-luna`) | Storefront redesign in the VoiceBox style, dark mode, motion, 42Factors branding and the pixel "67" mark (`src/templates/`, `src/static/`) | Front-end implementation assistance, led by Jun Keat Lim | Visual and UI checks by the team; frontend tests ([tests/test_frontend.py](tests/test_frontend.py)); FUNC-02 browser walkthrough | AI-assisted work, declared here |
| Chat assistant for planning and advice (tool not recorded) | Architecture, cost and scope discussions before decisions were written down | Advice only | Decisions were then recorded by the team in [docs/decisions/](docs/decisions/) and the scope | AI-assisted advice |

AI output was not accepted as fact; it was accepted only through recorded gates. Backend changes
were reviewed by a separate, read-only reviewer agent against the written contracts, with findings,
fixes and re-reviews logged under [docs/reviews/](docs/reviews/). The last two gates, the backend changes from
`0442665` onward ([shoe-baseline-gate.md](docs/reviews/shoe-baseline-gate.md), verdict CLEAR) and `ec2/` with the
scripts, were closed on 11 October 2026 by the team lead's recorded approval
([docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)). Changes were also checked by the
automated tests, by deployed tests on AWS, by cross-checking results against the database, and by
checking pages in the browser. Recorded command-based results are backed by raw output under
[evidence/raw/](evidence/raw/). Hermann's separate reproduction attempt has no saved raw log,
and the local Gunicorn diagnosis remains an AI-assisted explanation without a logged reproduction;
these limitations are stated in the report, README and contribution reflection rather than presented
as independently verified command results. Where an agent ran a check,
the evidence says so and does not credit a human. The local functional and security test records were run and written by AI agents and then reviewed by the testing members; the FUNC-02 browser walkthrough was carried out by a person.

## Libraries, assets and data

| Source | Where used | Purpose | Verification performed | Licence/attribution |
|---|---|---|---|---|
| Django 5.2, Gunicorn, WhiteNoise, psycopg ([src/requirements.txt](src/requirements.txt)) | Web application | Framework and runtime | Versions pinned; test suite | Django BSD-3-Clause; Gunicorn MIT; WhiteNoise MIT; psycopg LGPL-3.0 |
| PostgreSQL 17 and Docker Official Images | Local runtime and Amazon RDS | Database and containers | Image digests pinned; migrations and constraints exercised | PostgreSQL Licence; upstream image licences |
| HTMX ([src/static/vendor/htmx/](src/static/vendor/htmx/LICENSE.md)) | Storefront and dashboard partials | Partial page updates | Vendored with recorded SHA-256 | Zero-Clause BSD |
| Chart.js ([src/static/vendor/chartjs/](src/static/vendor/chartjs/LICENSE.md)) | Operator dashboard | Charts | Vendored with recorded SHA-256 | MIT |
| model-viewer ([src/static/vendor/model-viewer/](src/static/vendor/model-viewer/LICENSE)) | Product pages | 3D shoe viewer | Vendored | Apache-2.0 |
| 3D shoe models from Sketchfab ([src/static/models/CREDITS.md](src/static/models/CREDITS.md)) | Product pages | Product visuals, compressed with glTF-Transform (below) and cut to a single shoe by the team | Credits recorded per file | Mostly CC BY 4.0; two CC BY-NC 4.0 (non-commercial course use); per-model authors in CREDITS.md |
| Google Fonts (Archivo Black, Space Mono, Work Sans, Inter, Manrope, Pixelify Sans) | Site typography | Fonts | Loaded from Google Fonts | SIL Open Font License 1.1 |
| pandas, NumPy, scikit-learn | [analytics/](analytics/README.md) | Analytics verification and customer segmentation | Versions pinned; tests and reproducible evaluation in [evidence/test-data-ai.md](evidence/test-data-ai.md) | BSD-3-Clause |
| Locust | [tests/load/](tests/load/README.md) | Load generation | Version pinned | MIT |
| Terraform and the AWS provider | [src/infrastructure/](src/infrastructure/) | Infrastructure as code | Plans and applies recorded in [evidence/aws-build-runbook.md](evidence/aws-build-runbook.md) | Terraform BUSL-1.1; AWS provider MPL-2.0 |
| Analytics Engineering, "Ecommerce Sales & Returns Dataset v1.0.0" | [data/](data/README.md), remapped to shoes | Synthetic source data | Checksums in `data/raw/checksums.txt`; import reconciliation | CC BY 4.0; notice in `data/raw/LICENSE.txt` |
| glTF-Transform v4.5.0 | [src/static/models/](src/static/models/CREDITS.md) | Compressing the 3D models (WebP textures, quantized meshes) | The generator string is recorded in the header of each of the 12 files (read on 10 October 2026) and every texture is at most 1024 px. Who ran it, and the exact commands, were not recorded | MIT |
| Phosphor Icons, regular weight | `src/static/img/icons.svg` | Interface icons, vendored as one SVG sprite | Licence notice is in the file header | MIT |
| `DESIGN.md` ("VoiceBox" design reference) | Visual reference for the storefront CSS; included in this package for reference | [VoiceBox v1 by Chef (@chef)](https://designmd.ai/chef/voicebox), introduced by Jun Keat Lim on 23 September 2026 (commit `d147c9d`), replacing the earlier Starbucks-inspired reference | Source recovered on 11 October 2026: all 287 lines of the supplied reference match the upstream download after normalising line endings and surrounding whitespace; project adaptations are recorded in the "As built in this project" section | MIT, as declared on the source page; [licence text and verification details](docs/licenses/voicebox-MIT.txt). Fonts and icons retain their separate licences listed above |

## Team decisions and modifications

The team chose the problem, scope, architecture and dataset, and approved each plan before AI tools
implemented it. Substantive team decisions include: remapping the dataset to a shoe shop with sizes;
building two AWS compute variants from one shared module and choosing ECS Fargate from the measured
results ([ADR-018](docs/decisions/ADR-018-final-architecture-ecs-fargate.md)); which review findings
to fix and which to keep as documented limitations; the storefront redesign and 3D model choice;
and reporting the finding that segments do not predict repurchase on this synthetic data as
measured. Members reviewed AI output, ran the application and checked results against the evidence.

## Appendix: dated AI-use records

The records below were written as the work happened and are kept unchanged.

## Foundation verification and attribution

| Tool/source | Where used | Purpose | Verification performed | Licence/attribution |
|---|---|---|---|---|
| OpenAI Codex; independent Astra Medium reviewer agents | Local backend foundation batches 1-4, src/, tests/, related docs | Scaffolding, configuration, schema/migrations, health, test and documentation assistance | Dated foundation evidence and independent review logs under evidence/ and docs/reviews/; follow-up workflows explicitly unverified | AI-assisted work; review records distinguish coordinator-run tests from reviewer inspection |
| Django and Python official documentation | Runtime/framework selection and framework patterns | Supported Django 5.2 LTS / Python 3.13 baseline | Exact installed versions and dependency compatibility recorded in foundation evidence | https://docs.djangoproject.com/en/5.2/releases/5.2/ ; https://www.python.org/downloads/ |
| PostgreSQL official documentation and Docker Official Images | Local PostgreSQL and Python containers | Reproducible local runtime | Image digests pinned; PostgreSQL constraints and migrations exercised | https://www.postgresql.org/docs/17/ ; upstream software/image licences apply |

| Claude Code (Claude Opus 5.5) | Shoe catalogue with sizes, 26 September 2026: `src/catalogue/`, importer, `analytics/build_shoe_dataset.py`, storefront and dashboard changes, tests and docs | Implementation assistance under the user's approved plan (`docs/plans/shoe-sizes-catalogue.md`) | Full test suite, importer validation, disposable import/refresh and pandas cross-check, as recorded in the implementation plan; reviewed in [shoe-baseline-gate.md](docs/reviews/shoe-baseline-gate.md) (CLEAR) and approved by the team lead on 11 October 2026 | AI-assisted work |

No external application template or another course's implementation was copied. Source dataset provenance and any frontend imagery/font attribution remain separate future records. This entry does not claim human team members performed the agent-run checks.

## ML quality and reproducible evaluation (25 September 2026)

OpenAI Codex coordinated Phase 3 on `erfan/analytics`, with explicitly assigned `gpt-6-astra` / `low` implementation and a separate `gpt-6-astra` / `medium` read-only review gate. Assistance covers offline segmentation, focused tests, analytics CI, aggregate evaluation and supporting documentation. The coordinator owns Git, tracker and review records. Actual verification, review rounds and limitations are recorded in [ml-quality-evaluation](docs/reviews/ml-quality-evaluation.md); assignment of a reviewer alone is not a completed review. Source data remains the attributed synthetic Analytics Engineering release; no teammate-owned dataset was replaced or repriced. These are agent contributions, not claimed human test execution.

## ML batch handoff and recovery (25 September 2026)

OpenAI Codex coordinates Phase 4 on `erfan/analytics`, with explicitly assigned `gpt-6-astra` / `low` implementation and separate fresh-context `gpt-6-astra` / `medium` read-only review. Assistance covers explicit batch provenance, export/import recovery, focused checks and operational documentation. The coordinator owns Git, tracker and review records; subagents do not stage, commit or push. Actual review status, executed checks and limitations are recorded in [ml-batch-handoff](docs/reviews/ml-batch-handoff.md). These are agent contributions, not claimed human test execution; source dataset attribution remains unchanged.

## Production runtime and AWS security preparation (25 September 2026)

OpenAI Codex coordinates Phase 5 on `erfan/analytics`, with explicitly assigned `gpt-6-astra` / `low` implementation and separate fresh-context `gpt-6-astra` / `medium` read-only review. Assistance covers runtime TLS, bootstrap privilege safety, startup secret configuration, packaging, focused verification and the infrastructure handoff. The coordinator owns Git, tracker and review records; subagents do not stage, commit or push. [Runtime review](docs/reviews/runtime-aws-security.md) records actual checks, findings and limitations. This attribution does not claim deployment, verified AWS permissions or human execution of agent-run tests.


## Local integration and ML display (25–26 September 2026)

OpenAI Codex coordinates Phase 6 on `erfan/analytics`, with explicit `gpt-6-astra` / `low` backend implementation and isolated verification, `gpt-5.6-luna` / `max` frontend implementation/visual verification, and a separate fresh-context `gpt-6-astra` / `medium` read-only review gate. Assistance covers truthful ML display, coherent segment reads, local integration checks and release/handoff documentation. Coordinator owns Git, evidence and review records. [Phase 6 review](docs/reviews/ml-local-release-readiness.md) records actual checks, reviewer outcome and limitations; assignments alone are not completed checks. No human team execution, hosted CI or AWS deployment is inferred from agent-run local tests.

## ML evaluation fixes and storefront polish (26 September 2026)

| Tool/source | Where used | Purpose | Verification performed | Licence/attribution |
|---|---|---|---|---|
| Claude Code (Claude Opus 5.5) | `analytics/evaluate_holdout.py`, `analytics/segment_customers.py`, `src/reporting/segment_contract.py`, `src/catalogue/`, `src/cart/views.py`, related templates, CSS, tests, `evidence/` DATA-01/DATA-02 records and `docs/plans/` | Implementation and verification assistance on tasks chosen and approved by the team | Plans written before each change; full test suite, focused ML/loader suites, disposable-database reruns of import, refresh, independent pandas check, training, import and dashboard, and headless-browser screenshots, as recorded in `evidence/test-data-ai.md` and the plans; reviewed in [shoe-baseline-gate.md](docs/reviews/shoe-baseline-gate.md) (CLEAR) and approved by the team lead on 11 October 2026 | AI-assisted work |
| Gemini (Google) | Dashboard description (reported by Hermann) | Structuring the wording of the dashboard description | Used in FUNC-02 step 7 ([evidence/test-functional.md](evidence/test-functional.md)); each value cross-checked against the database | AI-assisted wording |

Scope and decisions came from the team. Syahfariz chose which review findings to act on
(M-02 hold-out check, M-05 subsample stability, M-03 feature fix; M-04 kept as a documented
limitation), set the adoption criteria for the new recipe before it was run, approved each plan
and decided what is committed. Hermann asked for Add to cart to keep customers on the page. The
manage-products filter and product detail page started from an uncommitted first draft already in
the working tree; Claude Code finished them (filter chips, filtered paging and return, detail
layout, stay-on-page cart message) and wrote the tests. Claude Code ran the recorded checks; they
are not claimed as human test execution. The M-02 finding that segments do not predict later
purchases on this synthetic data is reported as measured, not tuned.
