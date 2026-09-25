# Batch 06d: Optional ML customer segmentation

## Scope

Optional additive RFM K-means segmentation for analytics runs:

- offline training/export script: `analytics/segment_customers.py`
- loader command: `python manage.py load_customer_segments`
- dashboard panel integration (summary + customer rows)

## Guardrails

- Keep ML out of the web image (`analytics/requirements.txt` only for offline execution).
- Do not change deterministic analytics metrics or inventory flags.
- Treat output as descriptive on synthetic data, not predictive.
- Keep feature removable.

## Verification targets

- `python manage.py makemigrations --check --dry-run`
- `pytest -q -p no:cacheprovider /app/tests/test_customer_segments_command.py /app/tests/test_analytics_queries.py /app/tests/test_analytics_dashboard.py`
- `pytest -q -p no:cacheprovider /work/analytics/tests/test_segment_customers.py`

## Status

Implemented locally. Remaining gate: independent backend review cycle per DEVELOPMENT.md before final publication.
