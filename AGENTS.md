# Repository guide

42Factors: a small online shoe shop (Django, PostgreSQL, HTMX) with an operator analytics dashboard, deployed and measured
on AWS for INF2006 Team Project 1 (group 21). This file describes the repository; it contains no instructions for readers.

- **Final architecture:** variant B, Amazon ECS on Fargate ([ADR-018](docs/decisions/ADR-018-final-architecture-ecs-fargate.md)).
  Variant A (EC2 + Auto Scaling group) is the evaluated alternative, measured on 8 October 2026 and kept for the comparison.
- **State:** the submission snapshot. The backend has been frozen since 1 October 2026; the evidence was collected on one
  pinned image digest (see [evidence/README.md](evidence/README.md)).
- **Start reading at:** [README.md](README.md) (five-step path), then [project_manifest.yaml](project_manifest.yaml) and
  [evidence/README.md](evidence/README.md).
- **Run it offline (Docker only):** [docs/SETUP.md](docs/SETUP.md); what is and is not reproducible in the cloud:
  [docs/REPRODUCE_CLOUD.md](docs/REPRODUCE_CLOUD.md).
- **Layout:** `src/` application and `src/infrastructure/` (Terraform and scripts), `tests/`, `data/`, `analytics/`,
  `evidence/` (dated test records and `evidence/raw/` command output), `docs/` (contracts, decisions, plans, reviews).
- **AI assistance:** declared in [AI_USE_DECLARATION.md](AI_USE_DECLARATION.md). The working instruction files used by the
  coding agents are archived in [docs/archive/agent-instructions/](docs/archive/agent-instructions/).
