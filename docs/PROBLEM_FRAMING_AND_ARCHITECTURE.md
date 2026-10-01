# Problem framing and architecture — roadmap to a top score

This file plans how to score as close to full marks as possible on the **Problem framing and
architecture** rubric criterion (15 of 100 marks). It is a roadmap, not the deliverable itself —
the actual diagram, report and manifest are produced elsewhere (`evidence/architecture.png`,
`report.pdf`, `project_manifest.yaml`). Nothing here is implemented yet.

## Why this file exists

The brief (`INF2006_Team_Project_Brief_2026.pdf`) grades this criterion from **four artifacts
together**: `README.md`, report sections 1–3, the one required architecture diagram, and
`project_manifest.yaml`. The rubric's own "marker principle" states markers award marks only for
verifiable evidence, never for ambition, polish or an unsupported claim. There is no indication in
the brief that grading is curved or quota-limited — it is criterion-referenced against an explicit
checklist. The only lever documented anywhere is *literal compliance with that checklist, backed by
traceable evidence*. This roadmap treats "score in the top slice" and "hit every explicit
requirement below with real, cross-referenced evidence" as the same task, because the brief gives
us no other mechanism to aim at.

## What the brief literally requires

From section 5.1 and the rubric table:

1. A clear, specific user need (not generic ecommerce boilerplate).
2. A coherent architecture, explained in prose, not just drawn.
3. Service-model and deployment-model choices stated explicitly, **with at least two alternatives
   considered and why they were rejected**.
4. Assumptions, constraints, expected workload and cost-control measures stated.
5. **One** architecture diagram showing: users, application components, cloud services, trust
   boundaries, data stores, observability, and data flows — labels matching the repository and
   evidence filenames.

Missing any one of these five caps the score regardless of how good the rest looks.

## Where we already stand — reuse, don't rewrite

Most of the thinking this criterion needs has already been written down elsewhere in this repo.
The work here is mostly *extraction and packaging*, not new design:

| Requirement | Already exists at |
|---|---|
| User need | [PROJECT_SCOPE_INF2006.md](../PROJECT_SCOPE_INF2006.md) §1 (twofold: reliable order placement for customers, understandable sales/inventory information for the store operator) |
| Baseline architecture and flows | [PROJECT_SCOPE_INF2006.md](../PROJECT_SCOPE_INF2006.md) §7, [ARCHITECTURE.md](ARCHITECTURE.md) |
| Alternatives already reasoned about (unpolished, needs rewriting as report prose) | [ARCHITECTURE.md](ARCHITECTURE.md)'s "Failure boundaries and alternatives" section |
| Cost-control measures | [PROJECT_SCOPE_INF2006.md](../PROJECT_SCOPE_INF2006.md) §7 "Budget plan" (USD 30 of 40 working cap, ASG max 2, Single-AZ RDS, short log retention) |
| Expected workload | [cloud-independent-prep.md](archive/plans/cloud-independent-prep.md) B1 (browse-heavy mix, small checkout share) |

**Gaps:** the diagram doesn't exist yet; `report.pdf` and `project_manifest.yaml` don't exist yet;
`ARCHITECTURE.md`'s alternatives are terse status notes, not the justified prose the report needs.

## Roadmap

### Phase A — lock the content before touching a diagram tool

Do this first. A diagram drawn before the reasoning is settled gets redrawn.

