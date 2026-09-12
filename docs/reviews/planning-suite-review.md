# Planning suite: independent review handover

Recorded: 12 September 2026. Status: DOC-001 and DOC-002 resolved at the foundation contract/persistence boundary; DOC-003 documentation correction recorded below. Resolve open findings before dependent implementation. This records the earlier independent read-only documentation review from the planning conversation, not a new review or a claim that fixes were verified.

Reviewer: independent agent `/root/review_docs`. Model/reasoning was inherited and not separately verified in that review; do not label it an Astra Medium backend review. The review preceded the mandatory backend review-loop policy. Coordinator has transcribed the findings here for continuity.

Review scope: AGENTS.md, PROJECT_SCOPE_INF2006.md and the eleven docs contracts. Existing README, manifest and data dictionary were consulted to check scaffolding. No implementation existed. Reviewed working-tree planning documents preceded commit `5d789e8`; that commit also contains later policy/ownership updates, so it is not an exact review snapshot.

## Findings

| ID | Severity | Relevant contract | Finding and expected correction | Status |
|---|---|---|---|---|
| DOC-001 | P2 | [Schema](../SCHEMA.md), [analytics](../ANALYTICS.md), scope section 5 | Analytics requires aligned historical inventory, but the schema only specifies mutable Product stock. Define persistence and selection of an immutable dated snapshot (or explicitly isolated historical fixture state), separate from live checkout stock. Test that a live purchase cannot change historical coverage on recomputation. | Resolved in foundation batch 3 independent review; workflow regression deferred to implementing task |
| DOC-002 | P2 | [Data pipeline](../DATA_PIPELINE.md), [schema](../SCHEMA.md) | Idempotent import prevents duplicate rows but does not define protection for mutable state or identities across historical/demo/load modes. Define field update ownership and fixture namespaces/isolation. Make supplemental stock seeding create-only by default; require explicit controlled reset for overwrites. Test reimport after checkout preserves stock, live orders and authentication state. | Resolved in foundation batch 3 independent review; workflow regression deferred to implementing task |
| DOC-003 | P2 | [Infrastructure](../AWS_INFRASTRUCTURE.md), scope section 7 | Infrastructure permits request-count or CPU target tracking, whereas the scope selects ALBRequestCountPerTarget. Keep request count as baseline and label CPU an alternative requiring a documented scope decision. | Corrected during teammate-document adoption; coordinator verified contract alignment, no runtime claim |

Verdict: broadly coherent and sufficient for scaffolding. These are contract clarifications within the agreed scope, not additional product features. No Low remediation or second review occurred; no repeated-finding stop has been triggered.

Minor non-blocking note: scope section 10 repeats phase and weekly schedules. Avoid drift; consolidation is optional.

Missing exact versions, field precision/deletion rules, fragment IDs, health thresholds and executable commands were intentionally marked pending, not review defects. Finalise them at relevant implementation gates and record real checks. The planning conversation's local link check found no broken local links across 14 planning Markdown files; this is not runtime validation.

## Next action

Foundation agent should resolve the remaining DOC-001 and DOC-002 findings in the affected contracts before dependent implementation, record corrections here and run appropriate review/checks. Follow the current AGENTS.md backend review gate for subsequent backend work. Do not assume the proposed snapshot table or reset design is already implemented.

## Foundation contract correction: DOC-001 and DOC-002

12 September 2026: coordinator clarified immutable inventory selection (stock and lead time, namespace/version/cutoff, no live fallback) in SCHEMA/ANALYTICS, and create-only import, field ownership, namespace isolation and controlled reset rules in DATA_PIPELINE/SCHEMA before dependent implementation. Original findings above are retained as review history. Contract corrections await the foundation independent review; importer/checkout/aggregation regression execution remains explicitly deferred to those implementation tasks.

## Documentation correction: DOC-003

The infrastructure contract now explicitly selects ALBRequestCountPerTarget and labels CPU an alternative requiring a scope decision, matching scope section 7. Coordinator checked the two documents for consistency. This is a documentation correction, not an independent backend implementation review. DOC-001 and DOC-002 remain for foundation work.

Foundation implementation update: initial migrations now enforce sealed inventory/version immutability and namespace alignment. Forty foundation tests pass, including separation of live stock/lead time from historical inputs. DOC-001/002 contract correction and persistence evidence are submitted to the batch 3 independent reviewer; future importer/checkout/aggregation workflow tests remain unrun, not passed.

Independent foundation review (12 Sep 2026): /root/review_batch3, explicitly Astra Medium, found no actionable findings in the batch 3 staged diff against b137d63. DOC-001/002 corrections accepted at contract/persistence scope. See [batch 3 review](foundation-batch-3.md). Preserve prior text as historical review sequence; the earlier Next action is now satisfied for foundation. Import-after-checkout and aggregation-recompute tests remain follow-up requirements.
