"""refresh_analytics (PostgreSQL). Explicit dates and hand-computed expectations.

Cutoff is 00:00 Asia/Singapore on 8 March 2024, so L (the last complete business date) is 7 March 2024
and the run window is the 366 dates 8 March 2023 .. 7 March 2024 (2024 is a leap year: 7 March 2024 minus
365 days is 8 March 2023).
"""
import threading
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection
from django.test.utils import CaptureQueriesContext

from analytics_helpers import (
    DEFAULT_CUTOFF, NS, OTHER_NS, SGT, add_order, at, make_inventory, make_products)
from catalogue.models import Product
from reporting import services
from reporting.models import AnalyticsRun, DailyProductSales

pytestmark = pytest.mark.django_db
AS_OF = date(2024, 3, 8)
CUTOFF = DEFAULT_CUTOFF


@pytest.fixture
def owner():
    return get_user_model().objects.create_user(username="refresh-user")


def standard_orders(owner, p):
    add_order(owner, "o1", [(p["alpha"], 2, "10.00"), (p["beta"], 1, "5.00")], at(2024, 3, 5, 12))
    add_order(owner, "o2", [(p["alpha"], 1, "10.00")], at(2024, 3, 5, 20))
    add_order(owner, "o3", [(p["alpha"], 3, "12.00")], at(2024, 3, 6, 9))                        # price changed to 12.00
    add_order(owner, "o4", [(p["alpha"], 9, "10.00")], at(2024, 3, 6, 10), status="cancelled")   # excluded
    add_order(owner, "o5", [(p["beta"], 9, "5.00")], at(2024, 3, 6, 11), status="refunded")      # excluded
    add_order(owner, "o6", [(p["beta"], 4, "5.00")], at(2024, 3, 7, 23, 59))                     # last minute of L
    add_order(owner, "o7", [(p["alpha"], 100, "10.00")], at(2024, 3, 8, 0, 0))                   # exactly the cutoff: not complete
    add_order(owner, "o8", [(p["alpha"], 100, "10.00")], at(2024, 3, 8, 10, 0))                  # after the cutoff


EXPECTED = [
    (date(2024, 3, 5), "alpha", 3, Decimal("30.00")),      # 2 + 1 units at 10.00
    (date(2024, 3, 5), "beta", 1, Decimal("5.00")),
    (date(2024, 3, 6), "alpha", 3, Decimal("36.00")),      # 3 units at the new 12.00 price
    (date(2024, 3, 7), "beta", 4, Decimal("20.00")),
]


def refresh(**overrides):
    return services.refresh_analytics(**{"namespace": NS, "as_of": AS_OF, **overrides})


def rows_of(run):
    return list(DailyProductSales.objects.filter(run=run).order_by("business_date", "product__external_id")
                .values_list("business_date", "product__external_id", "units", "sales_amount"))


@pytest.fixture
def ready(owner):
    products = make_products()
    inventory = make_inventory(products)
    standard_orders(owner, products)
    return products, inventory


# --- correctness ----------------------------------------------------------------------------

def test_daily_rows_match_the_hand_computed_totals(ready):
    result = refresh()
    assert not result.skipped
    assert rows_of(result.run) == EXPECTED
    # completed lines in the window: o1 has two, o2, o3 and o6 one each
    assert (result.lines_processed, result.rows_written) == (5, 4)


def test_run_row_records_window_cutoff_and_inventory(ready):
    _, inventory = ready
    run = refresh().run
    assert run.status == AnalyticsRun.Status.COMPLETED
    assert run.finished_at is not None and run.processed_count == 5
    assert run.inventory == inventory
    assert run.cutoff == CUTOFF
    assert run.window_start == datetime(2023, 3, 8, tzinfo=SGT)


def test_singapore_date_boundary_is_used_for_the_business_date(owner):
    products = make_products()
    make_inventory(products)
    # 15:59 UTC is 23:59 on 6 March in Singapore; 16:00 UTC is 00:00 on 7 March
    add_order(owner, "a", [(products["alpha"], 1, "10.00")], datetime(2024, 3, 6, 15, 59, tzinfo=timezone.utc))
    add_order(owner, "b", [(products["alpha"], 1, "10.00")], datetime(2024, 3, 6, 16, 0, tzinfo=timezone.utc))
    assert [(row[0], row[2]) for row in rows_of(refresh().run)] == [(date(2024, 3, 6), 1), (date(2024, 3, 7), 1)]


def test_window_start_date_is_included_and_the_day_before_is_not(owner):
    products = make_products()
    make_inventory(products)
    add_order(owner, "in", [(products["alpha"], 1, "10.00")], at(2023, 3, 8, 0, 0))
    add_order(owner, "out", [(products["alpha"], 1, "10.00")], at(2023, 3, 7, 23, 59))
    assert [row[0] for row in rows_of(refresh().run)] == [date(2023, 3, 8)]


