# Foundation pre-push review

Date: 12 September 2026. Round 1 findings followed by focused round 2 below. Original recommendation: **hold the proposed push for FP-001 and FP-002 correction and focused re-review**. No actionable backend or Docker foundation defect was found. The findings concern delivered foundation behavior and handover accuracy, not deferred ecommerce, dataset, analytics or AWS delivery.

## Reviewed boundary and independence

- Exact range: `f719c679a73e1173d2f2dd8caf832ec9b1a2e385..72fc206a10c2fba1914bdb9f4997074da6df2a34` (baseline excluded, final commit included).
- First checks: `git status --short`, `git rev-parse HEAD`, `git log -5 --oneline`. HEAD matched expected `72fc206`; the working tree was clean. No newer changes existed. HEAD and clean status were checked again after runtime work, before this report was written.
- Scope: all 91 changed paths in the complete foundation diff, with targeted dependency/contract inspection. No recursive repository-content reading. Tracked-path enumeration was used specifically to check proposed-push artifacts.
- Coordinator `/root` conducted Docker/runtime, frontend/browser and documentation review and wrote this report. It did not implement the reviewed foundation. Independent backend reviewer `/root/backend_review` was explicitly assigned `gpt-6-astra`, reasoning `medium`, read-only; it inspected configuration, models, every domain migration/guard, tooling, tests and contracts and independently confirmed the boundary/whitespace checks. It did not run Docker checks; runtime results below are coordinator-performed. Coordinator model settings were not independently certified; browser work is additional review evidence, not a claim of Luna Max implementation verification.
- Read AGENTS, tracker, relevant scope sections 2-4 and 8-9, DESIGN and routed development/architecture/testing/frontend/API/security/schema/data/analytics contracts. Consulted foundation batch 1-4, planning, frontend, superseded startup-shortcut and root-Compose reviews and their evidence. Prior approvals were not treated as proof.
- Only this report is changed. No fixes, staging, commits, push or AWS actions were performed. The tracker is deliberately unchanged under the user's report-only restriction.

## Prioritized findings

| ID | Priority | File/line | Requirement | Finding, impact and suggested correction | Remediation / re-review |
|---|---|---|---|---|---|
| FP-001 | P2 | `src/static/css/site.css:109-115`, `src/static/css/site.css:667-669`; anchor links at `src/templates/base.html:27-30` | Scope section 3 frontend reference; `docs/FRONTEND.md:19-23`: usable responsive layout and keyboard navigation | At 390x844, open Menu with Enter and activate States with Enter. Once smooth scrolling settles, `#states` starts at approximately 0px, its heading starts at 95.75px, but the sticky header ends at 136px. The header visibly obscures the beginning of “States are part of the product.” There is no scroll offset accounting for the sticky header. A user following the delivered navigation loses the destination heading/context; this also affects direct fragment navigation. Add responsive `scroll-margin-top` on anchor targets or suitable `scroll-padding-top`, accounting for the mobile header's actual wrapped height. Verify Overview/Patterns/States and the skip link at mobile/tablet/desktop widths with keyboard activation and settled scrolling. | New; not fixed in this review. Frontend owner: Luna Max, then independent focused re-review. |
| FP-002 | P3 | `docs/FRONTEND.md:9`; related stale summary `README.md:141` | AGENTS documentation ownership; development handover accuracy; current tracker/API route contract | The current frontend contract says “foundation implements only health” although `/`, both design-note routes and branded 404 are delivered. README's limitation also says frontend evidence remains pending without distinguishing the completed foundation evidence from future business-workflow evidence. These statements conflict with API/tracker/evidence and mislead the next implementer about the integration surface. State the delivered presentation routes or link to API as owner, and qualify the README limitation as future business-frontend evidence. Preserve historical batch evidence as history. | New; documentation-only correction by coordinator, then consistency recheck. |

No credentials, generated runtime artifacts, unintended business routes, unsafe template rendering or material dead-code/complexity defect was identified in the proposed diff. Shared CSS variants are reasonable foundation components, not automatically dead code because the preview does not use every variant. No premature claim of complete authentication, cart, checkout, dataset acceptance, analytics execution or AWS delivery was found in the tracker; Phase 1 correctly remains in progress.

## Independently performed checks

Runtime: Docker Desktop Linux containers, Compose **5.1.4**, Python **3.13.15**, Django **5.2.17**, PostgreSQL **17.11**. Commands ran from the repository root. Root `docker compose config --quiet` passed. Normal-project `docker compose ps` showed no running services. Docker named-pipe access required sandbox escalation, which was granted.

All lifecycle experiments used `$env:APP_PORT='18006'` and `docker compose -p foundation-prepush-72fc206 ...`, retaining root configuration discovery/include and isolating containers, network and volume from the normal project. Existing `src/.env` was reused without printing or modifying it. The configured shared application image tag was rebuilt from the exact reviewed source; no existing image/cache was deleted.

