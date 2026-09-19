"""snapshot_inventory (PostgreSQL): seals current stock and lead times as an immutable inventory version."""
from datetime import date, datetime, timedelta
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError

from analytics_helpers import NS, OTHER_NS, SGT, add_order, at, make_products
from catalogue.models import Product
from reporting import services
from reporting.models import AnalyticsRun, InventorySnapshot, InventoryVersion

pytestmark = pytest.mark.django_db
AS_OF = date(2024, 3, 8)


def snapshot(**overrides):
    return services.snapshot_inventory(**{"namespace": NS, "as_of": AS_OF, **overrides})


def stored(version):
    return set(version.items.values_list("product__external_id", "stock", "lead_time_days"))


@pytest.fixture
def products():
    made = make_products(names=("alpha", "beta", "gamma"))
    Product.objects.filter(pk=made["alpha"].pk).update(stock=30, lead_time_days=5)
    Product.objects.filter(pk=made["beta"].pk).update(stock=0, lead_time_days=14)              # out of stock still counts
    Product.objects.filter(pk=made["gamma"].pk).update(stock=12, lead_time_days=3, active=False)  # inactive still counts
    return made


def test_snapshot_seals_current_values_for_every_product_including_inactive_and_out_of_stock(products):
    result = snapshot()
    assert result.created and result.rows == 3
    assert result.version.sealed
    assert stored(result.version) == {("alpha", 30, 5), ("beta", 0, 14), ("gamma", 12, 3)}


def test_cutoff_is_midnight_singapore_on_the_as_of_date_and_the_default_name_follows_it(products):
    version = snapshot().version
    assert version.cutoff == datetime(2024, 3, 8, tzinfo=SGT)
    assert version.version == "live-2024-03-08"
    assert snapshot(as_of=date(2024, 3, 9), version="custom").version.version == "custom"


def test_only_the_requested_namespace_is_snapshotted(products):
    make_products(OTHER_NS, names=("other-product",))
    assert {name for name, _, _ in stored(snapshot().version)} == {"alpha", "beta", "gamma"}


def test_later_stock_changes_do_not_alter_the_sealed_version(products):
    version = snapshot().version
    Product.objects.filter(pk=products["alpha"].pk).update(stock=999, lead_time_days=1)
    assert ("alpha", 30, 5) in stored(version)


def test_rerun_verifies_and_reports_unchanged_without_duplicating(products):
    first = snapshot()
    second = snapshot()
    assert first.created and not second.created
    assert second.version.pk == first.version.pk and second.rows == 3
    assert InventoryVersion.objects.count() == 1 and InventorySnapshot.objects.count() == 3


def test_rerun_after_stock_changed_is_rejected_and_leaves_the_original_intact(products):
    version = snapshot().version
    Product.objects.filter(pk=products["alpha"].pk).update(stock=29)
    with pytest.raises(services.SnapshotError, match="different values"):
        snapshot()
    assert ("alpha", 30, 5) in stored(version) and InventoryVersion.objects.count() == 1


def test_rerun_after_a_product_was_added_is_rejected(products):
    snapshot()
    make_products(names=("delta",))
    with pytest.raises(services.SnapshotError, match="different values"):
        snapshot()


def test_same_name_for_another_cutoff_is_rejected(products):
    snapshot(version="fixed")
    with pytest.raises(services.SnapshotError, match="already exists for cutoff"):
        snapshot(version="fixed", as_of=date(2024, 3, 9))


def test_namespace_without_products_is_rejected():
    with pytest.raises(services.SnapshotError, match="no products"):
        snapshot()
    assert InventoryVersion.objects.count() == 0


def test_future_as_of_is_rejected(products):
    with pytest.raises(services.SnapshotError, match="in the future"):
        snapshot(as_of=date.today() + timedelta(days=2))


def test_a_failure_while_writing_rows_leaves_no_version(products, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(InventorySnapshot.objects, "bulk_create", fail)
    with pytest.raises(RuntimeError):
        snapshot()
    assert InventoryVersion.objects.count() == 0


def test_a_concurrent_creation_is_reported_clearly(products, monkeypatch):
    def clash(*args, **kwargs):
        raise IntegrityError("duplicate key")

    monkeypatch.setattr(InventoryVersion.objects, "create", clash)
    with pytest.raises(services.SnapshotError, match="created concurrently"):
        snapshot()


def test_the_snapshot_is_what_refresh_analytics_selects(products):
    owner = get_user_model().objects.create_user(username="snap-user")
    add_order(owner, "o1", [(products["alpha"], 2, "10.00")], at(2024, 3, 5))
    version = snapshot().version
    run = services.refresh_analytics(namespace=NS, as_of=AS_OF).run     # no --inventory-version needed
    assert run.inventory == version and run.status == AnalyticsRun.Status.COMPLETED


def test_command_reports_created_and_then_unchanged(products):
    first, second = StringIO(), StringIO()
    call_command("snapshot_inventory", "--as-of", "2024-03-08", "--namespace", NS, stdout=first)
    call_command("snapshot_inventory", "--as-of", "2024-03-08", "--namespace", NS, stdout=second)
    assert "Sealed: inventory version 'live-2024-03-08' with 3 product row(s)" in first.getvalue()
    assert "Verified unchanged" in second.getvalue()


def test_command_turns_a_snapshot_error_into_a_command_error():
    with pytest.raises(CommandError, match="no products"):
        call_command("snapshot_inventory", "--as-of", "2024-03-08", "--namespace", NS)


def test_command_rejects_a_malformed_date():
    with pytest.raises(CommandError, match="YYYY-MM-DD"):
        call_command("snapshot_inventory", "--as-of", "2024/03/08")