1. **User need (report §1).** Tighten the scope doc's two-sided problem statement into one
   paragraph: customer needs reliable order placement; store operator needs understandable sales
   and inventory information. State it as the reason every technical choice below exists — the
   brief penalises technical features that don't visibly serve a user problem.

   **Decided: frame the store as local (Singapore/SEA), not global.** This isn't just the safer
   choice, it's the honest one — the scope doc already says "a **small** ecommerce application"
   and "a **small** store operator," and the actual build is single-region, Single-AZ RDS, no
   CloudFront, on a four-week/USD 30–40 budget. A "global ecommerce" framing would raise the bar a
   marker grades against (CDN, multi-region redundancy, data residency, currency/i18n) without any
   of it being built — under the marker principle that's a scope-claim the evidence can't back, and
   it makes "coherent architecture" *harder* to score well on, not easier. Framing it as local
   turns every cost-saving choice already made into a clean, honest trade-off instead of a gap:
   - Single region, no CloudFront — the customer base is geographically concentrated, so a CDN's
     latency benefit is marginal for this workload. (Keep the reason as workload/budget/deadline,
     **not** "CDNs only matter for global users" — that claim is technically inaccurate and
     `ARCHITECTURE.md` already avoids making it.)
   - Single-AZ RDS, ASG max 2 — sized to a small operator's actual expected traffic, not a global
     retailer's.
   - No multi-currency/i18n — out of scope by design, stated up front, not discovered as a gap.
   - Matches infrastructure already committed to: Singapore business dates in analytics, the
     submission deadline stated in Singapore time, and the "small store operator" language already
     in `PROJECT_SCOPE_INF2006.md` §1.