| Check / command | Actual result |
|---|---|
| `git diff --check f719c67..72fc206` | Passed, including independent backend reviewer check. |
| `up --build -d --wait --wait-timeout 90` with a newly created review volume | Passed. Pinned images resolved, image built, static collection ran, database initialized, all 21 migrations applied, migrate exited 0 before web started and became healthy. Build reused dependency layers; this was a fresh database, not a cache-free install. |
| `exec -T web pytest -q -p no:cacheprovider /app/tests` | **53 passed in 3.04s**, real isolated PostgreSQL test database. Independently reproduces the current reported count. |
| `exec -T web python manage.py check` | No issues, zero silenced. |
| `exec -T web python manage.py makemigrations --check --dry-run` | No changes detected. |
| `exec -T web python manage.py check_database` | Exit 0, database ok / migrations applied. Repeated successfully after failure recovery. |
| `exec -T web python -m pip check` | No broken requirements. Harmless non-writable pip-cache warning under the non-root UID. |
| `up -d --wait --wait-timeout 60` repeated | Passed; one-off migrate reran and reported no migrations to apply. An already-running unchanged web container stays running; the dependency is a startup gate, not a mechanism to quiesce existing workers. |
| `stop db`, HTTP health and `check_database`, followed by DB restart in `finally` | Health remained 200 with `{"status": "ok"}`; readiness exited 1 with sanitized `Database unavailable.` No credentials/connection details exposed by that command. |
| `exec -T web python manage.py migrate reporting 0001 --noinput`, then readiness, then `up` | On the empty review domain tables only: guard reversal succeeded; readiness exited 1 with `Database migrations are pending.` Subsequent up reapplied the guard migration and passed. |
| `down`, volume inspection, then `up -d --wait --wait-timeout 60` | Passed. Review volume survived down, and migration-record count remained **21** across recreation. No business/session persistence claim is inferred from this metadata check. |
| Injected migration failure | In the review DB only, deleted the `sessions/0001_initial` migration-recorder row while retaining its table, stopped web, then ran up. Duplicate-table migration failure made up exit 1; migrate exit code was 1 and web remained `exited`. Restored the recorder row through `run --rm --no-deps web ...`; no source edits. Subsequent `up --build -d --wait --wait-timeout 60` recreated services successfully and readiness passed. |
| Runtime secret/privilege checks | `/app/.env` absent; `POSTGRES_ADMIN_PASSWORD` absent from web environment; web UID/GID 10001. Compose source supplies bootstrap password only to db. Image/ignore rules and tracked paths show no committed environment secrets, private keys, state, bytecode, virtualenv or staticfiles output. This is targeted inspection, not an exhaustive secret-scanner certification. |

The include resolves build/init-script/tests paths under `src/` as intended, discovers `src/.env`, and preserves the normal project/volume naming. Missing required environment values fail interpolation by inspection. README accurately requires initialization and Compose 2.20+ for root include, rebuild after code changes, no concurrent deployment, and avoids implying that editing `.env` rotates an existing database password. `down` without volumes preserves data as independently exercised. The manifest's older explicit `-f src/compose.yaml` commands remain executable, although they redundantly request migrations now that a migration service exists.

## Browser and HTTP review

Actual Gunicorn/Django routes at `http://127.0.0.1:18006` were checked, not a static HTML substitute. Independent HTTP requests returned `/` 200, success fragment 200, intentional failure fragment 503, missing route 404 and `/health/` 200 JSON. The full suite verifies GET/HEAD health, no-store/no cookies/zero queries, Host policy, safe methods and production settings.

- In-app browser inspected desktop **1440x900**, tablet **768x900**, mobile **390x844**. Shared green/cream palette, system-font fallback, rounded components, labeled samples and own branding align with the scoped reference. Desktop has two-column hero and three-column states; mobile has one column. No horizontal document overflow at these measured widths. Desktop header 99px; mobile Menu/System status each 44px. Mobile header wraps to 136px, which exposes FP-001.
- Menu Enter opens navigation and focuses Overview; Escape closes and restores Menu focus. Selecting States closes navigation and reaches the fragment but obscures its heading, as recorded in FP-001 and observed in the screenshot.
- Keyboard activation of Load design notes fetched/swapped the live fragment, kept the preview URL, set polite/status feedback and focused the returned heading with visible 2.4px solid outline.
- Preview failure state made the deliberate 503 request, showed assertive/alert feedback, focused the error heading with visible outline and exposed Retry design notes. Keyboard retry restored success, label and focus. Browser log showed only the expected HTMX response-status error for the deliberate 503 during interaction inspection; no JavaScript exception observed.
- Invalid readonly sample is labeled, has `aria-invalid` and associated error text; Save sample is disabled. No foundation browser mutations/business forms require a CSRF token yet; middleware and reserved later POST/HTMX CSRF contracts remain in place. No `safe`/untrusted HTML insertion was introduced; client error DOM uses static textContent.
- Branded 404 was visited and its return link successfully navigated to the foundation. Screenshots/DOM observations were emitted in this review session; no screenshot files were added, respecting the report-only repository change restriction.

## Earlier findings and test quality

