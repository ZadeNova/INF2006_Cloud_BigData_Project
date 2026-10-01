# Documentation alignment

Written 24 September 2026, branch `erfan/analytics` at `b3c7d5a`. Purpose: bring the Markdown documents in line with what the repository actually contains after PR #2, the dataset import, the analytics dashboard and the UIUX merge. Facts below come from `src/config/urls.py`, the app `urls.py` files, the models, migrations, management commands and the tests directory, cross-checked against the tracker. Nothing was run; the 438-test figure is the tracker's (24 September) and is cited as such.

## Scope

Fix statements that are false today. Do not restructure documents, rewrite history, or claim anything that has not been run.

**Changed**

| File | Correction |
|---|---|
| `README.md` | Status, feature list, dataset paragraph, getting-started, layout and limitations describe the delivered application; AWS, evidence and report stay marked as not done |
| `src/README.md` | Route and command list is current (cart, checkout, orders, analytics, `import_dataset`, `refresh_analytics`, `snapshot_inventory`, `seed_demo --no-products`) |
| `tests/README.md` | Describes the whole suite and how to run it, not only the foundation batches |
| `docs/FRONTEND.md` | Business URL names exist; dark mode and the theme toggle are noted |
| `docs/API.md` | Statistics preview route added; stale "not created" and "contract, not implemented" wording removed |
| `docs/SCHEMA.md` | "No auth routes yet", "follow-up tasks" and "no checkout service" removed |
| `docs/TESTING.md` | Suite exists; CI exists |
| `docs/ARCHITECTURE.md` | Business behaviour is implemented locally; AWS stays planned |
| `docs/DATA_PIPELINE.md`, `data/README.md` | "Pending review" and "outside this batch" wording updated to the recorded outcomes |
| `docs/plans/project-evidence.md` | Evidence table and threat seed rows updated (import, dashboard, logging exist) |
| `docs/archive/plans/astra-review.md` | No round is open; PR #2 merged; the "upcoming queue" is now cleared |
| `docs/archive/plans/cloud-independent-prep.md` | Status line: the backend prerequisite is done, so the track is unblocked |
| `docs/archive/plans/analytics-status.md` | One sentence: the 24 September re-theme has not been independently reviewed |
| `evidence/test-functional.md`, `test-security.md`, `test-resilience.md` | Foundation-only notes corrected: the workflow is implemented but no run has been recorded |
| `docs/IMPLEMENTATION_PLAN.md` | One dated entry for this alignment; renamed-branch wording; nothing marked complete |

**Not changed, and why**

- `docs/reviews/*`: dated records of what a reviewer saw.
- `PROJECT_SCOPE_INF2006.md`, `AGENTS.md`, `CLAUDE.md`, `docs/ANALYTICS.md`, `docs/SECURITY.md`, `docs/AWS_INFRASTRUCTURE.md`, `docs/DEVELOPMENT.md`, `docs/INF2003_BASELINE.md`: checked, no false statements found.
- `analytics/README.md`, `data/DATA_DICTIONARY.md`, `data/PROFILE.md`: accurate and dated.
- `project_manifest.yaml` (not Markdown): still has TODO fields; listed for the user.
- `TEAM_CONTRIBUTIONS.md`, README team table, `AI_USE_DECLARATION.md`: need the team's own facts; inventing them would breach the attribution rule. Listed for the user.
- `DESIGN.md` source and licence attribution: needs the owner's answer.

## Rules for the edits

- Say "implemented locally" where a review record or test supports it, and "not deployed" for anything on AWS.
- Do not add test counts except the tracker's, labelled with its date.
- No new claims of verification: the live walkthrough and full-suite re-run are the next steps and will be recorded in `evidence/`.

## Verification

Read-only: grep the edited files for the removed phrases and confirm every link target still exists. No tests run (documentation only). No commit until the user asks.