def test_other_namespaces_are_not_counted(owner, ready):
    other = make_products(OTHER_NS, names=("alpha",))
    add_order(owner, "x1", [(other["alpha"], 50, "10.00")], at(2024, 3, 5), namespace=OTHER_NS)
    assert rows_of(refresh().run) == EXPECTED


def test_a_product_with_no_sales_has_no_row(ready):
    products, _ = ready
    result = refresh()
    assert not DailyProductSales.objects.filter(run=result.run, product=products["gamma"]).exists()


def test_no_orders_gives_an_empty_completed_run(owner):
    make_inventory(make_products())
    result = refresh()
    assert result.run.status == AnalyticsRun.Status.COMPLETED
    assert (result.lines_processed, result.rows_written) == (0, 0)


def test_rerun_produces_identical_rows_in_a_new_run(ready):
    first, second = refresh().run, refresh().run
    assert first.pk != second.pk
    assert rows_of(first) == rows_of(second) == EXPECTED


def test_live_stock_changes_do_not_affect_the_run(ready):
    products, inventory = ready
    Product.objects.filter(pk=products["alpha"].pk).update(stock=0, lead_time_days=99)
    run = refresh().run
    assert run.inventory == inventory and rows_of(run) == EXPECTED


# --- validation: nothing is created when the inventory is unusable --------------------------

def assert_no_run(match, **overrides):
    with pytest.raises(services.RefreshError, match=match):
        refresh(**overrides)
    assert AnalyticsRun.objects.count() == 0


def test_no_inventory_is_an_error_and_creates_no_run(owner):
    make_products()
    assert_no_run("No sealed inventory")


def test_unsealed_inventory_is_rejected(owner):
    make_inventory(make_products(), seal=False)
    assert_no_run("No sealed inventory")
    assert_no_run("is not sealed", inventory_version="inv-1")


def test_inventory_for_another_cutoff_is_rejected(owner):
    make_inventory(make_products(), cutoff=datetime(2024, 3, 9, tzinfo=SGT))
    assert_no_run("No sealed inventory")
    assert_no_run("is for cutoff", inventory_version="inv-1")


def test_a_missing_product_row_is_rejected(owner):
    products = make_products()
    make_inventory({"alpha": products["alpha"], "beta": products["beta"]})    # gamma has no snapshot row
    assert_no_run("no row for 1 product.*gamma")


def test_unknown_inventory_name_is_rejected(ready):
    assert_no_run("does not exist", inventory_version="nope")


def test_several_matching_inventories_need_an_explicit_choice(owner):
    products = make_products()
    make_inventory(products, version="inv-1")
    make_inventory(products, version="inv-2")
    assert_no_run("choose one with --inventory-version")
    assert refresh(inventory_version="inv-2").run.inventory.version == "inv-2"


def test_future_as_of_is_rejected(ready):
    assert_no_run("in the future", as_of=date.today() + timedelta(days=2))


@pytest.mark.parametrize("overrides, match", [({"keep": 1}, "keep must be at least 2"), ({"timeout": 0}, "timeout")])
def test_option_bounds(ready, overrides, match):
    assert_no_run(match, **overrides)


# --- orphaned runs --------------------------------------------------------------------------

def test_a_run_left_running_by_a_dead_host_is_marked_failed_on_the_next_refresh(ready):
    _, inventory = ready
    orphan = AnalyticsRun.objects.create(inventory=inventory, window_start=at(2023, 3, 8, 0), cutoff=CUTOFF,
                                         status=AnalyticsRun.Status.RUNNING)
    result = refresh()
    orphan.refresh_from_db()
    assert orphan.status == AnalyticsRun.Status.FAILED and orphan.finished_at is not None
    assert result.run.status == AnalyticsRun.Status.COMPLETED
    assert not DailyProductSales.objects.filter(run=orphan).exists()


# --- retention ------------------------------------------------------------------------------

def test_retention_keeps_the_newest_runs_and_their_rows(ready):
    runs = []
    for _ in range(7):
        runs.append(refresh(keep=5))
    assert [result.pruned for result in runs] == [0, 0, 0, 0, 0, 1, 1]
    completed = AnalyticsRun.objects.filter(status=AnalyticsRun.Status.COMPLETED)
    assert completed.count() == 5
    kept = {result.run.pk for result in runs[2:]}
    assert set(completed.values_list("pk", flat=True)) == kept
    assert set(DailyProductSales.objects.values_list("run_id", flat=True)) == kept
    assert not AnalyticsRun.objects.filter(pk__in=[result.run.pk for result in runs[:2]]).exists()


def test_retention_deletes_old_rows_in_the_database_not_in_python(ready):
    for _ in range(3):
        refresh(keep=2)
    with CaptureQueriesContext(connection) as captured:
        refresh(keep=2)                     # prunes one run holding four daily rows
    statements = [query["sql"].lstrip().upper() for query in captured.captured_queries]
    assert any(sql.startswith("DELETE FROM \"REPORTING_DAILYPRODUCTSALES\"") for sql in statements)
    assert not any(sql.startswith("SELECT") and "REPORTING_DAILYPRODUCTSALES" in sql for sql in statements)


