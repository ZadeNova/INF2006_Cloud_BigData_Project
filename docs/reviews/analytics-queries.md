# Analytics queries review

Task ID `analytics-queries`. Round 1 of the independent backend review gate ([DEVELOPMENT.md](../DEVELOPMENT.md#backend-review-gate)); brief: [astra-review.md](../archive/plans/astra-review.md). Report received 20 September 2026 from the project's teammate running Astra as the independent reviewer (model and reasoning level are not stated in the report). Log written by the coordinator (the user with Claude Code) from that report.

- **Base and snapshot:** `470becd..788f545`. Reviewed PR head `d0922916e12c9df6c582c369032b70c975c967b4`.
- **Owned paths:** `src/reporting/queries.py`, the snapshot half of `src/reporting/services.py`, `src/reporting/management/commands/snapshot_inventory.py`; tests `test_analytics_queries.py`, `test_analytics_snapshot.py`.
- **Specs:** [ANALYTICS.md](../ANALYTICS.md), [SCHEMA.md](../SCHEMA.md) inventory sections, plan [batch-06b-analytics-refresh.md](../plans/batch-06b-analytics-refresh.md).
- **Status:** Gate cleared. Round 2 resolved AQRY-001 and AQRY-002; KO-1 is **partially resolved** (owner-accepted mitigation, not a repeat). Rounds 3 and 4 did not reopen them (final head `7eea9b7`). Fixes were made by the user with Claude, not Astra Low.

## Checks and limitations

Environment: built from Git into a separate Docker image with pinned dependencies and PostgreSQL, disposable database, non-superuser role; fresh migrations, `manage.py check` and `makemigrations --check --dry-run` passed; full suite 301 passed. The literal root Compose commands were not run; the host checkout was not edited.

Task-specific: the query and snapshot tests passed, and both findings below were reproduced against PostgreSQL. Fixed query counts, exact normal-sized thresholds, zero-sales behaviour, leap-day coverage and immutable-snapshot behaviour are covered by the passing suite.

## Findings

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| AQRY-001 | High | `reporting/queries.py:69` | SCHEMA permits nonnegative integer stock; ANALYTICS requires an exact flag threshold. PostgreSQL reproduction: stock 400,000,000, seven units sold, seven-day lead time. | `stock * 7` overflows PostgreSQL's integer type and makes the entire coverage query fail with `DataError: integer out of range`. The numeric cast in the separate coverage-days expression does not protect the flag expression. Cast before multiplication, using numeric arithmetic for the comparison, and add a regression at a valid large stock value. | Fixed: `s.stock::numeric * 7` in the flag comparison. Verified: regression at stock 400,000,000 and at the maximum valid stock and lead time (exactly at the threshold); with the old SQL both raise `DataError: integer out of range`. | Resolved (round 2, `d092291..b282a60`) |
| AQRY-002 | Medium | `reporting/services.py:239` | SCHEMA inventory rules and batch 6b: `snapshot_inventory` must produce a sealed version usable by refresh. | An existing **unsealed** version with matching cutoff and rows is accepted as "Verified unchanged". Reproduced a successful result with `version.sealed == False`; refresh will reject that version. Reject unsealed existing versions with an actionable error, or explicitly validate and seal them under the appropriate lock. Add the missing replay test. | Fixed: an existing unsealed version is rejected with "not sealed" before any comparison. Verified: unsealed replay test, and a matching sealed version made elsewhere is still verified unchanged. | Resolved (round 2, `d092291..b282a60`) |

## Known open item KO-1 (existing, not a new finding)

`snapshot_inventory` captures live stock when it runs but accepts any past `--as-of`. Reviewer assessment: **High**, because backdating today's stock can produce misleading historical coverage and replenishment flags. Restricting the command to today's Singapore date is the safer proposed default; an `--allow-past` flag only acknowledges the mismatch and does not recover historical stock. Even with a today-only rule the command captures stock at execution time while labelling the cutoff midnight, so the owner must decide whether that is an explicitly disclosed live-demo approximation or whether actual cutoff-aligned stock is required before KO-1 is called fully fixed.

**Owner decision (20 September 2026): option 1, today-only guard plus disclosure; implemented; round 2 judged it a partially resolved, owner-accepted mitigation (not a repeat).** `snapshot_inventory` accepts only today's Singapore date (any other date is refused), and the disclosed approximation is recorded in ANALYTICS.md and the 6c dashboard plan. KO-1 is recorded as mitigated with disclosure, not fully fixed: capture time still differs from the midnight label. Original coordinator recommendation: today-only guard plus explicit disclosure (ANALYTICS.md and the dashboard footer), recorded as mitigated, not fixed. Reasoning: the application has no restock path (stock only decreases through checkout), so stock captured after midnight is at most the true cutoff stock and the bias is conservative (coverage understated, flags slightly over-eager). That reasoning breaks if a restock feature is added.

## Other observations

The query returns a numeric average alongside `insufficient_history`. No separate finding: the planned dashboard (batch 6c) owns hiding numeric metrics in that state. Verify when 6c lands (added to the 6c plan and tests).

Decision: KO-1 decided by the owner (see above).

## Re-review history

Rounds 2 to 4 of the independent review are done and the gate is **cleared at `7eea9b7`** (round 4, 22 September 2026). Fixes were made by the user with Claude, not Astra Low. Astra's round reports are PR #1 comments; this section is the concise record.

| Round | Snapshot | Result |
|---|---|---|
| 2 | `d092291..b282a60` | 429 tests, fresh migrations, `manage.py check` and `makemigrations --check --dry-run` passed on the reviewed snapshot (Astra). AQRY-001 and AQRY-002 resolved. KO-1 partially resolved: today-only Singapore date enforced and disclosed in ANALYTICS.md, but stock is still captured at run time under a midnight label; recorded as the owner's accepted mitigation, not a failed fix |
| 3 | `b282a60..282a1ec` | Bounded to the SEC-001 fix and the test trim; this task's findings were not reopened. |
| 4 | `282a1ec..7eea9b7` | Bounded to the R3-001/R3-002 fixes; this task's findings were not reopened. Gate cleared. |
