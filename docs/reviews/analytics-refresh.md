# Analytics refresh review

Task ID `analytics-refresh`. Round 1 of the independent backend review gate ([DEVELOPMENT.md](../DEVELOPMENT.md#backend-review-gate)); brief: [astra-review.md](../archive/plans/astra-review.md). Report received 20 September 2026 from the project's teammate running Astra as the independent reviewer (model and reasoning level are not stated in the report). Log written by the coordinator (the user with Claude Code) from that report.

- **Base and snapshot:** `91ba04e..470becd` (includes `41ea463`). Reviewed PR head `d0922916e12c9df6c582c369032b70c975c967b4`.
- **Owned paths:** `src/reporting/migrations/0003_completed_sale_lines_view.py`, `src/reporting/ranges.py`, the refresh half of `src/reporting/services.py`, `src/reporting/management/commands/refresh_analytics.py` and `_args.py`; tests `test_analytics_ranges.py`, `test_analytics_view.py`, `test_analytics_refresh.py`, `analytics_helpers.py`.
- **Specs:** [ANALYTICS.md](../ANALYTICS.md), [SCHEMA.md](../SCHEMA.md), plan [batch-06b-analytics-refresh.md](../plans/batch-06b-analytics-refresh.md).
- **Status:** Round 1 complete; **no actionable findings**.

## Result

No actionable findings in this task's reviewed diff.

## Checks and limitations

Environment: built from Git into a separate Docker image with pinned dependencies and PostgreSQL, disposable database, non-superuser role; fresh migrations, `manage.py check` and `makemigrations --check --dry-run` passed; full suite 301 passed. The literal root Compose commands were not run; the host checkout was not edited.

Task-specific: the range, SQL-view and refresh tests passed, including Singapore date boundaries, leap dates, rollback, statement timeout, advisory-lock contention and retention. The `reporting.0003` view migration reversed to `0002` and reapplied successfully in the disposable database.

Limitations: no real-dataset or pandas comparison and no scheduler-host-loss exercise was run. The independent pandas cross-check is still queued (see [analytics-status.md](../archive/plans/analytics-status.md)); this review does not mark it delivered. No owner decision identified for the implemented refresh task.

## Findings

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| none | n/a | n/a | n/a | No actionable findings. | n/a | n/a |