2. **Service model and deployment model, stated as a decision (report §3).** State plainly: IaaS —
   EC2 instances in an Auto Scaling Group behind an ALB, backed by managed RDS PostgreSQL and S3,
   provisioned with Terraform (see [AWS_INFRASTRUCTURE.md](AWS_INFRASTRUCTURE.md), "Deployment
   method", and [aws-terraform.md](archive/plans/aws-terraform.md)). This is a deliberate choice,
   not the only option — which leads to:

3. **Justify the choice from the workload, then reject the alternatives against it.** Written
   25 September 2026 as report-ready material for §3; see
   [Service-model justification](#service-model-justification-report-3-material) below. The rule:
   every reason must be a property of **42Factors' workload**, never of the project's
   circumstances. "The lab budget is small" or "the deadline is close" explains why *we* chose,
   not why the *shop* needs it, and other groups will have made different choices (some use
   Elastic Beanstalk) under the same circumstances. Cost is argued as the shop's operating cost,
   not as lab credits.
   - **A second, deployment-*configuration* trade-off already drafted in the scope doc**: public
     EC2 subnets with ALB-restricted security groups vs. private subnets behind a NAT gateway.
     Chosen: public subnets with ingress restricted to the ALB security group, to avoid a
     continuously-billed NAT gateway. State the estimated cost difference explicitly (see Phase D).
     This is a second, genuinely distinct trade-off beyond the top-level service model, and costs
     nothing extra to include since it's already reasoned in `ARCHITECTURE.md`.

4. **Assumptions, constraints, workload, cost-control (§5.1 third bullet — easy to forget as its
   own paragraph).** Pull directly from the Budget plan section: USD 30 of the USD 40 lab account
   as a working cap (~USD 10 reserved), ASG minimum 1 / test maximum 2, RDS Single-AZ as an
   explicit, named compromise (not hidden), short CloudWatch log retention, and browse-heavy
   expected traffic with a small checkout share (from the load-test plan).

### Service-model justification (report §3 material)

> **Sprint note (1 October 2026):** the rejection of ECS on Fargate under D5 below was argued from the design, not measured. It is being replaced by a measured EC2-versus-Fargate comparison ([plan](plans/aws-ecs-comparison.md)). Keep drivers D1 to D5; rewrite the Fargate paragraph and the summary matrix from the data once the runs are done.

Structure: state the decision drivers first, each traced to the story, then test every option
against them. The choice then follows from the requirements instead of being defended after the
fact.

**Decision drivers.** 42Factors is a small online shoe shop in Singapore run by one store operator.

| Driver | Traced to |
|---|---|
| **D1. Checkout stays correct under contention.** Demand for a popular shoe or a restock arrives in bursts; many buyers decrement the same stock at once, and the database is the bottleneck. | Transactional, idempotent checkout and "no negative stock" ([scope](../PROJECT_SCOPE_INF2006.md)); the scope's proposed starting objective of p95 checkout below 2 s and unexpected errors below 1%, to be calibrated after the one-instance measurement; sold-out rejections reported separately |
| **D2. The storefront is always open, with steady traffic and bursts.** It never scales to zero, and it must absorb a burst. | ASG minimum 1, test maximum 2; measured scaling ([AWS_INFRASTRUCTURE.md](AWS_INFRASTRUCTURE.md)) |
| **D3. Any web server can be lost without losing carts or logins.** | Database-backed sessions; the session-continuity test |
| **D4. Every security boundary is explicit and auditable,** because the shop holds customer accounts and order history. | Threat-control map; trust boundaries on the diagram |
| **D5. Cost and complexity proportionate to one deployable run by a small business,** with a path to grow. | One Django service, one database |

**Chosen: EC2 in an Auto Scaling group behind an ALB.** Replaceable instances running one container
image (D3), a fixed ceiling of instances and Gunicorn workers (D1), a scaling signal chosen for the
workload (ALBRequestCountPerTarget, because requests are the load that matters), and security groups
chaining ALB → app:8000 → RDS:5432 as explicit resources (D4).

**Lambda (with API Gateway) for the whole application: rejected on D1 and D2.** This is the
strongest argument. Under a burst, Lambda scales out to many concurrent functions, and each opens
its own PostgreSQL connection. That hits the database with unbounded concurrency at the moment rows
are locked for stock decrements. The failure mode is connection exhaustion and lock queues exactly
when sales matter most. The ASG gives **bounded concurrency** (instances × Gunicorn workers), so the
application tier applies back-pressure and the database stays within what it can serve. Lambda's
main benefit, scaling to zero, is worthless for a storefront that is always open, and its cold
starts land on the first buyers after a quiet period. Making it work needs RDS Proxy and a Django
adapter (Mangum or Zappa) in front of API Gateway: more components for a worse fit. Lambda remains
a reasonable fit for the batch refresh alone; it is not used because the refresh already runs
inside the application image under a database lock.

**EKS: rejected on D5.** Kubernetes solves scheduling many services across a fleet; 42Factors has
one deployable. The control plane is a fixed hourly charge before any request is served (verify
and cite the current price from the AWS pricing page, with its date), plus manifests, an ingress
controller and node groups. That is a disproportionate operating cost for a small shop, not a
technical impossibility.

**Elastic Beanstalk: same runtime topology, rejected on ownership (D4).** Beanstalk provisions EC2,
an Auto Scaling group and an ALB underneath, so do **not** claim the chosen design performs better.
Claim what is owned rather than generated:
- The trust boundaries are designed, not defaulted: the security-group chain and the private
  database subnets are explicit, reviewable resources.
- The database lifecycle is independent of the application. Beanstalk can create RDS inside an
  environment, and AWS documents that terminating that environment deletes the database (cite the
  AWS page). Order history must outlive any deployment. A decoupled Beanstalk setup is possible,
  but it then configures the same pieces this design owns.
- Health checks (`/health/`) and the scaling signal are chosen for the workload, and every resource
  maps one-to-one into Terraform, so the configuration is auditable and reproducible.

Report sentence: *"Elastic Beanstalk would provision this same topology; we own each component
explicitly because the security boundaries and the data lifecycle are requirements, not
defaults."* Never disparage Beanstalk: other groups use it, and it is a sound platform.

**ECS on Fargate: the honest near-miss, rejected narrowly on D5.** It meets D1 to D4 about as well
as EC2: bounded tasks, stateless containers, explicit security groups. An orchestrator's value is
placing many kinds of containers, and 42Factors runs exactly one, so ECS adds clusters, task
definitions and services with nothing to orchestrate yet. Because the application is already
containerised, moving to ECS is a deployment change, not a rewrite. Present it as the evolution
path: *"If the shop adds a second service, such as a separated analytics or image-processing
worker, ECS becomes the right choice, and the image moves unchanged."* Knowing when the choice
stops being right is part of the argument.

**Summary matrix for the report.**

| | D1 bounded DB concurrency | D2 always on, with bursts | D3 replaceable instances | D4 explicit boundaries | D5 proportionate |
|---|---|---|---|---|---|
| **EC2 + ASG (chosen)** | ✓ | ✓ | ✓ | ✓ | ✓ |
| Elastic Beanstalk | ✓ | ✓ | ✓ | ~ generated | ✓ |
| ECS on Fargate | ✓ | ✓ | ✓ | ✓ | ~ orchestration unused |
| EKS | ✓ | ✓ | ✓ | ✓ | ✗ fixed control-plane cost |
| Lambda | ✗ unbounded connections | ✗ scale to zero wasted, cold starts | ✓ | ✓ | ~ adds API Gateway and RDS Proxy |

**Also considered and rejected: splitting analytics into a separate service on its own admin
instance.** Both services would share one PostgreSQL schema (a distributed monolith without data
separation); operators sign in through Django sessions, so a split adds a new authentication
boundary; and dashboard reads are light because aggregation is precomputed. The heavy work is
isolated in time instead: `refresh_analytics` runs as a scheduled batch under an advisory lock, off
the request path. Revisit if analytics needs its own data store or independent scaling.

**Evidence each claim needs** (a claim without a linked artifact earns nothing):
- D1: during the Locust run, capture the RDS `DatabaseConnections` CloudWatch metric next to p95
  checkout latency and the absence of negative stock. That turns the Lambda argument into a
  measurement: connections stayed within the bounded ceiling at peak.
- D2: the fixed-capacity versus autoscaling comparison.
- D3: the session-continuity test (terminate an instance mid-session).
- D4: the threat-control map and the redacted security-group configuration.
- Prices and AWS guidance (EKS control plane, Beanstalk-coupled RDS deletion): cite the page and
  the date checked. Do not reuse unverified numbers.

### Phase B — build the one diagram

Tool: **draw.io / diagrams.net**, using the built-in AWS Architecture Icons library (search
"AWS19" in the shape panel). Free, offline-capable, exports directly to PNG/SVG, and the source
`.drawio` file can be committed for traceability.

Checklist — the diagram must show all seven required elements, using names that exist in this
repo, not generic terms:

| Required element | Draw it as |
|---|---|
| Users | Customer and Store Operator, as two distinct actors |
| Application components | "Django/Gunicorn (EC2 ASG)" — matches `ARCHITECTURE.md`'s own wording |
| Cloud services | EC2, ALB, Auto Scaling Group, RDS PostgreSQL 17, S3, ACM, ECR, Secrets Manager, IAM (`LabInstanceProfile`), Systems Manager, CloudWatch, SNS, WAF and CloudTrail — distinguish deployed evidence from planned controls; AWS Budgets dashed until the lab confirms it. No Lambda; EventBridge Scheduler only if the optional side quest is built |
| Trust boundaries | At minimum: the VPC boundary, and the public app subnet vs. the private RDS subnet, as drawn boxes, not implied; label the security-group chain sg-alb → sg-app → sg-db |
| Data stores | RDS and the one S3 bucket (dataset, exports, images, `.glb` models) as distinct labeled stores |
| Observability | CloudWatch with arrows showing it receiving logs/metrics, not floating disconnected; SNS alert to the team; CloudTrail event history for API audit |
| Data flows | Labeled arrows: browser to ALB (HTTPS/443), ALB to app (HTTP 8000, internal), app to RDS (5432, TLS), browser to app for static images and 3D models (served by WhiteNoise from the image; no browser-to-S3 arrow), S3 to import command to RDS (data pipeline), secrets and image at instance boot |

A review draft following this checklist was drawn on 25 September 2026 (outside the repository);
the submission copy is still to be drawn in draw.io.

Save both `evidence/architecture.drawio` (source, for traceability) and `evidence/architecture.png`
(the path the manifest schema requires exactly).

### Phase C — wire it into the deliverables

1. **README.md** — link the diagram image, quickstart commands, technology list, known
   limitations (per the brief's required README contents).
2. **report.pdf §1–3** — the Phase A prose plus a reference to the diagram; the report must
   *explain*, not duplicate, the manifest (explicit brief instruction).
3. **project_manifest.yaml** — fill `architecture.diagram`, `architecture.service_model`,
   `architecture.deployment_model`, `architecture.components[]` factually, using the same names as
   the diagram.
4. **Consistency pass** — every label in the diagram must appear identically in the manifest's
   `components` list and correspond to a real folder/Terraform resource name in `src/`. The
   submission preflight checklist tests exactly this ("architecture labels match component names in
   source/configuration and evidence"); it is a named, checkable item, not a suggestion.

### Phase D — differentiators (the difference between competent and excellent)

The minimum checklist above earns a compliant score. These push past it, and all are cheap because
they reuse reasoning already sitting in this repo:

- **Quantify the cost trade-off**, don't just narrate it: state the NAT gateway's approximate
  hourly + per-GB cost against the "$0 extra" of ALB-restricted public subnets, at the project's
  actual expected traffic volume. A number beats an adjective.
- **Tie the architecture to a measurable success criterion.** The scope doc already proposes p95
  checkout under 2 seconds and errors under 1% as a load target — cite that figure here as a
  *design driver* for choosing ALB + ASG, not only as a later test target. Reusing one fact across
  two rubric criteria (architecture and scalability) reads as a coherent design, which is what a
  15-mark "coherent architecture" line is actually checking for.
- **Cross-reference the trust boundary to the security section.** The same VPC/subnet boundary
  drawn here is also what the security criterion's threat-control map needs (RDS security-group
  restriction, S3 block-public-access). Draw and reason about it once, cite it from both places.
- **Avoid the generic-diagram failure mode.** A marker reading many submissions will see dozens of
  undifferentiated "browser → app → database" boxes with no trust boundary and no real alternative
  beyond "we could have used a different database." Ground the reasoning in the shop's workload
  (the decision drivers above), not in the project's circumstances; circumstances such as the lab
  budget belong in the assumptions and constraints paragraph, not in the justification.
- **Every claim needs an artifact path.** Per the brief's evidence rules table: state limitations
  honestly and link every claim to something a marker can open. A claim with no linked file is
  worth nothing under the marker principle, however well written.
- **One forward-looking paragraph on global scale, clearly marked as deferred, not built.** Having
  scoped the story as local (above), add one short sentence in report §3: "if this grew beyond a
  single region, we'd add CloudFront for static assets and consider RDS read replicas in a second
  region." This costs nothing to implement and demonstrates awareness of the global case without
  claiming a bigger project than what was delivered — free credit for engineering judgement.

### Phase E — verification before calling it done

- Literal grep check: every label in the diagram and every `components[]` entry in the manifest
  matches an actual name in `src/` or the eventual Terraform config.
- Cold read: have a teammate who didn't draw it trace a checkout request through the diagram
  without narration. If they can't, a marker won't either.
- Confirm report §1–3 makes no claim that isn't backed by a linked artifact.

## Sequencing and effort

| Phase | Depends on | Rough effort | When |
|---|---|---|---|
| A — content/prose | Nothing; can start immediately | 1–2 hours | Now, in parallel with backend work |
| B — diagram (first draft) | Phase A's component list | 2–4 hours | Now, using currently-planned AWS components |
| B — diagram (final pass) | Actual Terraform resource names existing | 30–60 minutes | After the Terraform skeleton (`cloud-independent-prep.md` B5) |
| C — wiring into README/report/manifest | Phases A and B | 1 hour | During packaging (brief's suggested week 5–6) |
| D — differentiators | Phases A–C done | Ongoing polish | Week 5 "close gaps" per the brief's own suggested plan |
| E — verification | Everything above | 30 minutes | Just before submission preflight |

Phase A and a first pass at Phase B do not depend on AWS being deployed yet — they can be started
in parallel with backend/analytics work, which is why this file was requested now rather than
later.
