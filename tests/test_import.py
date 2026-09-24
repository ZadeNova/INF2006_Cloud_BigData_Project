"""Hand-checkable CSV imports against PostgreSQL; no production datasets in tests."""
import copy
import csv
from datetime import timedelta
from decimal import Decimal
from io import StringIO
import json
import uuid

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError

from accounts.models import CustomerProfile
from cart.models import Cart, CartItem
from catalogue.models import Product
from config import dataset
from orders.models import Order, OrderItem
from orders.services import checkout, fingerprint_for
from reporting.models import InventorySnapshot, InventoryVersion
from reporting.services import _require_every_product

pytestmark = pytest.mark.django_db
NS = settings.DEMO_NAMESPACE


@pytest.fixture
def source(tmp_path):
    rows = {
        "customers": [dict(customer_id=f"C{i}", created_at="2024-02-27", country_code="SG", acquisition_channel="organic", customer_segment="consumer") for i in range(1, 4)],
        "products": [dict(product_id=f"P{i}", sku=f"SKU{i}", product_name=f"Item {i}", category="home", list_price="10.005", unit_cost="4.00") for i in range(1, 4)],
        "orders": [], "order_items": [],
    }
    for i, status in enumerate(["completed", "cancelled", "refunded", "partially_refunded", "completed"], 1):
        rows["orders"].append(dict(order_id=f"O{i}", customer_id=f"C{1+(i % 3)}", ordered_at=f"2024-02-{28 if i < 3 else 29}T12:00:00Z", order_status=status,
                                   currency="USD", subtotal="29.02", tax_amount="2.00", shipping_amount="3.00", order_total="34.02"))
        rows["order_items"] += [dict(order_item_id=f"L{i}a", order_id=f"O{i}", product_id="P1", quantity="2", unit_price="10.005", discount_amount="1.00", line_total="19.02"),
                                dict(order_item_id=f"L{i}b", order_id=f"O{i}", product_id="P2", quantity="1", unit_price="10.00", discount_amount="0.00", line_total="10.00")]
    return tmp_path, rows


