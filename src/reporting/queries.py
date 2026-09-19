"""Read-side analytics queries for the operator dashboard.

Every query takes one AnalyticsRun and never selects across runs (docs/ANALYTICS.md: readers select one
completed run). All aggregation is SQL over the precomputed reporting_dailyproductsales rows and the sealed
inventory snapshot, with the SQL kept as named constants so the same queries can be reused and explained
(docs/INF2003_BASELINE.md rule 4). Dates are business dates (Singapore calendar dates).
"""
from datetime import timedelta
from decimal import Decimal
from typing import NamedTuple

from django.db import connection

from . import ranges
from .models import AnalyticsRun

# Days used for average daily sales, coverage and flags. Defined by the metric, not by the calendar.
COVERAGE_DATES = 7

HISTORY_START_SQL = "SELECT MIN(business_date) FROM reporting_dailyproductsales WHERE run_id = %s"

SUMMARY_SQL = """
SELECT COALESCE(SUM(units), 0), COALESCE(SUM(sales_amount), 0)
FROM reporting_dailyproductsales
WHERE run_id = %s AND business_date BETWEEN %s AND %s
"""

# The %s marks inside the VALUES list are filled from the buckets; the final %s is the run id.
BUCKET_SQL = """
WITH b (bucket_start, bucket_end) AS (VALUES {values})
SELECT b.bucket_start, b.bucket_end, COALESCE(SUM(d.units), 0), COALESCE(SUM(d.sales_amount), 0)
FROM b
LEFT JOIN reporting_dailyproductsales d
       ON d.run_id = %s AND d.business_date BETWEEN b.bucket_start AND b.bucket_end
GROUP BY b.bucket_start, b.bucket_end
ORDER BY b.bucket_start
"""

CATEGORY_SQL = """
SELECT p.category, SUM(d.units), SUM(d.sales_amount)
FROM reporting_dailyproductsales d
JOIN catalogue_product p ON p.id = d.product_id
WHERE d.run_id = %s AND d.business_date BETWEEN %s AND %s
GROUP BY p.category
ORDER BY SUM(d.sales_amount) DESC, p.category
"""

TOP_SELLERS_SQL = """
SELECT ROW_NUMBER() OVER (ORDER BY SUM(d.units) DESC, p.id) AS rank,
       p.id, p.external_id, p.name, p.category, SUM(d.units), SUM(d.sales_amount)
FROM reporting_dailyproductsales d
JOIN catalogue_product p ON p.id = d.product_id
WHERE d.run_id = %s AND d.business_date BETWEEN %s AND %s
GROUP BY p.id
ORDER BY SUM(d.units) DESC, p.id
LIMIT %s
"""

# Stock and lead time come from the run's sealed snapshot, never from mutable Product values. The flag
# compares stock / (units / 7) <= lead time as stock * 7 <= lead_time * units, so the threshold is exact
# integer arithmetic. `sufficient` is false when the run has fewer than seven complete dates of history.
COVERAGE_SQL = """
SELECT p.id, p.external_id, p.name, p.category, s.stock, s.lead_time_days,
       COALESCE(w.units, 0) AS units_7d,
       ROUND(COALESCE(w.units, 0) / %(dates)s::numeric, 2) AS avg_daily_units,
       CASE WHEN %(sufficient)s AND COALESCE(w.units, 0) > 0
            THEN ROUND(s.stock * %(dates)s::numeric / w.units, 2) END AS coverage_days,
       (%(sufficient)s AND COALESCE(w.units, 0) > 0
            AND s.stock * %(dates)s <= s.lead_time_days * w.units) AS flagged
FROM reporting_inventorysnapshot s
JOIN catalogue_product p ON p.id = s.product_id
LEFT JOIN (
    SELECT product_id, SUM(units) AS units
    FROM reporting_dailyproductsales
    WHERE run_id = %(run_id)s AND business_date BETWEEN %(first)s AND %(last)s
    GROUP BY product_id
) w ON w.product_id = p.id
WHERE s.inventory_id = %(inventory_id)s
ORDER BY flagged DESC, coverage_days ASC NULLS LAST, p.id
"""


