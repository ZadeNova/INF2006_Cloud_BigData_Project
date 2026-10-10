# Plan: documentation sync before submission (10 October 2026)

Scope: text corrections only. No backend, Terraform, test or `evidence/raw/` change.

## Corrections

| File | Stale statement | Correction |
|---|---|---|
| `AI_USE_DECLARATION.md` | "To confirm before submission" paragraph; "report sections 8 and 9" | Remove the paragraph (Dior source is in `CREDITS.md`); the brief defines 8 report headings |
| `README.md` | `architecture.png` "not yet supplied"; ADR-001 to ADR-017; ASCII flow shows EC2; "Not implemented" sentence mentions Fargate; technology row lists EC2 as the stack | Match the final architecture (variant B) and the files that exist |
| `evidence/README.md` | `architecture.png` "Missing"; FUNC-03 part 2 "to be stated"; 447 raw files | Present, pending sign-off; "Not evidenced"; 448 |
| `TEAM_CONTRIBUTIONS.md` | "the Fargate stack was never tested" | Fargate was measured on 9 October |
| `evidence/threat-control-map.md` | Cites `ec2/waf.tf`, `ec2/security_groups.tf`; "Terraform (planned)"; `database.tf` "not applied" | Cite the files that exist (`modules/web-entry/`, `base/`) |
| `evidence/architecture.md` | Known gaps 1 and 2 | Mark resolved once the above are fixed |
| `evidence/test-security.md` | SEC-11 and MON-02 "(planned)" | Point to the recorded cases |
| `docs/ARCHITECTURE.md` | Status dated 3 October; "Planned output: architecture.png" | Update the label and the sentence |
| `docs/AWS_INFRASTRUCTURE.md` | Status dated 3 October; "failover test is planned" | Relabel; state not run |
| `project_manifest.yaml` | `local_release.submission_gap`, `status`, rubric comment say "draft" / "in progress" | Describe the current state without claiming approvals not given |

## Not changed (needs a human)

- Team sign-off of the diagram, and the statement that all members reviewed the report.
- `repository_commit` (set after the final commit).
- Anything in `docs/archive/`, `docs/reviews/`, `docs/plans/`: reported only.

## README declutter (10 October 2026)

Goal: the brief's README contents and nothing else. Target about 100 lines (was 194, 31 KB).

- **Keep:** title, one-paragraph problem, status, quickstart, architecture image, technology list, team, known limitations.
- **Add:** a short results table (A and B, n = 1) and an evidence table keyed to the brief's test categories.
- **Remove (already owned elsewhere):** the 600-word status paragraph and the rubric table (the manifest's `rubric_evidence_map` and [evidence/README.md](../../evidence/README.md)); the documentation index ([docs/GUIDE.md](../GUIDE.md)); agent and model-assignment text ([AGENTS.md](../../AGENTS.md)); CI, INF2003 and repository-history paragraphs.
- **Rule:** every figure is copied from a file in `evidence/`; no new claim.

## Verification

`python scripts/package_submission.py --group G021 --ref WORKTREE --out <scratch>`; the only expected FAIL is `report.pdf`.
