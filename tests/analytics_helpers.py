"""Shared builders for the analytics tests: products, sealed inventories, orders and completed runs."""
from datetime import datetime
from decimal import Decimal

from django.utils import timezone

from catalogue.models import Product
from orders.models import Order, OrderItem
from reporting import ranges
from reporting.models import AnalyticsRun, DailyProductSales, InventorySnapshot, InventoryVersion

SGT = ranges.BUSINESS_TZ
NS = "synthetic/revision-a/historical/v1"
OTHER_NS = "synthetic/revision-a/other/v1"
DEFAULT_CUTOFF = datetime(2024, 3, 8, tzinfo=SGT)


def at(year, month, day, hour=12, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=SGT)


def make_products(namespace=NS, names=("alpha", "beta", "gamma"), categories=None):
    categories = categories or {}
    return {name: Product.objects.create(namespace=namespace, external_id=name, name=name.title(),
                                         category=categories.get(name, "Tools"), price="10.00", cost="4.00",
                                         stock=50, lead_time_days=7) for name in names}


def make_inventory(products, cutoff=DEFAULT_CUTOFF, version="inv-1", namespace=NS, seal=True, values=None):
    """A sealed (by default) inventory version; `values` maps product name to (stock, lead_time_days)."""
    values = values or {}
    inventory = InventoryVersion.objects.create(namespace=namespace, version=version, cutoff=cutoff)
    InventorySnapshot.objects.bulk_create(
        InventorySnapshot(inventory=inventory, product=product, stock=values.get(name, (50, 7))[0],
                          lead_time_days=values.get(name, (50, 7))[1]) for name, product in products.items())
    if seal:
        InventoryVersion.objects.filter(pk=inventory.pk).update(sealed=True)
        inventory.refresh_from_db()
    return inventory


def add_order(owner, external_id, lines, placed_at, status="completed", namespace=NS):
    total = sum(quantity * Decimal(price) for _, quantity, price in lines)
    order = Order.objects.create(owner=owner, namespace=namespace, external_id=external_id, status=status,
                                 total=total, placed_at=placed_at)
    OrderItem.objects.bulk_create(
        OrderItem(order=order, product=product, quantity=quantity, unit_price=price, external_id=f"{external_id}-{n}")
        for n, (product, quantity, price) in enumerate(lines))
    return order


def make_run(inventory, rows, finished_at=None, status=AnalyticsRun.Status.COMPLETED):
    """A run with explicit daily rows [(date, product, units, amount)], for tests that need exact control."""
    run = AnalyticsRun.objects.create(inventory=inventory, window_start=inventory.cutoff.replace(year=inventory.cutoff.year - 1),
                                      cutoff=inventory.cutoff, status=AnalyticsRun.Status.RUNNING)
    DailyProductSales.objects.bulk_create(
        DailyProductSales(run=run, business_date=day, product=product, units=units, sales_amount=amount)
        for day, product, units, amount in rows)
    if status != AnalyticsRun.Status.RUNNING:
        AnalyticsRun.objects.filter(pk=run.pk).update(status=status, finished_at=finished_at or timezone.now())
    run.refresh_from_db()
    return run
