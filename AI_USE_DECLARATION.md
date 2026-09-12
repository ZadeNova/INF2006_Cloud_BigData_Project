# AI Use Declaration

For each AI tool or external baseline used, record:

| Tool/source | Where used | Purpose | Verification performed | Licence/attribution |
|---|---|---|---|---|
| TODO | TODO | TODO | TODO | TODO |

## Notes
TODO: describe any open-source baseline or AI-assisted code the team started from, and the team's substantive modifications and decisions on top of it.

## Foundation verification and attribution

| Tool/source | Where used | Purpose | Verification performed | Licence/attribution |
|---|---|---|---|---|
| OpenAI Codex; independent Astra Medium reviewer agents | Local backend foundation batches 1-4, src/, tests/, related docs | Scaffolding, configuration, schema/migrations, health, test and documentation assistance | Dated foundation evidence and independent review logs under evidence/ and docs/reviews/; follow-up workflows explicitly unverified | AI-assisted work; review records distinguish coordinator-run tests from reviewer inspection |
| Django and Python official documentation | Runtime/framework selection and framework patterns | Supported Django 5.2 LTS / Python 3.13 baseline | Exact installed versions and dependency compatibility recorded in foundation evidence | https://docs.djangoproject.com/en/5.2/releases/5.2/ ; https://www.python.org/downloads/ |
| PostgreSQL official documentation and Docker Official Images | Local PostgreSQL and Python containers | Reproducible local runtime | Image digests pinned; PostgreSQL constraints and migrations exercised | https://www.postgresql.org/docs/17/ ; upstream software/image licences apply |

No external application template or another course's implementation was copied. Source dataset provenance and any frontend imagery/font attribution remain separate future records. This entry does not claim human team members performed the agent-run checks.
