# Development conventions

Status: pre-implementation. Package manager, runtime/framework versions, Compose service names and CI gates are not established. Do not copy devenv/uv/SPA commands or fixture accounts from the unrelated senior-engineer reference.

## Setup and layout

Use the scoped Django/PostgreSQL/Docker/Gunicorn/WhiteNoise/pytest/Locust stack. Pin compatible supported runtime, dependencies and images during scaffolding; choose one dependency workflow. Put verified setup/run/test commands in root README and src/README. Examples contain placeholder secrets only.

Preserve submission layout: src/ owns app/dependencies/infrastructure; data/ source metadata/fixtures; analytics/ reproducible entry points; tests/ repeatable checks; evidence/ dated results. docs/ owns contracts, AGENTS.md routing. Define concrete Django package/template paths in the scaffold change and update architecture.

## Code and verification

Follow AGENTS.md targeted-reading rules: consult relevant sections and scoped code/tests, reuse current context, and avoid routine recursive repository scans. Widen searches only when narrower inspection cannot resolve the task. Inspect patterns/status first, keep edits focused and preserve unrelated work. Prefer ordinary Django forms/ORM and explicit business functions over speculative abstractions. Use readable names and cohesive functions; document non-obvious transaction/date/idempotency decisions. Add useful boundary type annotations.

Include migrations with model changes; do not casually rewrite shared applied migrations. Use decimal money and aware timestamps; validate database-specific behaviour on PostgreSQL.

Use the configured project environment once established. Do not install unrelated global dependencies or claim example commands are a working standard. Start only needed local services; clean up services started by this task when appropriate, not unrelated existing services. Avoid publicly exposed development servers.

Run appropriate focused checks and any established gate; do not invent a gate. Documentation changes need link/consistency checks, not an app suite. Frontend behaviour requires live HTTP verification. Record results/unrun checks/limitations.

Update affected contracts, executable instructions and implementation status together. Update evidence when experiments run. A TODO file is not implemented functionality.

## Git and review

Follow the user's authorised Git scope. Make atomic commits with concrete messages such as `docs: define checkout contract`; inspect staged paths/diff and avoid broad staging. Do not mix unrelated changes or discard another contributor's work. Default new branch prefix is `CL/` when needed. No force-push/history rewrite without explicit authorisation.

PRs describe the problem/result, validation and material limitations; follow templates if present. One agent stages/commits per shared working tree. These rules are not blanket permission to publish future work; honour the actual commit/push request and destination.

Maintain source licences and AI-use records. Documentation creation does not itself authorise building the app or provisioning AWS. Follow the current task and phase tracker.

## Backend review gate

This is the canonical review procedure required by [AGENTS.md](../AGENTS.md). The user authorises a separate Astra Medium reviewer and Astra Low remediation for backend-owned work, including database, import/analytics, infrastructure and supporting tests. Apply it per coherent completed task/feature/fix, not per keystroke. Documentation-only and frontend-only changes do not require this backend gate; mixed tasks review the backend changes and relevant integration boundaries.

### Review handoff

- Record the task's starting commit and owned paths; identify pre-existing/unrelated changes. Freeze the review snapshot while the reviewer examines it. Include tracked edits and newly created task files; plain git diff alone omits untracked files.
- Give the independent reviewer `gpt-6-astra` / `medium`, the user requirement, relevant spec sections, exact diff/snapshot, changed paths and check outputs. Use explicit bounded context rather than a full-history fork when model overrides require it.
- Reviewer must not have authored the implementation. It performs read-only inspection and may run focused non-mutating checks where supported; no edits, staging, commits, deployment or further delegation.
- Check correctness, specification gaps, security, failure handling, dead/unreachable or obsolete code introduced/affected by the task, migrations and meaningful test coverage. Trace relevant callers/dependencies before declaring code dead. Do not turn stylistic preferences or unrelated legacy issues into invented blockers.

### Findings and remediation

The coordinator creates `docs/reviews/<task-id>.md` on the first review. It records task/spec links, base and reviewed snapshot identification, owned paths, reviewer model/identity, date, round, checks and limitations. Use a stable finding table:

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|

Include findings for mistakes, omitted requirements and dead code. Record 'no actionable findings' explicitly when appropriate. Keep round history and stable IDs; do not overwrite the first report. Link the review log from IMPLEMENTATION_PLAN rather than copying detailed findings there.

Hand actionable findings to Astra Low (the original Low implementer or an explicitly assigned Low fixer). Only one writer edits a given task scope. Low fixes the issues, reruns relevant checks and records the changed paths/results. Medium then re-reviews the updated task diff and prior findings; reviewing only a fix snippet is insufficient if it introduces regressions.

### Stop and completion rules

If a finding remains unresolved or recurs in the review following its Low remediation attempt, **stop the current task**. Match the underlying defect/requirement, not just wording or line number. Preserve the work and report the finding ID, both review outcomes, attempted fix, failing evidence and log path. Set tracker status to 'Awaiting user manual Astra Medium escalation'. Do not reset the task/finding ID, spawn another Low retry, upgrade implementation automatically, mark complete or publish the affected work.

If the second review finds only genuinely new issues, send those to Low and apply the same repeat-after-fix stop rule per finding. Disputed findings require evidence and reviewer resolution; a genuine unresolved spec ambiguity goes to the user, not silent dismissal. Reviewer inability to execute checks is recorded as a limitation, not a passed check.

Resume implementation after the user manually selects Medium and directs continuation. An independent Medium review remains necessary for the resulting fix; the implementing agent cannot approve its own work. The reviewer assignment itself never authorises escalation of implementation.

Complete the task only when review has no unresolved actionable findings, relevant checks are recorded and the tracker links the final review. Passing review does not replace tests or imply permission to commit/push. If required model/delegation capabilities are unavailable, stop at that gate and explain the limitation.