class Summary(NamedTuple):
    units: int
    sales_amount: Decimal


class BucketSales(NamedTuple):
    start: object
    end: object
    units: int
    sales_amount: Decimal


class CategorySales(NamedTuple):
    category: str
    units: int
    sales_amount: Decimal


class TopSeller(NamedTuple):
    rank: int
    product_id: int
    external_id: str
    name: str
    category: str
    units: int
    sales_amount: Decimal


class CoverageRow(NamedTuple):
    product_id: int
    external_id: str
    name: str
    category: str
    stock: int
    lead_time_days: int
    units_7d: int
    avg_daily_units: Decimal
    coverage_days: Decimal | None
    status: str          # flagged | ok | unavailable | insufficient_history


def latest_completed_run(namespace):
    """The newest completed run for the namespace, or None. Failed and running runs are never returned."""
    return (AnalyticsRun.objects
            .filter(status=AnalyticsRun.Status.COMPLETED, inventory__namespace=namespace)
            .select_related("inventory")
            .order_by("-finished_at", "-started_at")
            .first())


def history_start(run):
    """Earliest business date with a row in the run, or None when the run holds no sales at all."""
    return _fetch_one(HISTORY_START_SQL, [run.pk])[0]


def sales_summary(run, span):
    units, amount = _fetch_one(SUMMARY_SQL, [run.pk, span.start, span.end])
    return Summary(int(units), amount)


def bucket_sales(run, bucket_list):
    """Units and sales per bucket, zero-filled, in bucket order. Works for the selected and shifted comparison buckets."""
    if not bucket_list:
        return []
    values = ", ".join(["(%s::date, %s::date)"] * len(bucket_list))
    params = [day for item in bucket_list for day in (item.start, item.end)] + [run.pk]
    return [BucketSales(start, end, int(units), amount)
            for start, end, units, amount in _fetch_all(BUCKET_SQL.format(values=values), params)]


def category_sales(run, span):
    """Sales per product category over the span, highest first. Uses each product's current category."""
    return [CategorySales(category, int(units), amount)
            for category, units, amount in _fetch_all(CATEGORY_SQL, [run.pk, span.start, span.end])]


def top_sellers(run, span, limit=10):
    """Top products by completed units in the span; ties break on the lower product ID."""
    return [TopSeller(int(rank), product_id, external_id, name, category, int(units), amount)
            for rank, product_id, external_id, name, category, units, amount
            in _fetch_all(TOP_SELLERS_SQL, [run.pk, span.start, span.end, limit])]


def coverage(run):
    """Average daily sales, stock coverage and replenishment status for every product in the run's inventory.

    Always uses the seven complete business dates ending at L, whatever range the dashboard shows. Sorted by
    urgency: flagged first by lowest coverage, then the rest, products with no coverage last.
    """
    latest = ranges.latest_complete_date(run.cutoff)
    first = latest - timedelta(days=COVERAGE_DATES - 1)
    earliest = history_start(run)
    sufficient = earliest is not None and earliest <= first

    rows = _fetch_all(COVERAGE_SQL, {
        "dates": COVERAGE_DATES, "sufficient": sufficient, "run_id": run.pk, "first": first, "last": latest,
        "inventory_id": run.inventory_id})
    result = []
    for product_id, external_id, name, category, stock, lead, units, average, days, flagged in rows:
        if not sufficient:
            status = "insufficient_history"
        elif units == 0:
            status = "unavailable"
        else:
            status = "flagged" if flagged else "ok"
        result.append(CoverageRow(product_id, external_id, name, category, stock, lead, int(units), average, days, status))
    return result


def _fetch_one(sql, params):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def _fetch_all(sql, params):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()