def test_retention_ignores_failed_runs_and_other_namespaces(ready, owner):
    products, inventory = ready
    failed = AnalyticsRun.objects.create(inventory=inventory, window_start=at(2023, 3, 8, 0), cutoff=CUTOFF,
                                         status=AnalyticsRun.Status.RUNNING)
    AnalyticsRun.objects.filter(pk=failed.pk).update(status=AnalyticsRun.Status.FAILED, finished_at=at(2024, 3, 8, 1))
    other_products = make_products(OTHER_NS, names=("alpha",))
    make_inventory(other_products, namespace=OTHER_NS, version="other-inv")
    other_run = refresh(namespace=OTHER_NS).run
    for _ in range(4):
        refresh(keep=2)
    assert AnalyticsRun.objects.filter(pk__in=[failed.pk, other_run.pk]).count() == 2
    assert AnalyticsRun.objects.filter(status=AnalyticsRun.Status.COMPLETED, inventory__namespace=NS).count() == 2


# --- publication, statement timeout and locking need real connections and commits -----------

@pytest.mark.django_db(transaction=True)
def test_a_failure_during_publication_leaves_no_partial_run(ready, monkeypatch):
    good = refresh().run

    def fail(run, lines):
        raise RuntimeError("boom")

    monkeypatch.setattr(services, "_complete", fail)
    with pytest.raises(RuntimeError, match="boom"):
        refresh()
    monkeypatch.undo()

    failed = AnalyticsRun.objects.exclude(pk=good.pk).get()
    assert failed.status == AnalyticsRun.Status.FAILED and failed.finished_at is not None
    assert not DailyProductSales.objects.filter(run=failed).exists()      # rows rolled back with the transaction
    assert rows_of(good) == EXPECTED                                        # the earlier completed run is untouched
    assert AnalyticsRun.objects.filter(status=AnalyticsRun.Status.COMPLETED).get() == good


@pytest.mark.django_db(transaction=True)
def test_statement_timeout_is_set_for_the_publish_and_does_not_leak(ready):
    with CaptureQueriesContext(connection) as captured:
        refresh(timeout=120)
    assert any("statement_timeout" in query["sql"] and "120000" in query["sql"] for query in captured.captured_queries)
    with connection.cursor() as cursor:
        cursor.execute("SHOW statement_timeout")
        assert cursor.fetchone()[0] == "0"


@pytest.mark.django_db(transaction=True)
def test_a_slow_publish_is_cancelled_by_the_statement_timeout(ready, monkeypatch):
    monkeypatch.setattr(services, "PUBLISH_SQL", "SELECT pg_sleep(5), 0")
    with pytest.raises(DatabaseError):
        refresh(timeout=1)
    failed = AnalyticsRun.objects.get()
    assert failed.status == AnalyticsRun.Status.FAILED and failed.finished_at is not None
    assert DailyProductSales.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_a_concurrent_refresh_is_skipped_without_writing(ready):
    held, release = threading.Event(), threading.Event()

    def hold_lock():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_lock(%s)", [services.REFRESH_LOCK_KEY])
            held.set()
            release.wait(10)
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [services.REFRESH_LOCK_KEY])
        finally:
            connection.close()

    holder = threading.Thread(target=hold_lock)
    holder.start()
    assert held.wait(10)
    try:
        result = refresh()
        assert result.skipped and result.run is None
        assert AnalyticsRun.objects.count() == 0 and DailyProductSales.objects.count() == 0
    finally:
        release.set()
        holder.join(10)
    assert not refresh().skipped        # the lock is free again once the holder lets go


# --- management command ---------------------------------------------------------------------

def test_command_reports_the_completed_run(ready):
    out = StringIO()
    call_command("refresh_analytics", "--as-of", "2024-03-08", "--namespace", NS, stdout=out)
    text = out.getvalue()
    assert "completed: 4 daily rows from 5 order lines" in text
    assert "business dates 2023-03-08 to 2024-03-07" in text
    assert AnalyticsRun.objects.filter(status=AnalyticsRun.Status.COMPLETED).count() == 1


def test_command_turns_a_refresh_error_into_a_command_error(owner):
    make_products()
    with pytest.raises(CommandError, match="No sealed inventory"):
        call_command("refresh_analytics", "--as-of", "2024-03-08", "--namespace", NS)


def test_command_rejects_a_malformed_date():
    with pytest.raises(CommandError, match="YYYY-MM-DD"):
        call_command("refresh_analytics", "--as-of", "08/03/2024")


def test_command_prints_skipped_when_the_lock_is_held(monkeypatch):
    monkeypatch.setattr(services, "refresh_analytics", lambda **kwargs: services.RefreshResult(skipped=True))
    out = StringIO()
    call_command("refresh_analytics", "--as-of", "2024-03-08", stdout=out)
    assert "Skipped" in out.getvalue()
