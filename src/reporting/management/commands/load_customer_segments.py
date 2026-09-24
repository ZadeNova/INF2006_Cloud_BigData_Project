"""Load offline ML customer-segmentation assignments for one completed analytics run."""
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from reporting.models import AnalyticsRun, CustomerSegment


class Command(BaseCommand):
    help = ("Load customer-segment assignments produced by analytics/segment_customers.py. "
            "Rows are keyed by run and model version.")

    def add_arguments(self, parser):
        parser.add_argument("--run-id", required=True, help="Completed analytics run UUID")
        parser.add_argument("--input", required=True, type=Path, help="JSON file with assignment rows")
        parser.add_argument("--model-version", help="Override the JSON model_version")

    def handle(self, *args, **options):
        run = self._completed_run(options["run_id"])
        payload = self._payload(options["input"])
        file_run = str(payload.get("run_id", ""))
        if file_run and file_run != str(run.pk):
            raise CommandError(f"JSON run_id {file_run!r} does not match --run-id {run.pk}")

        model_version = options["model_version"] or payload.get("model_version")
        if not isinstance(model_version, str) or not model_version.strip():
            raise CommandError("model_version is required (either in JSON or --model-version)")
        model_version = model_version.strip()
        rows = payload.get("rows")
        if not isinstance(rows, list) or not rows:
            raise CommandError("rows must be a non-empty JSON array")

        assignments = [self._assignment(run, model_version, item, index) for index, item in enumerate(rows, start=1)]
        try:
            with transaction.atomic():
                CustomerSegment.objects.filter(run=run, model_version=model_version).delete()
                CustomerSegment.objects.bulk_create(assignments)
        except IntegrityError:
            raise CommandError("rows contain invalid references or duplicate customer assignments") from None

        self.stdout.write(
            f"Loaded {len(assignments)} customer segment rows for run {run.pk} (model_version={model_version}).")

    def _completed_run(self, run_id):
        try:
            run = AnalyticsRun.objects.get(pk=run_id)
        except AnalyticsRun.DoesNotExist:
            raise CommandError(f"Analytics run {run_id!r} does not exist") from None
        if run.status != AnalyticsRun.Status.COMPLETED:
            raise CommandError(f"Analytics run {run_id!r} is not completed")
        return run

    def _payload(self, path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except OSError:
            raise CommandError(f"Unable to read {path}") from None
        except json.JSONDecodeError:
            raise CommandError(f"{path} is not valid JSON") from None

    def _assignment(self, run, model_version, item, index):
        if not isinstance(item, dict):
            raise CommandError(f"rows[{index}] must be an object")
        try:
            customer_id = int(item["customer_id"])
            cluster_id = int(item["cluster_id"])
            segment_label = str(item["segment_label"]).strip()
            recency_days = int(item["recency_days"])
            frequency_orders = int(item["frequency_orders"])
            monetary_total = Decimal(str(item["monetary_total"]))
            k_clusters = int(item["k_clusters"])
            silhouette = item.get("silhouette_score")
            silhouette_score = None if silhouette is None else Decimal(str(silhouette))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            raise CommandError(f"rows[{index}] has invalid or missing fields") from None
        if not segment_label:
            raise CommandError(f"rows[{index}].segment_label must not be empty")
        return CustomerSegment(
            run=run,
            customer_id=customer_id,
            model_version=model_version,
            cluster_id=cluster_id,
            segment_label=segment_label,
            recency_days=recency_days,
            frequency_orders=frequency_orders,
            monetary_total=monetary_total,
            k_clusters=k_clusters,
            silhouette_score=silhouette_score,
        )
