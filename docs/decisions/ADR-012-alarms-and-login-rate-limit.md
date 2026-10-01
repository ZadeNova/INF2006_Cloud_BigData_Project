# ADR-012: Three alarms, saved log queries, and a WAF rate limit on `POST /login/`

**Status:** drafted by the writing session for review (1 October 2026). Thresholds are starting points, recorded and tuned from the failure tests.

## Decision

- **Alarms to the SNS topic** (email): unhealthy targets above 0 for 2 minutes; fewer than 1 healthy target for 2 minutes (missing data counts as breaching); more than 5 target 5xx responses in a minute, twice running. Each also emails when it clears.
- **Two saved CloudWatch Logs Insights queries** over the app's JSON log lines: recent errors and security warnings, and their count per minute by level.
- **One regional WAF web ACL on the ALB** with one rate-based rule: more than **20 `POST /login/` requests per client IP in 5 minutes**. It starts in **count** mode and is switched to **block** (a 403) with `waf_login_action = "block"` for the security test. No managed rule sets.

## Options considered

| Option | Why not |
|---|---|
| Many alarms (CPU, latency, memory) | Each needs a threshold and a response; these three are the conditions a person would act on |
| Alarm on the app's log lines through a metric filter | The ALB already publishes 5xx counts; a filter adds a second path for the same signal |
| Managed WAF rule sets | Cost, and they inspect traffic this small app does not need blocked; the named threat (T7) needs one rule |
| Rate limiting in Django | The backend is frozen; the WAF rule needs no code change |
| Block from the first day | A mis-set limit could lock out the operator; count first shows what would be blocked |

## Driver (shop scenario)

An always-open shop with one operator needs to learn quickly that it is down or failing, and the one threat the brief names for this service, password guessing against the login, needs a control that can be shown working. WAF costs about USD 6 a month plus per-request charges, which is justified by that.

## Consequences

- 20 attempts per 5 minutes is far above a person's logins and far below credential stuffing; a shared office IP could trip it, which the report states.
- The load test sends `POST /login/` requests from one machine, so the limit is raised or counted during scaling runs, and that is recorded.
- Alarms need the SNS subscription confirmed (done on 29 September).

## Evidence that will back it

An alarm firing on a killed instance and its email; the Logs Insights result exported; a burst of `POST /login/` returning 403 in block mode and the WAF sampled requests and `BlockedRequests` metric; the same burst counted in count mode.

## Revisit when

The tests show a threshold firing on normal use or missing a real failure.
