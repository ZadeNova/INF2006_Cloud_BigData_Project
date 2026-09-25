"""Real PostgreSQL invariants; business/import/aggregation workflows remain follow-ups."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError

from accounts.models import CustomerProfile
from cart.models import Cart, CartItem
from catalogue.models import Product, ShoeModel
from orders.models import Order, OrderItem
from reporting.models import AnalyticsRun, DailyProductSales, InventorySnapshot, InventoryVersion

pytestmark = pytest.mark.django_db
CUTOFF = datetime(2025, 1, 1, tzinfo=timezone.utc)
NAMESPACE = "synthetic/revision-a/historical/v1"


@pytest.fixture
def product():
    return Product.objects.create(namespace=NAMESPACE, external_id="p1", name="Example",
        category="Example", price="10.25", cost="5.00", stock=30, lead_time_days=7)


@pytest.fixture
def owner():
    return get_user_model().objects.create_user(username="example-user")


@pytest.fixture
def inventory(product):
    version = InventoryVersion.objects.create(namespace=NAMESPACE, version="seed-1", cutoff=CUTOFF)
    InventorySnapshot.objects.create(inventory=version, product=product, stock=30, lead_time_days=7)
    InventoryVersion.objects.filter(pk=version.pk).update(sealed=True)
    version.refresh_from_db()
    return version


def historical_order(owner, **changes):
    return Order.objects.create(**{**dict(owner=owner, namespace=NAMESPACE, external_id="o1",
        status="completed", total="20.50", placed_at=CUTOFF - timedelta(days=1)), **changes})


@pytest.mark.parametrize("changes", [
    {"stock": -1}, {"lead_time_days": -1}, {"price": "-0.01"}, {"cost": "-0.01"},
    {"namespace": ""}, {"external_id": ""},
])
def test_product_invalid_values_rejected(product, changes):
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.filter(pk=product.pk).update(**changes)


def test_shoe_size_pairs_with_a_model_stays_in_range_and_is_unique_per_model(product):
    model = ShoeModel.objects.create(namespace=NAMESPACE, external_id="s1", name="Example", category="Example")
    for changes in ({"shoe_model": model}, {"size": "9.0"}, {"shoe_model": model, "size": "0.5"},
                    {"shoe_model": model, "size": "20.5"}):
        with pytest.raises(IntegrityError), transaction.atomic():
            Product.objects.filter(pk=product.pk).update(**changes)
    Product.objects.filter(pk=product.pk).update(shoe_model=model, size="9.5")
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.create(namespace=NAMESPACE, external_id="p2", name="Example", category="Example", price="1.00",
                               cost="1.00", stock=1, lead_time_days=1, shoe_model=model, size="9.5")


@pytest.mark.parametrize("column", ["price", "cost"])
def test_postgresql_numeric_nan_rejected(product, column):
    # PostgreSQL numeric NaN compares greater than ordinary values: a lower bound alone is insufficient.
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(f"UPDATE catalogue_product SET {column} = 'NaN' WHERE id = %s", [product.pk])


def test_namespaced_identity_unique_and_immutable(product):
    values = dict(name="Another", category="Example", price=1, cost=0, stock=0, lead_time_days=0)
    Product.objects.create(namespace="synthetic/revision-a/demo/v1", external_id="p1", **values)
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.create(namespace=NAMESPACE, external_id="p1", **values)
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.filter(pk=product.pk).update(namespace="another-mode")


def test_profile_identity_and_account_are_distinct(owner):
    profile = CustomerProfile.objects.create(user=owner, namespace=NAMESPACE, external_id="c1",
        source_signup_at=CUTOFF - timedelta(days=30), channel="example", country="example")
    assert profile.source_signup_at != owner.date_joined
    assert not owner.has_usable_password()
    with pytest.raises(IntegrityError), transaction.atomic():
        CustomerProfile.objects.filter(pk=profile.pk).update(external_id="changed")


@pytest.mark.parametrize("quantity", [0, 1000])
def test_cart_quantity_bounds(owner, product, quantity):
    cart = Cart.objects.create(owner=owner)
    with pytest.raises(IntegrityError), transaction.atomic():
        CartItem.objects.create(cart=cart, product=product, quantity=quantity)


def test_one_cart_and_one_line_per_product(owner, product):
    cart = Cart.objects.create(owner=owner)
    CartItem.objects.create(cart=cart, product=product, quantity=999)
    with pytest.raises(IntegrityError), transaction.atomic():
        Cart.objects.create(owner=owner)
    with pytest.raises(IntegrityError), transaction.atomic():
        CartItem.objects.create(cart=cart, product=product, quantity=1)


def test_order_idempotency_is_user_scoped(owner):
    key = uuid.uuid4()
    values = dict(namespace=NAMESPACE, status="completed", total=0, placed_at=CUTOFF,
        idempotency_key=key, request_fingerprint="a" * 64)
    Order.objects.create(owner=owner, **values)
    other = get_user_model().objects.create_user(username="other-user")
    Order.objects.create(owner=other, **values)
    with pytest.raises(IntegrityError), transaction.atomic():
        Order.objects.create(owner=owner, **values)


@pytest.mark.parametrize("changes", [
    {"status": "unknown"}, {"total": "-1"}, {"external_id": ""},
    {"idempotency_key": uuid.UUID(int=1)}, {"external_id": None},
])
def test_order_origin_and_values(owner, changes):
    with pytest.raises(IntegrityError), transaction.atomic():
        historical_order(owner, **changes)


def test_historical_prices_and_references_survive_retirement(owner, product):
    order = historical_order(owner)
    item = OrderItem.objects.create(order=order, product=product, external_id="line-1", quantity=2, unit_price="10.25")
    Product.objects.filter(pk=product.pk).update(price="25.00", active=False)
    item.refresh_from_db()
    assert item.unit_price == Decimal("10.25")
    with pytest.raises(ProtectedError):
        product.delete()
    with pytest.raises(ProtectedError):
        owner.delete()
    with pytest.raises(ProtectedError):
        order.delete()


def test_order_item_cannot_cross_fixture_modes(owner, product):
    order = historical_order(owner, namespace="synthetic/revision-a/demo/v1")
    with pytest.raises(IntegrityError), transaction.atomic():
        OrderItem.objects.create(order=order, product=product, quantity=1, unit_price=1)


def test_live_stock_change_does_not_change_historical_inventory(product, inventory):
    Product.objects.filter(pk=product.pk).update(stock=1, lead_time_days=2)
    snapshot = inventory.items.get(product=product)
    assert (snapshot.stock, snapshot.lead_time_days) == (30, 7)


@pytest.mark.parametrize("operation", ["update_row", "delete_row", "append_row", "change_cutoff", "unseal"])
def test_published_inventory_is_immutable(product, inventory, operation):
    with pytest.raises(IntegrityError), transaction.atomic():
        if operation == "update_row":
            InventorySnapshot.objects.filter(inventory=inventory).update(stock=999)
        elif operation == "delete_row":
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM reporting_inventorysnapshot WHERE inventory_id = %s", [inventory.pk])
        elif operation == "append_row":
            InventorySnapshot.objects.create(inventory=inventory, product=product, stock=9, lead_time_days=1)
        elif operation == "change_cutoff":
            InventoryVersion.objects.filter(pk=inventory.pk).update(cutoff=CUTOFF + timedelta(days=1))
        else:
            InventoryVersion.objects.filter(pk=inventory.pk).update(sealed=False)


def test_empty_or_cross_namespace_inventory_rejected(product):
    version = InventoryVersion.objects.create(namespace="other", version="1", cutoff=CUTOFF)
    with pytest.raises(IntegrityError), transaction.atomic():
        InventoryVersion.objects.filter(pk=version.pk).update(sealed=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        InventorySnapshot.objects.create(inventory=version, product=product, stock=1, lead_time_days=1)
    with pytest.raises(IntegrityError), transaction.atomic():
        InventoryVersion.objects.create(namespace=NAMESPACE, version="already-sealed", cutoff=CUTOFF, sealed=True)


def test_run_requires_sealed_matching_cutoff(inventory):
    values = dict(inventory=inventory, window_start=CUTOFF - timedelta(days=7), status="running")
    with pytest.raises(IntegrityError), transaction.atomic():
        AnalyticsRun.objects.create(cutoff=CUTOFF + timedelta(days=1), **values)
    unsealed = InventoryVersion.objects.create(namespace=NAMESPACE, version="pending", cutoff=CUTOFF)
    with pytest.raises(IntegrityError), transaction.atomic():
        AnalyticsRun.objects.create(cutoff=CUTOFF, **{**values, "inventory": unsealed})


def test_summaries_are_versioned_and_require_snapshot(product, inventory):
    values = dict(inventory=inventory, window_start=CUTOFF - timedelta(days=7), cutoff=CUTOFF, status="running")
    run1 = AnalyticsRun.objects.create(**values)
    run2 = AnalyticsRun.objects.create(**values)
    line = dict(product=product, business_date=(CUTOFF - timedelta(days=1)).date(), units=2, sales_amount="20.50")
    DailyProductSales.objects.create(run=run1, **line)
    DailyProductSales.objects.create(run=run2, **line)
    with pytest.raises(IntegrityError), transaction.atomic():
        DailyProductSales.objects.create(run=run1, **line)
    missing = Product.objects.create(namespace=NAMESPACE, external_id="missing-snapshot", name="Example",
        category="Example", price=1, cost=0, stock=0, lead_time_days=0)
    with pytest.raises(IntegrityError), transaction.atomic():
        DailyProductSales.objects.create(run=run1, **{**line, "product": missing})
    with pytest.raises(IntegrityError), transaction.atomic():
        AnalyticsRun.objects.filter(pk=run1.pk).update(cutoff=CUTOFF + timedelta(days=1))
