@AGENTS.md

# Instructions

AGENTS.md is the authoritative source of truth for this repository.
Read it before making changes.

Follow all conventions, architecture decisions, and constraints defined there.
If instructions conflict, AGENTS.md takes precedence.

# Claude Code session role

This Claude Code session and the user implement backend/frontend features
together directly, for learning purposes, following
docs/IMPLEMENTATION_PLAN.md. The AGENTS.md-mandated Astra Low/Astra Medium
review-gate loop is a separate track: Astra reviews this work when the user
pushes changes or opens a pull request. This session does not simulate,
substitute for, or auto-run that review gate; work done here is tracked as
implemented-pending-review until Astra's review happens on push/PR.
