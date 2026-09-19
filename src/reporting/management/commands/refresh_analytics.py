"""Recompute and publish an analytics run; safe to re-run (each run is a full recompute)."""
import argparse
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from reporting import ranges, services


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a YYYY-MM-DD date") from None


class Command(BaseCommand):
    help = ("Create an analytics run whose cutoff is 00:00 Asia/Singapore on --as-of (so the last complete business "
            "date is the day before). Skips, exiting 0, if another refresh holds the lock.")

    def add_arguments(self, parser):
        parser.add_argument("--as-of", type=iso_date, required=True, help="Cutoff date, YYYY-MM-DD")
        parser.add_argument("--namespace", default=settings.DEMO_NAMESPACE)
        parser.add_argument("--inventory-version", help="Sealed inventory version name; optional if only one matches")
        parser.add_argument("--keep", type=int, default=5, help="Completed runs to retain per namespace (minimum 2)")
        parser.add_argument("--timeout", type=int, default=300, help="Statement timeout in seconds")

    def handle(self, *args, **options):
        try:
            result = services.refresh_analytics(
                namespace=options["namespace"], as_of=options["as_of"], inventory_version=options["inventory_version"],
                keep=options["keep"], timeout=options["timeout"])
        except services.RefreshError as exc:
            raise CommandError(str(exc)) from exc

        if result.skipped:
            self.stdout.write("Skipped: another analytics refresh is running.")
            return
        run = result.run
        latest = ranges.latest_complete_date(run.cutoff)
        self.stdout.write(
            f"Run {run.pk} completed: {result.rows_written} daily rows from {result.lines_processed} order lines, "
            f"business dates {ranges.run_window_start(latest)} to {latest}, cutoff {run.cutoff.isoformat()}, "
            f"pruned {result.pruned} old run(s), {result.seconds:.1f}s.")
