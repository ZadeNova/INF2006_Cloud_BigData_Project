# evidence/

Named, dated evidence artefacts cited by `project_manifest.yaml` and `report.pdf`.

Rules (Section 9 of the brief):
- Prefer text/config exports over screenshots; use screenshots only when no text export is possible.
- Redact account IDs, public IPs, tokens and other sensitive values.
- No credentials, production data, or personal data.

## Required files (referenced by the manifest — do not rename)
- `architecture.png` — TODO: add the architecture diagram (users, components, cloud services, trust boundaries, data stores, observability, data flows).
- `test-functional.md` — functional workflow test
- `test-security.md` — security control test
- `test-data-ai.md` — data/AI validation test
- `test-resilience.md` — scalability/resilience/recovery test
- `monitoring.md` — monitoring/operational evidence
- `threat-control-map.md` — threats mapped to controls

Each test file should record: objective, setup, command/steps, expected result, actual result, date, artefact path.
