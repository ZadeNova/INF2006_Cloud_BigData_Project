"""Export production coverage as a comparison target, separate from the pandas verifier."""
import argparse
import json
import os
from pathlib import Path
import sys
from uuid import UUID


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.db import transaction
    from reporting.models import AnalyticsRun
    from reporting.queries import coverage
    with transaction.atomic():
        run = AnalyticsRun.objects.select_related("inventory").get(pk=args.run_id, status="completed")
        fields = ("product_id", "stock", "lead_time_days", "units_7d", "avg_daily_units", "coverage_days", "status")
        target = dict(run_id=str(run.pk), summary_version=str(run.summary_version), inventory_id=run.inventory_id,
                      namespace=run.inventory.namespace, inventory_version=run.inventory.version,
                      rows=[{field: getattr(row, field) for field in fields} for row in coverage(run)])
    args.output.write_text(json.dumps(target, default=str, indent=2) + "\n", encoding="utf-8")
    print(f"Exported coverage for run {run.pk}: {len(target['rows'])} products")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Framework/database errors may embed credentials; do not echo their messages.
        print("FAIL: unable to export completed run coverage", file=sys.stderr)
        sys.exit(1)
