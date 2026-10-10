# Report edits for the Google Doc (10 October 2026)

Apply in the Doc, then export as `report.pdf` at the repository root and delete the old long-named PDF.
"Find" texts are short, exact phrases from the current report; use Ctrl+H where the edit is a plain replacement.
Every figure below comes from `evidence/` (RES-04: `evidence/test-resilience.md#res-04-session-continuity`).

## Must do (brief requirements or factual corrections)

### 1. Section 3: add the alternatives the brief requires (§5.1 "at least two alternatives")

Insert a new paragraph **after** the sentence ending "measurements: evidence/test-performance.md and evidence/load-summary.md." (end of "Decision"):

> **Alternatives considered.** AWS Lambda with API Gateway was rejected because Django is a long-running process with a connection pool: many concurrent functions would each open a PostgreSQL connection exactly when stock rows are locked at a restock, and scaling to zero has no value for an always-open shop. Amazon EKS adds a control plane for a single deployable, well beyond what a one-to-three-engineer team needs. Elastic Beanstalk and App Runner hide the network and scaling decisions this project must show, and the Learner Lab restricts some of their roles. ECS on EC2 was dropped for time. EC2 with an Auto Scaling group (variant A) was built and measured as the closest alternative (ADR-018).

### 2. Delete the ninth heading

Delete the heading **"9. AI declaration"** and its paragraph ("AI-assisted work is summarised in Section 8. The complete per-tool use ... which is the submission authority."). The brief fixes eight headings; Section 8 already points to `AI_USE_DECLARATION.md`.

### 3. Section 8: say the report was AI-drafted

After "AI coding assistants were used extensively: Claude Code, OpenAI Codex agents, GitHub Copilot and Gemini." add:

> This report was drafted with Claude Code and Codex agents and edited by the team; the two developers checked its numbers and paths against the evidence records, all members read it, and the primary developer approved it.

### 4. Security test attribution (Section 4 table and Section 6)

| Find | Replace with |
|---|---|
| `SEC-01 to SEC-06, local suite of 25 tests PASS (rerun 1 Oct)` | `SEC-01 to SEC-06 PASS, part of the 25-test local security suite SEC-01 to SEC-08 (rerun 1 Oct)` |
| `SEC-01–06's 25 security tests passed` | `the 25 security tests of SEC-01 to SEC-08 passed` |

### 5. RES-04 is now analysed (session and cart continuity held)

| Where | Find | Replace with |
|---|---|---|
| SC3 row, Result cell | `Partial (n = 1): A/B scale-out was automatic; after graceful removal, two healthy units returned in 114 s/50 s with 0 errors. Session and cart continuity was not analysed` | `Met for a graceful removal (n = 1): A/B scale-out was automatic; two healthy units returned in 114 s/50 s with 0 errors; logged-in visits that spanned the removal kept their session and cart (A: 11 visits, B: 3; small sample)` |
| Section 2, Request path | `however, cross-task session/cart continuity was not analysed (RES-04).` | `the RES-04 request-log analysis found that logged-in visits spanning a graceful removal continued without a new login (A: 11 visits, B: 3; small sample).` |
| Section 6 scaling table, RES-04 row | `Not analysed on either variant; 0 request errors are indirect evidence only` / `Not analysed` / `Not analysed` | Measure: `Logged-in visits spanning the removal · later requests ok · second logins`; A: `11 · 29 of 29 · 0`; B: `3 · 8 of 8 · 0` |
| Section 6 text | `Scale-in was observed only on B after the run; session/cart continuity was not analysed.` | `Scale-in was observed only on B after the run. Session and cart continuity held for the logged-in visits that spanned the removal (A: 11, B: 3), a small sample from a graceful removal (RES-04).` |
| Section 6, "Not tested, stated plainly" | `local RES-01/02 database-outage cases and session/cart continuity analysis were not completed.` | `and local RES-01/02 database-outage cases were not completed.` (also delete the comma or "and" left before it so the list still reads correctly) |
| Appendix A, new row after "Load, scaling, replacement (6)" | — | Claim: `Session continuity (6)`; Evidence path: `evidence/raw/RES-04_2026-10-10_ec2_continuity.txt; evidence/raw/RES-04_2026-10-10_fargate_continuity.txt; tests/load/continuity.py` |

### 6. Success-criteria table: paths break in the PDF text layer

An AI marker reads the extracted text, where 12 paths in the Evidence column come out split (for example `evidence/test-se curity.md`). Either widen the Evidence column so each path fits on one line, or replace each cell with the case IDs only (for example `SEC-01, SEC-05; LOAD runs`) and rely on Appendix A, whose paths extract cleanly.

### 7. Section 8, Hermann's row and reflection (after he approves)

| Find | Replace with |
|---|---|
| Hermann's "Main artefacts" cell starting `Local functional and security test records` | `Review of the local functional and security test records (run by AI agents), FUNC-02 browser walkthrough of the storefront and dashboard, the reproduction test of the submission package, and the stay-on-page Add to cart request.` |
| His reflection starting `I wrote the local functional and security test records` | The text he approves (draft below). |

Draft, for Hermann to reword:

> I reviewed the local functional and security test records, ran the FUNC-02 browser walkthrough of the storefront and dashboard, and asked for the stay-on-page Add to cart behaviour. I learned to write the expected result before running a test and to keep the raw output, so that someone who did not run it can check it, and that even the Gemini-assisted dashboard description had to be cross-checked against the database before we recorded it as matching. I also ran the reproduction test, unzipping the package on a clean machine and following the README. [One sentence on what it showed.] If we repeated the project I would rerun the local test records against each new build earlier and automate more of the walkthrough.

## After the edits

- The body must stay within 8 to 12 pages (references and appendix excluded).
- Export as `report.pdf` and run `python scripts/package_submission.py --group G021 --ref WORKTREE --out <scratch path>`; it must show 0 FAIL.
- When Hermann's reflection is final, the same text goes into `TEAM_CONTRIBUTIONS.md` (his row).
