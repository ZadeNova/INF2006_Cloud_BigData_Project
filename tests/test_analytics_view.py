"""reporting_completed_sale_lines view (PostgreSQL). Batch 6b, migration 0003."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.db import connection

from catalogue.models import Product
from orders.models import Order, OrderItem

pytestmark = pytest.mark.django_db
NAMESPACE = "synthetic/revision-a/historical/v1"
NOON = datetime(2024, 6, 10, 4, 0, tzinfo=timezone.utc)   # 12:00 Singapore


@pytest.fixture
def owner():
    return get_user_model().objects.create_user(username="view-user")


@pytest.fixture
def widget():
    return Product.objects.create(namespace=NAMESPACE, external_id="w", name="Widget", category="Tools",
                                  price="99.00", cost="40.00", stock=10, lead_time_days=5)


@pytest.fixture
def gadget():
    return Product.objects.create(namespace=NAMESPACE, external_id="g", name="Gadget", category="Tools",
                                  price="5.00", cost="2.00", stock=10, lead_time_days=5)


def add_order(owner, external_id, lines, status="completed", placed_at=NOON):
    total = sum(quantity * Decimal(price) for _, quantity, price in lines)
    order = Order.objects.create(owner=owner, namespace=NAMESPACE, external_id=external_id,
                                 status=status, total=total, placed_at=placed_at)
    OrderItem.objects.bulk_create(
        OrderItem(order=order, product=product, quantity=quantity, unit_price=price, external_id=f"{external_id}-{n}")
        for n, (product, quantity, price) in enumerate(lines))
    return order


def view_rows():
    with connection.cursor() as cursor:
        cursor.execute("SELECT namespace, order_id, product_id, quantity, unit_price, line_total, business_date "
                       "FROM reporting_completed_sale_lines ORDER BY order_id, product_id")
        return cursor.fetchall()


def test_view_is_empty_without_orders():
    assert view_rows() == []


def test_only_completed_orders_appear(owner, widget):
    completed = add_order(owner, "o-done", [(widget, 1, "10.00")])
    add_order(owner, "o-cancelled", [(widget, 1, "10.00")], status="cancelled")
    add_order(owner, "o-refunded", [(widget, 1, "10.00")], status="refunded")
    assert [row[1] for row in view_rows()] == [completed.pk]


def test_line_total_uses_the_historical_unit_price(owner, widget):
    # the live product price (99.00) must not leak in: the order line carried 12.50
    add_order(owner, "o1", [(widget, 3, "12.50")])
    (namespace, order_id, product_id, quantity, unit_price, line_total, _), = view_rows()
    assert (namespace, product_id, quantity) == (NAMESPACE, widget.pk, 3)
    assert unit_price == Decimal("12.50")
    assert line_total == Decimal("37.50")


def test_view_exposes_the_raw_timestamp_for_indexable_range_filters(owner, widget):
    order = add_order(owner, "o1", [(widget, 1, "10.00")], placed_at=NOON)
    with connection.cursor() as cursor:
        cursor.execute("SELECT placed_at FROM reporting_completed_sale_lines WHERE placed_at >= %s AND placed_at < %s",
                       [NOON, NOON + timedelta(seconds=1)])
        assert [row[0] for row in cursor.fetchall()] == [order.placed_at]
        cursor.execute("SELECT count(*) FROM reporting_completed_sale_lines WHERE placed_at >= %s", [NOON + timedelta(seconds=1)])
        assert cursor.fetchone()[0] == 0


def test_each_order_line_is_its_own_row(owner, widget, gadget):
    add_order(owner, "o1", [(widget, 2, "10.00"), (gadget, 1, "5.00")])
    rows = view_rows()
    assert len(rows) == 2
    assert sorted(row[2] for row in rows) == sorted([widget.pk, gadget.pk])


def test_live_orders_are_included_like_imported_ones(owner, widget):
    # Live checkout orders have no external id, but a key and fingerprint; the view must not depend on either.
    Order.objects.create(owner=owner, namespace=NAMESPACE, external_id=None, status="completed", total="10.00",
                         placed_at=NOON, idempotency_key=uuid.uuid4(), request_fingerprint="a" * 64)
    order = Order.objects.get(idempotency_key__isnull=False)
    OrderItem.objects.create(order=order, product=widget, quantity=1, unit_price="10.00")
    assert len(view_rows()) == 1


@pytest.mark.parametrize("placed_at, expected", [
    # Singapore is UTC+8 with no daylight saving: 16:00 UTC is midnight of the next business date
    (datetime(2024, 3, 1, 15, 59, 59, tzinfo=timezone.utc), date(2024, 3, 1)),
    (datetime(2024, 3, 1, 16, 0, 0, tzinfo=timezone.utc), date(2024, 3, 2)),
    (datetime(2024, 3, 1, 23, 30, tzinfo=timezone.utc), date(2024, 3, 2)),
    (datetime(2024, 3, 1, 0, 0, tzinfo=timezone.utc), date(2024, 3, 1)),
    # the leap day is a real business date, and 16:00 UTC on 28 Feb is its first instant
    (datetime(2024, 2, 28, 16, 0, tzinfo=timezone.utc), date(2024, 2, 29)),
    (datetime(2024, 2, 29, 15, 59, tzinfo=timezone.utc), date(2024, 2, 29)),
    (datetime(2024, 2, 29, 16, 0, tzinfo=timezone.utc), date(2024, 3, 1)),
    # year end
    (datetime(2024, 12, 31, 16, 0, tzinfo=timezone.utc), date(2025, 1, 1)),
])
def test_business_date_is_the_singapore_calendar_date(owner, widget, placed_at, expected):
    add_order(owner, "o1", [(widget, 1, "10.00")], placed_at=placed_at)
    assert view_rows()[0][6] == expected


def test_business_date_is_independent_of_the_session_time_zone(owner, widget):
    add_order(owner, "o1", [(widget, 1, "10.00")], placed_at=datetime(2024, 3, 1, 16, 0, tzinfo=timezone.utc))
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL TIME ZONE 'America/Los_Angeles'")
    assert view_rows()[0][6] == date(2024, 3, 2)


def test_view_can_be_used_for_the_documented_aggregate(owner, widget, gadget):
    # the shape the refresh command will use: sum per (business date, product)
    add_order(owner, "o1", [(widget, 2, "10.00"), (gadget, 1, "5.00")], placed_at=NOON)
    add_order(owner, "o2", [(widget, 1, "10.00")], placed_at=NOON + timedelta(hours=1))
    add_order(owner, "o3", [(widget, 5, "10.00")], status="refunded", placed_at=NOON)
    with connection.cursor() as cursor:
        cursor.execute("SELECT business_date, product_id, SUM(quantity), SUM(line_total) "
                       "FROM reporting_completed_sale_lines WHERE namespace = %s GROUP BY 1, 2 ORDER BY 2",
                       [NAMESPACE])
        result = cursor.fetchall()
    assert result == [(date(2024, 6, 10), widget.pk, 3, Decimal("30.00")),
                      (date(2024, 6, 10), gadget.pk, 1, Decimal("5.00"))]
