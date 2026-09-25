"""Load validated offline assignments as one complete, atomic run snapshot."""
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction

from orders.models import Order
from reporting.models import AnalyticsRun, CustomerSegment


def integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError
    return value


def decimal_value(value, minimum, maximum, places):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError
    result = Decimal(str(value))
    if not result.is_finite() or not minimum <= result <= maximum:
        raise ValueError
    if result != result.quantize(Decimal(1).scaleb(-places)):
        raise ValueError
    return result


def text_value(value, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError
    if "\x00" in value:
        raise ValueError
    value.encode("utf-8")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


class Command(BaseCommand):
    help = "Load a complete customer-segment snapshot for a completed analytics run."

    def add_arguments(self, parser):
        parser.add_argument("--run-id", required=True, help="Completed analytics run UUID")
        parser.add_argument("--input", required=True, type=Path)
        parser.add_argument("--model-version", help="Assert the JSON model_version")

    def handle(self, *args, **options):
        payload = self._payload(options["input"])
        try:
            run_id = UUID(str(options["run_id"]))
            file_run = UUID(payload["run_id"])
        except (KeyError, ValueError, TypeError, AttributeError):
            raise CommandError("Explicit valid run_id values are required") from None
        if file_run != run_id:
            raise CommandError("JSON run_id does not match --run-id")
        try:
            model_version = text_value(payload["model_version"], 100)
            if options["model_version"] is not None and options["model_version"] != model_version:
                raise ValueError
            k = integer(payload["k_clusters"], 2, 32767)
            score = payload["silhouette_score"]
            score = None if score is None else decimal_value(score, -1, 1, 4)
        except (KeyError, ValueError, TypeError, InvalidOperation, UnicodeError):
            raise CommandError("Invalid or missing model metadata") from None
        rows = payload.get("rows")
        if not isinstance(rows, list) or not rows:
            raise CommandError("rows must be a non-empty JSON array")
        assignments = [self._assignment(run_id, model_version, item, index, k, score)
                       for index, item in enumerate(rows, start=1)]
        customer_ids = {row.customer_id for row in assignments}
        if len(customer_ids) != len(assignments):
            raise CommandError("Duplicate customer assignments")
        labels = {}
        for row in assignments:
            if row.cluster_id in labels and labels[row.cluster_id] != row.segment_label:
                raise CommandError("Each cluster must have one consistent segment label")
            labels[row.cluster_id] = row.segment_label
        try:
            with transaction.atomic():
                # Serializes replacements, including the first load, and prevents run pruning.
                run = AnalyticsRun.objects.select_for_update().get(pk=run_id)
                if run.status != AnalyticsRun.Status.COMPLETED:
                    raise CommandError("Analytics run is not completed")
                eligible = set(Order.objects.filter(
                    namespace=run.inventory.namespace, status=Order.Status.COMPLETED,
                    placed_at__lt=run.cutoff, owner__is_staff=False, owner__is_superuser=False,
                ).exclude(owner__groups__name="store_operator").values_list("owner_id", flat=True).distinct())
                if customer_ids != eligible:
                    raise CommandError("Rows must cover exactly the eligible customers; regenerate the export")
                CustomerSegment.objects.filter(run=run, model_version=model_version).delete()
                CustomerSegment.objects.bulk_create(assignments)
        except AnalyticsRun.DoesNotExist:
            raise CommandError("Analytics run does not exist") from None
        except DatabaseError:
            raise CommandError("Unable to load customer segments; check database availability and retry the complete export") from None
        self.stdout.write(f"Loaded {len(assignments)} customer segment rows for run {run_id}.")

    def _payload(self, path):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                                 parse_float=Decimal)
            if not isinstance(payload, dict):
                raise ValueError
            return payload
        except (OSError, UnicodeError, ValueError, InvalidOperation, RecursionError):
            raise CommandError("Unable to read a valid JSON object from input") from None

    def _assignment(self, run_id, model_version, item, index, k, score):
        try:
            if not isinstance(item, dict):
                raise ValueError
            row = CustomerSegment(
                run_id=run_id, model_version=model_version,
                customer_id=integer(item["customer_id"], 1, 2147483647),
                cluster_id=integer(item["cluster_id"], 0, k - 1),
                segment_label=text_value(item["segment_label"], 40),
                recency_days=integer(item["recency_days"], 0, 2147483647),
                frequency_orders=integer(item["frequency_orders"], 1, 2147483647),
                monetary_total=decimal_value(item["monetary_total"], 0, Decimal("9999999999999999.99"), 2),
                k_clusters=integer(item["k_clusters"], 2, 32767),
                silhouette_score=(None if item["silhouette_score"] is None
                                  else decimal_value(item["silhouette_score"], -1, 1, 4)),
            )
            if row.k_clusters != k or row.silhouette_score != score:
                raise ValueError
        except (KeyError, ValueError, TypeError, InvalidOperation, UnicodeError):
            raise CommandError(f"rows[{index}] has invalid or inconsistent fields") from None
        return row
