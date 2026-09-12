# Frontend foundation review

## Task and review scope

- Task: INF2006 Phase 1 frontend foundation.
- Required scope: Django templates, shared CSS/layout/components, responsive navigation, form/button/message/empty/error states, a presentation-only HTMX interaction, keyboard accessibility, visible focus, mobile layout and live HTTP/browser verification. Business routes remain reserved.
- Specifications reviewed: [AGENTS.md](../../AGENTS.md), [DESIGN.md](../../DESIGN.md), [FRONTEND.md](../FRONTEND.md), [API.md](../API.md), [ARCHITECTURE.md](../ARCHITECTURE.md), [SECURITY.md](../SECURITY.md), [DEVELOPMENT.md](../DEVELOPMENT.md), and `evidence/frontend-foundation.md` (historical record, removed).
- Backend handover baseline: `51e4ec1`; first frontend implementation checkpoint: `d081007`.
- Round 1 reviewed snapshot: `d081007..54d02cf` (working tree clean at review time).
- Remediation checkpoint for Round 2: `c59b162` (complete corrected implementation diff is `51e4ec1..c59b162`).
- Round 2 reviewed snapshot: `51e4ec1..6e94aec894e4afe384bec1a47ac2d8cfd2b005a8` (working tree clean at review time; the latter checkpoint changes documentation only).
- Owned paths: frontend templates/assets/tests, minimal presentation-serving URL/view integration, related API/README/tracker/evidence documentation and `.vscode/settings.json`.

## Review metadata

- Reviewer: independent Astra Medium (`gpt-6-astra`, reasoning `medium`), reviewer agent `Euler` (`01a09479-885e-7092-a925-2a86251249ae`).
- Date: 12 September 2026.
- Review mode: read-only; reviewer did not edit, stage, commit, deploy or delegate.
- Round 1 checks: targeted diff/spec/source inspection, `git diff --check`, focused frontend tests (`4 passed in 0.43s`), HTTP checks for `/`, `/foundation/design-notes/`, missing route and `/health/`. Reviewer did not repeat browser or full-suite checks in this round.
- Round 2 checks: targeted complete-scope inspection, `git diff --check`, focused frontend tests (`5 passed in 0.20s` with cache/bytecode writes disabled), and HTTP checks for the home page (`200`), success fragment (`200`), intentional failure fragment (`503`), missing route (`404`) and health (`200` JSON/no-store). Browser layout, keyboard, focus, announcement and console claims remain explicitly attributed to the coordinator’s browser evidence.
- Reviewer limitation: model settings were not exposed to the reviewer runtime for independent certification; the coordinator assigned the explicit Astra Medium settings above. Browser/visual claims remained attributed to the coordinator’s evidence record.

## Findings and remediation

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| F-001 | Major | `src/templates/foundation/home.html:114-121` | `docs/FRONTEND.md` validation states | The form only showed disabled controls; it lacked an invalid field, associated error text and `aria-invalid` example. Add a clearly labelled presentation-only validation state with shared styling and an accessible error association. | Fixed in `c59b162`: invalid readonly sample uses `aria-invalid="true"`, `aria-describedby`, a visible error and shared `.form-field--invalid`/`.form-error` styles; focused frontend tests `5 passed`, live browser inspection confirmed the attributes and text. | Resolved in Round 2; no residual issue. |
| F-002 | Minor | `src/templates/foundation/home.html:141-146`; `src/static/js/site.js:48-58` | `docs/FRONTEND.md` dependency/error states | The HTMX interaction handled loading/success but no request failure feedback or usable retry. Add scoped announced failure feedback and a retry path; record an actual failed-request check. | Fixed in `c59b162`: presentation-only `/foundation/design-notes-unavailable/` returns 503, scoped `htmx:afterRequest` builds static error DOM, changes the success action to “Retry design notes” and restores it after success; HTTP and coordinator browser 503/retry checks passed. | Resolved in Round 2; no residual issue. |
| F-003 | Minor | `src/static/css/site.css:857-859` | Accessibility requirement for visible focus | The focus handoff targeted the returned heading, but CSS removed its outline without a replacement. Give the focused heading a visible indicator and verify keyboard activation through the swap. | Fixed in `c59b162`: programmatically focused fragment heading has a visible `solid` `2.4px` outline in the coordinator’s live browser after both failure and success swaps. | Resolved in Round 2; no residual issue. |
| F-004 | Minor | `src/static/css/site.css:208-218`; `src/static/css/site.css:1088-1091` | `DESIGN.md` mobile touch targets | The mobile Menu target had no minimum height and System status was explicitly 38px, below the stated 44px target. Provide 44px hit areas and record measured dimensions. | Fixed in `c59b162`: mobile browser measurement at `390x844` found Menu `44px` high and System status `44px` high; responsive nav behavior remained correct. | Resolved in Round 2; no residual issue. |
| F-005 | Minor | `evidence/frontend-foundation.md:3,7,55` | Review scope/evidence accuracy | `d081007..54d02cf` excluded the initial frontend implementation introduced by `d081007`, while the evidence claimed it was the complete task diff. Correct the baseline to the backend handover commit and distinguish the reviewed range. | Fixed in `c59b162`: evidence and tracker use `51e4ec1` as the backend handover baseline and identify the first frontend checkpoint separately; complete task scope includes all new templates/assets/docs/tests. | Resolved in Round 2; no residual issue. |

## Round 2

Round 2 completed on 12 September 2026. The same independent Astra Medium reviewer inspected the complete corrected task scope from `51e4ec1` through `6e94aec894e4afe384bec1a47ac2d8cfd2b005a8`, preserved finding IDs, and found F-001 through F-005 resolved with no new actionable findings and no substantive backend findings. The reviewer’s browser limitation is explicit above; coordinator browser evidence is recorded in `evidence/frontend-foundation.md` (historical record, removed). Conclusion: clean; the frontend foundation may be marked complete.

Record retention: the separate foundation verification Markdown and raw output files were deleted at the user's request on 12 September 2026. References above identify historical inputs available in Git history; this review summary is retained.