- **B1-001 remains resolved**: concrete package paths and pinned dependency workflow are documented.
- **DOC-001/002 remain resolved at contract/persistence scope**: sealed immutable historical stock/lead-time versions, namespace protections and explicit create-only reimport rules remain intact. Actual importer-after-checkout and aggregation recomputation are deferred and not claimed as tests passed. DOC-003 remains aligned with request-count scaling in scope; AWS is unverified.
- **F-001 through F-005 remain resolved**: validation sample, failure/retry, heading focus indicator, mobile control size and corrected complete frontend baseline persist. The browser repeated the applicable behavioral checks. FP-001 is a distinct anchor-offset defect, not recurrence of the HTMX heading-outline issue.
- Prior foundation batches 2-4 and root-Compose review had no actionable findings to reopen. The removed startup wrapper record is explicitly superseded; its tests are not evidence for Compose.
- Schema tests exercise real PostgreSQL rejection boundaries, protected references, namespace separation, sealed inventory and historical/live independence; they are meaningful foundation checks. Health/settings tests combine actual requests/configuration boundaries with narrow failure mocks. Frontend tests meaningfully check routing/templates/methods but mostly assert HTML, so they cannot establish layout or JS behavior and did not catch FP-001. Browser observations supplement them. No concurrency, complete analytics, authentication or cloud evidence is inferred from these 53 tests.

## Limitations, cleanup and handoff

No cache-free dependency install, alternate CPU platform, minimum Compose 2.20 runtime, fresh-host missing-env initialization, screen-reader speech, exhaustive contrast/zoom audit, CDN outage, TLS/RDS/ALB, business workflows, dataset acceptance or AWS checks were performed. Dependency pins/installed compatibility were checked; this is not a current vulnerability-database audit. Tests ran before the subsequent lifecycle fault injections; restored readiness and successful rebuilding were verified afterward. Failure injection used an existing empty schema, not a destructive migration or partial data migration. Attached interactive Ctrl-C behavior was not separately tested; up/build used detached wait flags and down was exercised.

Review-created containers/network were removed with down. Before removing the disposable volume, its exact name and Compose project label were verified as `foundation-prepush-72fc206_postgres_data` / `foundation-prepush-72fc206`. Only that created volume was deleted. Final review-project container and volume listings were empty. Normal-project volumes and secrets were never reset/deleted. Browser viewport override was reset and the review tab closed; build cache/shared application image retained.

Hand FP-001 to the frontend Luna Max owner and FP-002 to the documentation coordinator for a separately authorized fix task. Re-review the corrected complete foundation boundary and these stable IDs, including mobile anchor positioning. No backend fix was identified, so no Low remediation was started. If backend changes become necessary, use Astra Low implementation and independent Astra Medium review, preserving finding IDs and the mandated stop after a repeated unresolved finding. This report is a review handoff, not authorization to implement, commit or push.

## Round 2: focused remediation and independent re-review

Uncommitted fix boundary against 72fc206: src/static/css/site.css, README.md and docs/FRONTEND.md. FP-001 implemented by /root/fix_mobile_anchor (explicit Luna Max); FP-002 corrected by coordinator. Independent reviewer /root/fp_rereview (explicit Astra Medium) performed read-only diff/dependency and browser checks. Historical findings/results above are preserved.

| ID | Fix | Focused re-review outcome |
|---|---|---|
| FP-001 | Responsive CSS scroll-margin-top applied to Overview, Patterns, States and skip-link destination: mobile 136px, tablet 83px, desktop 99px. No template/JS/backend changes. | Original mobile defect resolved independently at 390x844: keyboard Menu/States; settled target top 136.15px, heading 231.75px, header bottom 136px. Heading visible in reviewer screenshot. |
| FP-002 | Frontend contract describes delivered presentation routes and links to API; README distinguishes completed foundation evidence from deferred business-frontend evidence. | Resolved by independent contract/API/tracker comparison. |

Reviewer confirmed served site.fdb4aac7427e.css includes fix, tablet header/offset 83px and desktop header/all four target offsets 99px; no horizontal overflow observed. No new actionable findings. No repeated unresolved issue, so escalation stop is not triggered.

Implementer reported successful rebuild, five passing frontend tests, desktop settled-target checks, direct-fragment and keyboard skip-link checks. Coordinator independently checked served CSS and documentation links. Tests cover route/template behaviour, not layout. Do not infer tablet/mobile full-matrix verification from the implementer's cross-reference to parent results.

Limitation: additional smooth-scroll animations stalled in the independent reviewer's hidden browser; visibility control is unavailable for that subagent. The entire Overview/Patterns/States/skip-link settled-scroll matrix was therefore not independently completed at every viewport. The original FP-001 reproduction and responsive offsets were checked as described. This is a verification limitation, not a recurring defect. Screen-reader/zoom/other Round 1 limitations remain.

Recommendation: both reported code/documentation findings are resolved with no new actionable findings; retain the above browser coverage limitation in handover. Full navigation matrix can be checked during final UI acceptance. No commit or push performed by this remediation task. Reviewer tab closed/viewport reset. Normal local app was started for verification and remains running; no volume or secret reset.