def write_source(source):
    path, rows = source
    for table, values in rows.items():
        with (path / f"{table}.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=values[0].keys())
            writer.writeheader()
            writer.writerows(values)
    return path


def run_import(source, **kwargs):
    path = write_source(source)
    output = StringIO()
    call_command("import_dataset", source=path, namespace=kwargs.pop("namespace", NS),
                 rejects_file=path.parent / f"{path.name}-rejects.json", stdout=output, **kwargs)
    return output.getvalue()


def test_counts_mappings_rounding_and_sealed_inventory(source):
    output = run_import(source)
    assert get_user_model().objects.count() == CustomerProfile.objects.count() == 3
    assert Product.objects.count() == 3
    assert Order.objects.count() == 5 and OrderItem.objects.count() == 10
    assert Order.objects.filter(status="refunded").count() == 2
    for profile in CustomerProfile.objects.select_related("user"):
        assert profile.user.username == dataset.username(NS, profile.external_id)
        assert not profile.user.has_usable_password()
        assert not profile.user.email and not profile.user.is_staff
        assert profile.country == "SG" and profile.channel == "organic"
    assert Order.objects.get(external_id="O1").owner.customerprofile.external_id == "C2"
    assert Order.objects.get(external_id="O1").total == Decimal("30.02")
    assert OrderItem.objects.get(external_id="L1a").unit_price == Decimal("10.01")
    assert Product.objects.get(external_id="P1").price == Decimal("10.01")
    inventory = InventoryVersion.objects.get()
    assert inventory.sealed and inventory.cutoff.isoformat() == "2024-02-29T16:00:00+00:00"
    assert inventory.items.count() == 3
    assert set(inventory.items.values_list("product_id", "stock", "lead_time_days")) == set(Product.objects.values_list("pk", "stock", "lead_time_days"))
    assert "application_lines=60.04" in output


def test_replay_preserves_checkout_credentials_cart_session_and_live_product(source, client):
    run_import(source)
    user = CustomerProfile.objects.get(external_id="C1").user
    user.set_password("fixture-only-password")
    user.save()
    product = Product.objects.get(external_id="P1")
    product.stock = 50
    product.save()
    cart = Cart.objects.create(owner=user)
    CartItem.objects.create(cart=cart, product=product, quantity=2)
    live = checkout(user, uuid.uuid4(), fingerprint_for([(product, 2)]))
    CartItem.objects.create(cart=cart, product=product, quantity=3)
    Product.objects.filter(pk=product.pk).update(name="Live name", price="99.99", cost="1.23", active=False, lead_time_days=99)
    client.force_login(user)
    session = Session.objects.get()
    snapshots = list(InventorySnapshot.objects.values())
    password = user.password
    # Row ordering is irrelevant to both identity and per-product generation.
    for rows in source[1].values():
        rows.reverse()
    output = run_import(source)
    assert "orders: created=0 unchanged=5" in output
    assert "order_items: created=0 unchanged=10" in output
    assert "products: created=0 unchanged=3" in output
    product.refresh_from_db()
    user.refresh_from_db()
    assert product.stock == 48 and product.name == "Live name" and product.price == Decimal("99.99")
    assert product.cost == Decimal("1.23") and not product.active and product.lead_time_days == 99
    assert user.password == password
    assert cart.items.get().quantity == 3 and Order.objects.get(pk=live.pk).total == Decimal("20.02")
    assert Session.objects.get(pk=session.pk).session_data == session.session_data
    assert snapshots == list(InventorySnapshot.objects.values())
    assert Order.objects.count() == 6 and get_user_model().objects.count() == 3


def test_source_conflict_and_database_failure_rollback(source, monkeypatch):
    # Fail the final stage, after users/products/orders/items have been inserted.
    original = InventorySnapshot.objects.bulk_create
    def fail(*args, **kwargs):
        raise IntegrityError("fixture late failure")
    monkeypatch.setattr(InventorySnapshot.objects, "bulk_create", fail)
    with pytest.raises(CommandError, match="rolled back"):
        run_import(source)
    assert not get_user_model().objects.exists() and not Product.objects.exists() and not Order.objects.exists()
    monkeypatch.setattr(InventorySnapshot.objects, "bulk_create", original)
    run_import(source)
    source[1]["products"][0]["list_price"] = "11.00"
    with pytest.raises(CommandError, match="accepted source manifest"):
        run_import(source)
    assert Product.objects.get(external_id="P1").price == Decimal("10.01")
    assert Order.objects.count() == 5 and InventoryVersion.objects.count() == 1


@pytest.mark.parametrize("table,field,value,reason", [
    ("products", "list_price", "-1", "nonnegative"),
    ("products", "list_price", "NaN", "finite"),
    ("products", "list_price", "10000000000", "precision"),
    ("order_items", "quantity", "0", "positive"),
    ("orders", "order_status", "pending", "unknown order status"),
    ("orders", "customer_id", "absent", "missing/rejected customer"),
    ("order_items", "product_id", "absent", "missing/rejected product"),
    ("order_items", "order_id", "absent", "missing/rejected order"),
    ("order_items", "line_total", "1.00", "line total !="),
    ("orders", "order_total", "1.00", "subtotal + tax"),
    ("customers", "created_at", "2024-03-02", "order before customer signup"),
])
def test_validation_rejects(source, table, field, value, reason):
    source[1][table][0][field] = value
    with pytest.raises(CommandError, match="Rejected rows"):
        run_import(source)
    audit = json.loads((source[0].parent / f"{source[0].name}-rejects.json").read_text())
    assert any(reason in message for row in audit["rejects"] for message in row["reasons"])
    assert not Order.objects.exists() and not get_user_model().objects.exists()


def test_duplicate_ids_reject_all_copies_and_dependents(source):
    source[1]["customers"].append(copy.deepcopy(source[1]["customers"][1]))
    output = run_import(source, allow_rejects=True)
    assert "customers: read=4 valid=2 rejected=2" in output
    assert not CustomerProfile.objects.filter(external_id="C2").exists()
    assert not Order.objects.filter(external_id__in=["O1", "O4"]).exists()
    assert Order.objects.count() == 3 and OrderItem.objects.count() == 6
    assert "orders: created=0 unchanged=3" in run_import(source, allow_rejects=True)


def test_invalid_line_rejects_whole_order_and_siblings(source):
    source[1]["order_items"][0]["quantity"] = "0"
    run_import(source, allow_rejects=True)
    assert not Order.objects.filter(external_id="O1").exists()
    assert not OrderItem.objects.filter(external_id__in=["L1a", "L1b"]).exists()
    assert Order.objects.count() == 4


def test_net_subtotal_reconciliation(source):
    source[1]["orders"][0].update(subtotal="28.02", order_total="33.02")
    with pytest.raises(CommandError, match="Rejected rows"):
        run_import(source)
    audit = (source[0].parent / f"{source[0].name}-rejects.json").read_text()
    assert "line net sum != subtotal" in audit


def test_constant_shift_leap_day_timezone_and_future_refusal(source):
    run_import(source)
    original = list(Order.objects.order_by("external_id").values_list("placed_at", flat=True))
    signup = CustomerProfile.objects.get(namespace=NS, external_id="C1").source_signup_at
    output = run_import(source, namespace="shifted", shift_anchor="2025-03-01")
    shifted = list(Order.objects.filter(namespace="shifted").order_by("external_id").values_list("placed_at", flat=True))
    assert {new - old for old, new in zip(original, shifted)} == {timedelta(days=365)}
    assert CustomerProfile.objects.get(namespace="shifted", external_id="C1").source_signup_at - signup == timedelta(days=365)
    assert max(shifted) < InventoryVersion.objects.get(namespace="shifted").cutoff
    assert "offset_days=365" in output
    assert dataset.timestamp("2024-02-29T23:00:00Z").date().isoformat() == "2024-03-01"
    source[1]["customers"].append(dict(source[1]["customers"][0], customer_id="future", created_at="2024-03-02"))
    with pytest.raises(CommandError, match="at/after cutoff"):
        run_import(source, namespace="future", shift_anchor="2025-03-01")
    assert not CustomerProfile.objects.filter(namespace="future").exists()


def test_namespace_isolation_and_deterministic_generation(source):
    source[1]["products"][2]["unit_cost"] = ""
    run_import(source)
    expected = list(Product.objects.filter(namespace=NS).order_by("external_id").values_list("external_id", "stock", "lead_time_days", "cost"))
    assert [(key, stock, lead) for key, stock, lead, _ in expected] == [("P1", 11, 10), ("P2", 2, 10), ("P3", 58, 10)]
    for rows in source[1].values():
        rows.reverse()
    run_import(source, namespace="another")
    assert expected == list(Product.objects.filter(namespace="another").order_by("external_id").values_list("external_id", "stock", "lead_time_days", "cost"))
    assert get_user_model().objects.count() == 6
    assert Product.objects.get(namespace=NS, external_id="P3").cost == Decimal("6.01")
    for product in Product.objects.all():
        assert 3 <= product.lead_time_days <= 14
        if product.external_id == "P3":
            assert 20 <= product.stock <= 200


def test_existing_username_never_adopted(source):
    get_user_model().objects.create_user(username=dataset.username(NS, "C2"))
    with pytest.raises(CommandError, match="username already owned"):
        run_import(source)
    assert get_user_model().objects.count() == 1 and not CustomerProfile.objects.exists()


def test_historical_database_tampering_conflicts(source):
    run_import(source)
    Order.objects.filter(external_id="O1").update(total="1.00")
    with pytest.raises(CommandError, match="total differs"):
        run_import(source)


def test_replay_verifies_generated_values_against_sealed_snapshot(source, monkeypatch):
    run_import(source)
    snapshots = list(InventorySnapshot.objects.values())
    original = dataset.prepare
    def different_expected(*args, **kwargs):
        result = original(*args, **kwargs)
        args[1]["products"]["P1"]["stock"] += 1
        return result
    monkeypatch.setattr(dataset, "prepare", different_expected)
    with pytest.raises(CommandError, match="sealed inventory differs"):
        run_import(source)
    assert list(InventorySnapshot.objects.values()) == snapshots


def test_seed_demo_without_products():
    call_command("seed_demo", no_products=True)
    assert not Product.objects.exists()
    operator = get_user_model().objects.get(username="demo-operator")
    assert operator.groups.filter(name="store_operator").exists()
    call_command("seed_demo")
    assert Product.objects.count() == 14


def test_demo_products_rejected_and_clean_import_inventory_validates(source):
    call_command("seed_demo")
    demo_products = list(Product.objects.values())
    users = get_user_model().objects.count()
    with pytest.raises(CommandError, match="products outside the accepted source"):
        run_import(source)
    assert list(Product.objects.values()) == demo_products
    assert get_user_model().objects.count() == users
    assert not CustomerProfile.objects.exists() and not Order.objects.exists()
    assert not InventoryVersion.objects.exists()
    # Another namespace is a safe alternative; never delete/reset the demo products.
    run_import(source, namespace="clean-history")
    inventory = InventoryVersion.objects.get(namespace="clean-history")
    _require_every_product("clean-history", inventory)
    assert inventory.sealed and inventory.items.count() == 3


def test_source_owned_category_drift_conflicts_without_overwrite(source):
    run_import(source)
    Product.objects.filter(external_id="P1").update(category="changed-category")
    with pytest.raises(CommandError, match="category differs"):
        run_import(source)
    assert Product.objects.get(external_id="P1").category == "changed-category"
    assert Order.objects.count() == 5 and InventorySnapshot.objects.count() == 3
