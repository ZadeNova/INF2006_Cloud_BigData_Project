"""Seal current stock and lead times as an immutable inventory version for analytics; create-only."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from reporting import services

from ._args import iso_date


class Command(BaseCommand):
    help = ("Seal the CURRENT stock and lead time of every product as an inventory version whose cutoff is 00:00 "
            "Asia/Singapore on --as-of, so refresh_analytics --as-of the same date can use it. --as-of must be "
            "today's Singapore date: live values are captured now. Re-running verifies an identical version and "
            "reports it unchanged.")

    def add_arguments(self, parser):
        parser.add_argument("--as-of", type=iso_date, required=True, help="Cutoff date, YYYY-MM-DD")
        parser.add_argument("--namespace", default=settings.DEMO_NAMESPACE)
        parser.add_argument("--name", help="Inventory version name (default: live-<as-of>); --version is reserved by Django")

    def handle(self, *args, **options):
        try:
            result = services.snapshot_inventory(
                namespace=options["namespace"], as_of=options["as_of"], version=options["name"])
        except services.SnapshotError as exc:
            raise CommandError(str(exc)) from exc

        state = "Sealed" if result.created else "Verified unchanged"
        self.stdout.write(f"{state}: inventory version {result.version.version!r} with {result.rows} product row(s), "
                          f"cutoff {result.version.cutoff.isoformat()}.")
