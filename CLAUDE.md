# Claude Code Session

`AGENTS.md` is the authoritative source of truth for this repository.
Read it before making changes and follow its conventions, architecture,
and constraints.

## Operating Modes

The user can explicitly choose between two modes.

### Learning Mode — Default

Goal: help the user understand the implementation while building it.

- Explain relevant framework concepts and important design decisions.
- Briefly explain request/data flow and unfamiliar patterns when useful.
- Prefer simple, idiomatic solutions over clever abstractions.
- Claude may implement the requested code; the user does not need to write
  every line manually.
- Keep explanations proportional to the complexity of the task.

### Implementation Mode

Goal: maximize implementation speed and efficiency.

- Prioritize completing the agreed implementation.
- Minimize explanations unless clarification is important.
- Inspect the relevant code and documentation before editing.
- Implement directly within the agreed scope.
- Avoid unnecessary abstractions, refactors, and exploration.
- Follow the same testing, review, commit, and push gates as Learning Mode.

The user may switch modes at any time.

## Workflow

Follow this workflow unless the user explicitly changes it:

`Discuss/Plan → Implement → Test → Self-Review → Fix → Test → Commit → Push`

### Discuss / Plan

Before implementation:

- Read the relevant status in `docs/IMPLEMENTATION_PLAN.md`.
- Read relevant contracts and documentation.
- Inspect relevant code, tests, configuration, and dependencies.
- Check Git status and preserve unrelated changes.
- Discuss important design decisions with the user.
- Write the finalized implementation plan to `docs/plans/` before
  implementation.

Do not begin implementation until the plan is sufficiently clear.

### Implement

Implement only the agreed scope.

- Do not modify unrelated files.
- Avoid unnecessary abstractions or refactors.

### Test

After implementation:

- Run the smallest relevant tests by default.
- Do not automatically run the full test suite.
- Do not start the application, Docker, databases, or other services
  unless required for verification.
- Avoid redundant or expensive verification.

Tests should cover behavior introduced or changed by the implementation.

### Self-Review

Claude may perform a self-review as an early guard before the independent
Astra review.

- Clearly label findings as a `Claude self-review`.
- Do not represent self-review as independent review.
- Report all findings before fixing anything.
- Wait for the user to decide which findings should be fixed unless the
  user explicitly authorized autonomous fixes.

### Fix

Fix the findings approved by the user.

Do not expand the scope with unrelated improvements.

### Final Test

After fixes:

- Run targeted tests covering the affected behavior.
- Run broader tests only when justified by the change or explicitly requested.
- Do not repeatedly run unchanged expensive checks.

### Commit

Never commit automatically.

Only create a commit when the user explicitly asks for one.

Before committing:

- Verify the intended files are included.
- Ensure unrelated changes are excluded.
- Ensure the implementation and tests are in the intended final state.
- Author the commit to the User.

### Push

Never push automatically.

Only push when the user explicitly asks.

Do not create PRs, merge, reset, revert, or discard changes unless explicitly
instructed.

## Cost

The user has limited credits.

- Prefer direct tools over subagents.
- Do not launch multiple agents by default.
- Use targeted investigation and testing.
- Avoid unnecessary repeated commands.
- Use low/medium effort for self-review unless a deeper review is explicitly
  requested.
