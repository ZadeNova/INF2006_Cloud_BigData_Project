"""Load validated offline assignments as one complete, atomic run snapshot."""
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection, transaction

from orders.models import Order
from reporting.models import AnalyticsRun, CustomerSegment
from reporting.segment_contract import unique_object, validate_rows, validate_batch, source_binding


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
        except (ValueError, TypeError, AttributeError):
            raise CommandError("Explicit valid run_id values are required") from None
        try:
            rows = validate_rows(payload, run_id, options["model_version"])
        except ValueError as error:
            raise CommandError(str(error)) from None
        model_version = payload["model_version"]
        assignments = [CustomerSegment(run_id=run_id, model_version=model_version, **row) for row in rows]
        customer_ids = {row.customer_id for row in assignments}
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
                try:
                    validate_batch(payload, {
                        "run_id": run.pk, "namespace": run.inventory.namespace, "cutoff": run.cutoff,
                        "inventory_version": run.inventory.version, "summary_version": run.summary_version,
                    }, source_binding(connection))
                except ValueError:
                    raise CommandError("Invalid completed batch, provenance or destination; regenerate the export") from None
                CustomerSegment.objects.filter(run=run, model_version=model_version).delete()
                CustomerSegment.objects.bulk_create(assignments)
        except AnalyticsRun.DoesNotExist:
            raise CommandError("Analytics run does not exist") from None
        except DatabaseError:
            raise CommandError("Unable to load customer segments; check database availability and retry the complete export") from None
        self.stdout.write(f"Loaded {len(assignments)} customer segment rows for run {run_id}; "
                          f"model_version={model_version}; batch_id={payload['batch_id']}.")

    def _payload(self, path):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                                 parse_float=Decimal)
            if not isinstance(payload, dict):
                raise ValueError
            return payload
        except (OSError, UnicodeError, ValueError, InvalidOperation, RecursionError):
            raise CommandError("Unable to read a valid JSON object from input") from None
