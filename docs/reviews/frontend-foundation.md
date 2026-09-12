# Frontend foundation review

## Task and review scope

- Task: INF2006 Phase 1 frontend foundation.
- Required scope: Django templates, shared CSS/layout/components, responsive navigation, form/button/message/empty/error states, a presentation-only HTMX interaction, keyboard accessibility, visible focus, mobile layout and live HTTP/browser verification. Business routes remain reserved.
- Specifications reviewed: [AGENTS.md](../../AGENTS.md), [DESIGN.md](../../DESIGN.md), [FRONTEND.md](../FRONTEND.md), [API.md](../API.md), [ARCHITECTURE.md](../ARCHITECTURE.md), [SECURITY.md](../SECURITY.md), [DEVELOPMENT.md](../DEVELOPMENT.md), and [frontend-foundation.md](../../evidence/frontend-foundation.md).
- Backend handover baseline: `51e4ec1`; first frontend implementation checkpoint: `d081007`.
- Round 1 reviewed snapshot: `d081007..54d02cf` (working tree clean at review time).
- Owned paths: frontend templates/assets/tests, minimal presentation-serving URL/view integration, related API/README/tracker/evidence documentation and `.vscode/settings.json`.

## Review metadata

- Reviewer: independent Astra Medium (`gpt-6-astra`, reasoning `medium`), reviewer agent `Euler` (`01a09479-885e-7092-a925-2a86251249ae`).
- Date: 12 September 2026.
- Review mode: read-only; reviewer did not edit, stage, commit, deploy or delegate.
- Round 1 checks: targeted diff/spec/source inspection, `git diff --check`, focused frontend tests (`4 passed in 0.43s`), HTTP checks for `/`, `/foundation/design-notes/`, missing route and `/health/`. Reviewer did not repeat browser or full-suite checks in this round.
- Reviewer limitation: model settings were not exposed to the reviewer runtime for independent certification; the coordinator assigned the explicit Astra Medium settings above. Browser/visual claims remained attributed to the coordinator’s evidence record.

## Findings and remediation

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| F-001 | Major | `src/templates/foundation/home.html:114-121` | `docs/FRONTEND.md` validation states | The form only showed disabled controls; it lacked an invalid field, associated error text and `aria-invalid` example. Add a clearly labelled presentation-only validation state with shared styling and an accessible error association. | Fixed in remediation batch: invalid readonly sample uses `aria-invalid="true"`, `aria-describedby`, a visible error and shared `.form-field--invalid`/`.form-error` styles; focused frontend tests `5 passed`, live browser inspection confirmed the attributes and text. | Pending Round 2 |
| F-002 | Minor | `src/templates/foundation/home.html:141-146`; `src/static/js/site.js:48-58` | `docs/FRONTEND.md` dependency/error states | The HTMX interaction handled loading/success but no request failure feedback or usable retry. Add scoped announced failure feedback and a retry path; record an actual failed-request check. | Fixed in remediation batch: presentation-only `/foundation/design-notes-unavailable/` returns 503, scoped `htmx:afterRequest` builds static error DOM, changes the success action to “Retry design notes” and restores it after success; HTTP and browser 503/retry checks passed. | Pending Round 2 |
| F-003 | Minor | `src/static/css/site.css:857-859` | Accessibility requirement for visible focus | The focus handoff targeted the returned heading, but CSS removed its outline without a replacement. Give the focused heading a visible indicator and verify keyboard activation through the swap. | Fixed in remediation batch: programmatically focused fragment heading has a visible `solid` `2.4px` outline in the live browser after both failure and success swaps. | Pending Round 2 |
| F-004 | Minor | `src/static/css/site.css:208-218`; `src/static/css/site.css:1088-1091` | `DESIGN.md` mobile touch targets | The mobile Menu target had no minimum height and System status was explicitly 38px, below the stated 44px target. Provide 44px hit areas and record measured dimensions. | Fixed in remediation batch: mobile browser measurement at `390x844` found Menu `44px` high and System status `44px` high; responsive nav behavior remained correct. | Pending Round 2 |
| F-005 | Minor | `evidence/frontend-foundation.md:3,7,55` | Review scope/evidence accuracy | `d081007..54d02cf` excluded the initial frontend implementation introduced by `d081007`, while the evidence claimed it was the complete task diff. Correct the baseline to the backend handover commit and distinguish the reviewed range. | Fixed in remediation batch: evidence and tracker now use `51e4ec1` as the backend handover baseline and identify the first frontend checkpoint separately; complete task scope includes all new templates/assets/docs/tests. | Pending Round 2 |

## Round 2

Round 2 is required after the fixes. It must review the complete frontend task diff from the corrected backend handover baseline `51e4ec1` through the final remediation commit, preserve finding IDs, and record any new findings separately. Completion requires no unresolved actionable findings, relevant checks and browser/HTTP evidence recorded.
