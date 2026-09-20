"""Analytics refresh: recompute a run's daily sales from completed order lines and publish it.

Contract: docs/ANALYTICS.md ("Processing and validation"). Plan: docs/plans/batch-06b-analytics-refresh.md.
A run is a full recompute of a 366-business-date window ending at L (the last complete date before
the cutoff). It is published atomically: readers only ever see runs with status "completed".
"""
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, time as clock

from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from catalogue.models import Product

from . import ranges
from .models import AnalyticsRun, InventorySnapshot, InventoryVersion

# Fixed key identifying the refresh job to PostgreSQL advisory locks (any constant bigint).
REFRESH_LOCK_KEY = 2006_0601
# Retention always keeps at least two runs, so the run a reader has just selected survives a publish.
MIN_KEEP = 2

# One statement, so the counts and the inserted rows come from the same snapshot even while orders
# are being placed. The placed_at range is the indexable bound; business_date keeps only complete dates.
PUBLISH_SQL = """
WITH lines AS (
    SELECT business_date, product_id, quantity, line_total
    FROM reporting_completed_sale_lines
    WHERE namespace = %(namespace)s
      AND placed_at >= %(window_start)s AND placed_at < %(cutoff)s
      AND business_date BETWEEN %(first_date)s AND %(last_date)s
),
inserted AS (
    INSERT INTO reporting_dailyproductsales (run_id, business_date, product_id, units, sales_amount)
    SELECT %(run_id)s, business_date, product_id, SUM(quantity), SUM(line_total)
    FROM lines
    GROUP BY business_date, product_id
    RETURNING 1
)
SELECT (SELECT COUNT(*) FROM lines), (SELECT COUNT(*) FROM inserted)
"""


class RefreshError(Exception):
    """A refresh cannot start or complete for a reason the operator can act on."""


class SnapshotError(Exception):
    """An inventory snapshot cannot be created or verified for a reason the operator can act on."""


@dataclass
class RefreshResult:
    skipped: bool = False
    run: AnalyticsRun | None = None
    lines_processed: int = 0
    rows_written: int = 0
    pruned: int = 0
    seconds: float = 0.0


def refresh_analytics(*, namespace, as_of, inventory_version=None, keep=5, timeout=300):
    """Create and publish one run for `namespace` at the cutoff 00:00 Asia/Singapore on `as_of`."""
    if keep < MIN_KEEP:
        raise RefreshError(f"keep must be at least {MIN_KEEP}")
    if timeout < 1:
        raise RefreshError("timeout must be at least one second")
    cutoff = _cutoff_for(as_of)
    if cutoff > timezone.now():
        raise RefreshError("as-of date is in the future; that cutoff has not happened yet")

    latest = ranges.latest_complete_date(cutoff)
    first_date = ranges.run_window_start(latest)
    window_start = datetime.combine(first_date, clock.min, tzinfo=ranges.BUSINESS_TZ)

    started = time.monotonic()
    with _advisory_lock() as acquired:
        if not acquired:
            return RefreshResult(skipped=True)
        _fail_orphaned_runs()
        version = _select_inventory(namespace, cutoff, inventory_version)
        _require_every_product(namespace, version)

        run = AnalyticsRun.objects.create(
            inventory=version, window_start=window_start, cutoff=cutoff, status=AnalyticsRun.Status.RUNNING)
        try:
            with transaction.atomic():
                lines, rows = _insert_rows(run, namespace, window_start, cutoff, first_date, latest, timeout)
                _complete(run, lines)
        except Exception:
            _mark_failed(run)
            raise
        pruned = _prune(run, namespace, keep)

    run.refresh_from_db()
    return RefreshResult(run=run, lines_processed=lines, rows_written=rows, pruned=pruned,
                         seconds=time.monotonic() - started)


def _today():
    """Today's business date (Singapore calendar date)."""
    return timezone.now().astimezone(ranges.BUSINESS_TZ).date()


def _cutoff_for(as_of):
    """The cutoff for an as-of date: 00:00 Asia/Singapore, so the last complete business date is the day before."""
    return datetime.combine(as_of, clock.min, tzinfo=ranges.BUSINESS_TZ)


