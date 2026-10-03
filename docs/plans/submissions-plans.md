# Submission plan

Written 3 October 2026 by the security session at the user's request. **Status: parked. Start only once all engineering is done** (user decision, 3 October 2026). Deadline: Sunday 11 October 2026, 23:59; target submitting by midday. The user has quizzes on Monday 5 to Wednesday 7 October.

Sources: the project brief (sections 4 to 10 and Appendix A) and the repository state checked on 3 October 2026.

## 1. Where the marks stand (estimate, 3 October 2026)

A judgement from reading the repository against the rubric, not an official mark; each figure ±3.

| Criterion | Max | Estimate | Main reason |
|---|---|---|---|
| Problem framing and architecture | 15 | ~5 | No `report.pdf`, no `evidence/architecture.png`, manifest fields empty; ADRs and README earn some credit |
| Cloud implementation and functionality | 20 | ~14 | Variant A deployed and smoke-tested, Terraform and runbook recorded; no functional test against the deployed shop |
| Cloud data and analytics/AI | 20 | ~16 | Strong evidence and evaluation; no report section tying it together |
| Security and responsible cloud practice | 15 | ~10 | Strong local cases and scans; no cloud security cases |
| Scalability, resilience and operations | 15 | ~3 | `test-resilience.md` and `monitoring.md` are templates; scaling and alarms exist only as configuration |
| Engineering quality and reproducibility | 10 | ~6 | Good code and tests; manifest still a template |
| Team contribution and communication | 5 | ~1 | `TEAM_CONTRIBUTIONS.md` empty; AI declaration incomplete |
| **Total** | **100** | **~55** | |

After the work below, 80 to 90 is realistic. Check the module's grade bands for the A boundary.

## 2. Work remaining

### A. One AWS evidence session (owner: user, about 2 to 3 hours; about USD 1 of lab credit)

Run with one script that saves redacted, dated output (written beforehand; see C1).

1. `up.sh ec2`, then `smoke.sh ec2`.
2. Scale-out: a load burst until the ASG goes from 1 to 2 instances; record the times.
3. Recovery: terminate the instance; time the ASG replacement and the error window.
4. Alarm: force one alarm; capture the alarm history and the SNS email.
5. Logs Insights: export one saved query and its output.
6. Security: SEC-09 (RDS and S3 not public), SEC-10 (HTTPS enforced), SEC-11 (secrets read by the instance role); WAF switched to block mode and a `/login/` burst returns 403.
7. Functional: register, add to cart, check out and view the order on the live site (FUNC-03).
8. `down.sh ec2`; confirm teardown.

### B. Documents (owners: the three test, report and evidence members)

9. `report.pdf`: 8 to 12 pages, the 8 required headings verbatim (brief section 7), text-extractable, file paths cited inline.
10. `evidence/architecture.png`: users, ALB, WAF, EC2/ASG, RDS, S3, Secrets Manager, CloudWatch/SNS, trust boundaries, data flows; labels match Terraform names. Plus `evidence/architecture.md` describing the same in text.
11. `project_manifest.yaml`: every field filled and factual; group ID and member names from the user.
12. `TEAM_CONTRIBUTIONS.md`: one row per member (role, artefacts/commits, test/evidence ownership, reflection).
13. `AI_USE_DECLARATION.md`: every AI tool and where it was used, the review gates as verification, the baseline paragraph, and which agent-instruction files were left out of the ZIP (see D4).

### C. Technical tidy-ups (owner: Claude, unattended)

14. (C1) The evidence-session script for section A, with redaction of account IDs and public IPs.
15. Turn the section A output into RES, MON, SEC-09 to SEC-11 and FUNC-03 records.
16. Rerun the IaC scan (SCAN-07) on `base/` and `ec2/` and re-triage it.
17. Redact the account-ID fragments in `evidence/aws-capability-record.md` (lines 7 and 21).
18. Preflight checker (see D2).
19. Push so the CI `security` job runs for the first time; fix what fails; record the run in `evidence/security-scan-triage.md`.

**Not required:** the Fargate comparison (variant B). Do it only if A to C are finished; the report can still name Fargate as an alternative considered, backed by the ADRs.

## 3. Making the ZIP easy to mark

The brief calls the package "designed for reliable AI-assisted marking". Assume an AI reads `README.md` and `project_manifest.yaml` first, follows the paths and scores each criterion; a human checks its output.

What follows from that:
- It credits only what it can find and read. A claim without a path, or evidence it cannot open, scores zero.
- Contradictions hurt more than gaps. Dated plans, reviews and status notes saying "not deployed" or "planned" next to evidence of deployment are the main risk.
- It follows the brief's exact filenames, headings, manifest schema and test fields (objective, setup, command, expected, actual, date, artefact path).

### D. Actions (do these last, after the evidence exists)

1. **Rubric-to-evidence index:** one table in `README.md` mapping each of the 7 criteria to the exact files that prove it, and the same mapping as an extra manifest field (the brief allows added fields). Owner: Claude.
2. **Preflight checker:** fails on any missing manifest path, any `TODO`/`Gxxx`/empty required field, any credential, account ID or public IP, and builds the ZIP named `Group_Gxxx_INF2006_Project.zip` without `*.tfstate*`, `*.tfvars`, `*.tfplan`, `.terraform/`, `src/.env` or local caches. Owner: Claude.
3. **Contradiction sweep:** every status line in the README, manifest, evidence index and report describes the final state (deployed, tested, torn down on a stated date). Grep the files the marker reads for "not deployed", "planned", "not yet", "TODO", "pending". Owner: Claude, user approves.
4. **ZIP contents (user decision pending):** recommended to exclude `AGENTS.md`, `CLAUDE.md` and `docs/plans/`, because they are instructions written for AI agents or superseded decisions. Keep `docs/decisions/` (ADRs) and `docs/reviews/` as evidence of justification and verification. Declare the exclusion in `AI_USE_DECLARATION.md`.
5. **Machine-readable artefacts:** report as real text; architecture described in text as well as the image; every evidence case uses the same field labels; raw output as text, screenshots only as supplements with captions.
6. **Mock marking pass (Saturday):** a fresh AI session with no project context gets the brief and the built ZIP and marks it against the rubric, citing paths. Every "no evidence found" is fixed before submission. Owner: user starts the fresh session; Claude fixes the gaps it reports.

## 4. Schedule

| When | User | Teammates | Claude |
|---|---|---|---|
| Sat 3 / Sun 4 | Hand out B9 to B13; send group ID and member names | Start B9 to B13 | C14, C16, C17, D2 |
| Mon 5 to Wed 7 (quizzes) | Nothing | Report sections 1 to 5 | Draft evidence files ready for results |
| Thu 8 | Section A session | — | C15 |
| Fri 9 | Review evidence | Report sections 6 to 8 | D1, D3 |
| Sat 10 | Push; start D6 | Report to PDF | C19, fix D6 gaps |
| Sun 11 | **Submit by midday** | — | — |

## 5. Open decisions

- [ ] Claude's scope beyond security: writing the resilience, monitoring and functional parts of the section A script (proposed yes).
- [ ] Drop the Fargate comparison unless A to C are done by Friday 9 October (proposed yes).
- [ ] ZIP exclusions in D4.
- [ ] Group ID and member names for the manifest.
- [ ] Dockerfile base-digest bump for the 21 fixable image findings (see `evidence/security-scan-triage.md`); proposed: leave frozen and disclose.
