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
| Expected workload | [cloud-independent-prep.md](plans/cloud-independent-prep.md) B1 (browse-heavy mix, small checkout share) |

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
   EC2 instances in an Auto Scaling Group behind an ALB, managed via Terraform, backed by managed
   RDS PostgreSQL and S3. This is a deliberate choice, not the only option — which leads to:

3. **Pick two (or three, for margin) alternatives and write the rejection reasoning.** Everything
   below is already implied in `ARCHITECTURE.md`; the job is to turn it into justified prose with a
   real reason, not "we didn't have time":
   - **Managed container/PaaS platform** (ECS Fargate, or Elastic Beanstalk) — rejected: the module
     syllabus targets explicit IaaS-level understanding (virtual machines, ASG, ALB configuration);
     a managed platform would hide exactly the mechanics being assessed, and adds lab-quota and
     learning-curve risk inside a fixed four-week timeline.
   - **Serverless** (Lambda + API Gateway for the whole application, not just analytics) —
     rejected: Django's session-backed, HTMX-fragment request model and persistent database
     connections don't map cleanly onto short-lived functions; cold starts would hurt the p95
     checkout latency target. (This mirrors an earlier project decision to reject Lambda for the
     main app while still considering it narrowly for a batch analytics job.)
   - **Optional third, for depth:** container orchestration (ECS/EKS with a service mesh) —
     rejected as unjustified complexity for this workload's size and the team's two-developer
     infrastructure capacity.
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
| Cloud services | EC2, ALB, Auto Scaling Group, RDS PostgreSQL, S3, CloudWatch — each its own labeled box |
| Trust boundaries | At minimum: the VPC boundary, and the public app subnet vs. the private RDS subnet, as drawn boxes, not implied |
| Data stores | RDS and S3 as distinct labeled stores |
| Observability | CloudWatch with arrows showing it receiving logs/metrics, not floating disconnected |
| Data flows | Labeled arrows: browser to ALB (HTTPS/443), ALB to app (HTTP, internal), app to RDS (5432), S3 to import command to RDS (data pipeline) |

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
  beyond "we could have used a different database." This project already has concrete,
  project-specific constraints (a $30 lab budget, a two-person infrastructure team, a gated
  dataset) — use them as the actual reasoning, not filler.
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