@contextmanager
def _advisory_lock():
    """Session-level advisory lock; yields whether it was acquired. Released even on error."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [REFRESH_LOCK_KEY])
        acquired = cursor.fetchone()[0]
    try:
        yield acquired
    finally:
        if acquired:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [REFRESH_LOCK_KEY])


def _fail_orphaned_runs():
    # We hold the lock, so no refresh is genuinely in progress: any "running" run was left behind by a
    # host that died. Its rows were written in the publish transaction and rolled back with it.
    AnalyticsRun.objects.filter(status=AnalyticsRun.Status.RUNNING).update(
        status=AnalyticsRun.Status.FAILED, finished_at=timezone.now())


def _select_inventory(namespace, cutoff, name):
    """The sealed inventory version for this cutoff. DOC-001: explicit, never a fallback to live stock."""
    if name:
        try:
            version = InventoryVersion.objects.get(namespace=namespace, version=name)
        except InventoryVersion.DoesNotExist:
            raise RefreshError(f"Inventory version {name!r} does not exist in namespace {namespace!r}") from None
        if not version.sealed:
            raise RefreshError(f"Inventory version {name!r} is not sealed")
        if version.cutoff != cutoff:
            raise RefreshError(f"Inventory version {name!r} is for cutoff {version.cutoff.isoformat()}, "
                               f"not the run cutoff {cutoff.isoformat()}")
        return version

    candidates = list(InventoryVersion.objects.filter(namespace=namespace, cutoff=cutoff, sealed=True).order_by("version"))
    if not candidates:
        raise RefreshError(f"No sealed inventory version for namespace {namespace!r} at cutoff {cutoff.isoformat()}; "
                           "seal one first (snapshot_inventory)")
    if len(candidates) > 1:
        names = ", ".join(item.version for item in candidates)
        raise RefreshError(f"Several sealed inventory versions match this cutoff ({names}); choose one with --inventory-version")
    return candidates[0]


def _require_every_product(namespace, version):
    missing = Product.objects.filter(namespace=namespace).exclude(pk__in=version.items.values("product_id"))
    count = missing.count()
    if count:
        sample = ", ".join(missing.order_by("external_id").values_list("external_id", flat=True)[:5])
        raise RefreshError(f"Inventory version {version.version!r} has no row for {count} product(s) in "
                           f"{namespace!r} (for example {sample})")


def _insert_rows(run, namespace, window_start, cutoff, first_date, last_date, timeout):
    with connection.cursor() as cursor:
        # Transaction-local: reverts at commit or rollback, so it cannot leak to other work on the connection.
        cursor.execute("SELECT set_config('statement_timeout', %s, true)", [str(timeout * 1000)])
        cursor.execute(PUBLISH_SQL, {
            "namespace": namespace, "window_start": window_start, "cutoff": cutoff,
            "first_date": first_date, "last_date": last_date, "run_id": run.pk})
        return cursor.fetchone()


def _complete(run, lines):
    updated = AnalyticsRun.objects.filter(pk=run.pk, status=AnalyticsRun.Status.RUNNING).update(
        status=AnalyticsRun.Status.COMPLETED, finished_at=timezone.now(), processed_count=lines)
    if updated != 1:
        raise RefreshError("The run was no longer in progress")


def _mark_failed(run):
    AnalyticsRun.objects.filter(pk=run.pk, status=AnalyticsRun.Status.RUNNING).update(
        status=AnalyticsRun.Status.FAILED, finished_at=timezone.now())


def _prune(run, namespace, keep):
    """Keep the newest `keep` completed runs for the namespace (always including `run`); delete the rest."""
    others = list(AnalyticsRun.objects
                  .filter(status=AnalyticsRun.Status.COMPLETED, inventory__namespace=namespace)
                  .exclude(pk=run.pk)
                  .order_by("-finished_at", "-started_at")
                  .values_list("pk", flat=True))
    stale = others[keep - 1:]
    if stale:
        AnalyticsRun.objects.filter(pk__in=stale).delete()   # cascades to their daily rows
    return len(stale)


@dataclass
class SnapshotResult:
    version: InventoryVersion
    rows: int
    created: bool


def snapshot_inventory(*, namespace, as_of, version=None):
    """Seal the CURRENT stock and lead times of every product in `namespace` as an immutable inventory version.

    The cutoff is 00:00 Asia/Singapore on `as_of`, matching refresh_analytics, and `as_of` must be today's
    Singapore date (KO-1): live values are captured when this runs, so it can only describe today's cutoff.
    That is a disclosed approximation: sales between midnight and now are already deducted from stock, and
    because nothing in the application raises stock, the captured stock is at most the true midnight stock,
    so coverage errs low (flags slightly early), never late. A historical import seals its generated stock at
    import time instead. Create-only: an existing version of the same name must be sealed and is verified
    against the current values and reported unchanged, or rejected if anything differs.
    """
    today = _today()
    if as_of != today:
        raise SnapshotError(f"as-of must be today's date in Singapore ({today.isoformat()}): a snapshot captures "
                            "live stock when it runs, so it cannot describe another cutoff")
    cutoff = _cutoff_for(as_of)
    name = version or f"live-{as_of.isoformat()}"

    with transaction.atomic():
        products = list(Product.objects.filter(namespace=namespace).order_by("pk")
                        .values_list("pk", "stock", "lead_time_days"))
        if not products:
            raise SnapshotError(f"Namespace {namespace!r} has no products to snapshot")

        existing = InventoryVersion.objects.filter(namespace=namespace, version=name).first()
        if existing is not None:
            return _verify_existing(existing, cutoff, products)

        try:
            with transaction.atomic():
                inventory = InventoryVersion.objects.create(namespace=namespace, version=name, cutoff=cutoff)
        except IntegrityError:
            raise SnapshotError(f"Inventory version {name!r} was created concurrently; re-run to verify it") from None
        InventorySnapshot.objects.bulk_create(
            InventorySnapshot(inventory=inventory, product_id=product_id, stock=stock, lead_time_days=lead)
            for product_id, stock, lead in products)
        InventoryVersion.objects.filter(pk=inventory.pk).update(sealed=True)   # the guard requires rows before sealing
    inventory.refresh_from_db()
    return SnapshotResult(version=inventory, rows=len(products), created=True)


def _verify_existing(existing, cutoff, products):
    if not existing.sealed:
        raise SnapshotError(f"Inventory version {existing.version!r} already exists but is not sealed, so "
                            "refresh_analytics cannot use it; use a new version name")
    if existing.cutoff != cutoff:
        raise SnapshotError(f"Inventory version {existing.version!r} already exists for cutoff "
                            f"{existing.cutoff.isoformat()}, not {cutoff.isoformat()}")
    stored = set(existing.items.values_list("product_id", "stock", "lead_time_days"))
    if stored != set(products):
        raise SnapshotError(f"Inventory version {existing.version!r} already exists with different values "
                            "(stock or lead times have changed since); use a new version name")
    return SnapshotResult(version=existing, rows=len(products), created=False)
