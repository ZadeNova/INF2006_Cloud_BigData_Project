# Claude Code Session

AGENTS.md is the authoritative source of truth for this repository.
Read it before making changes.

Follow all repository conventions, architecture decisions, and constraints
defined there.

## Context and Implementation

Before implementing or modifying anything:

1. Read the current relevant status/next step in
   `docs/IMPLEMENTATION_PLAN.md`.
2. Identify and read the relevant sections of the project's contracts and
   documentation based on the task.
3. Inspect the relevant existing code, tests, configuration and dependencies.
4. Check Git status and preserve unrelated changes.

Do not implement based only on the user's description when relevant
repository code, documentation or contracts can provide additional context.

Use targeted reading rather than recursively loading the entire repository.
Read only the material necessary for the current task, while ensuring
sufficient context for correctness.

## Operating Modes

The user can explicitly switch between two modes.

### Learning Mode

Goal: implement features while helping the user understand the framework
and implementation.

- Explain relevant Django/framework concepts and important design decisions.
- Briefly explain request/data flow when useful.
- Prefer simple, idiomatic framework patterns.
- Claude may implement the requested code; the user does not need to write
  every line manually.
- Keep explanations proportional to the complexity of the task.

### Heavy Implementation Mode

Goal: maximize implementation speed and correctness.

- Prioritize completing the requested work.
- Inspect the relevant code, documentation and contracts before editing.
- Implement directly and minimize unnecessary explanation.
- Run appropriate checks and fix issues encountered.
- Do not introduce unnecessary abstractions or unrelated refactors.

Default to Learning Mode unless the user explicitly requests
Heavy Implementation Mode.

## Review Workflow

Astra is the independent reviewer for this project.

Claude Code is the implementer and must not act as, simulate, or substitute
for the Astra review.

After implementation, the work is considered:

`implemented-pending-review`

The review does not happen automatically or immediately after implementation.

The user may push the changes or open a PR, after which the separate Astra
review workflow reviews the work according to `AGENTS.md` and
`docs/DEVELOPMENT.md`.

Do not claim that work has passed review unless an actual Astra review has
occurred and its result is available.

Do not repeatedly review your own implementation in an attempt to simulate
Astra. Claude may run normal implementation checks and tests, but these are
not equivalent to the independent Astra review gate.

If the user asks for a self-review, clearly label it as a Claude self-review
and do not represent it as the Astra review.

When a self-review (requested, or run via the code-review skill as part of
finishing a task) surfaces code smells, bugs or other findings, report every
finding to the user before fixing anything. The user reviews each finding and
decides whether it needs to be fixed. Only implement a fix after that
decision, unless the user has explicitly authorised fixing self-review
findings autonomously for that specific task.

## Git

Whenever creating a commit, ensure that it is authored to the User.
