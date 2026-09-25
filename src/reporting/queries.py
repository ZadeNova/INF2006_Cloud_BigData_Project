"""Read-side analytics queries for the operator dashboard.

Every query takes one AnalyticsRun and never selects across runs (docs/ANALYTICS.md: readers select one
completed run). All aggregation is SQL over the precomputed reporting_dailyproductsales rows and the sealed
inventory snapshot, with the SQL kept as named constants so the same queries can be reused and explained
(docs/INF2003_BASELINE.md rule 4). Dates are business dates (Singapore calendar dates).
"""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import NamedTuple

from django.db import connection
from django.db.models import Avg, Case, Count, F, IntegerField, Max, Sum, Value, When, Window
from django.db.models.functions import RowNumber

from . import ranges
from .models import AnalyticsRun, CustomerSegment

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

# Top sellers are shoe models: every size (SKU) of a model counts together. A product without a model
# (legacy or size-less rows) is its own group. Ties break on the group's lowest product ID.
TOP_SELLERS_SQL = """
SELECT ROW_NUMBER() OVER (ORDER BY SUM(d.units) DESC, MIN(p.id)) AS rank,
       MIN(p.id), MIN(COALESCE(m.external_id, p.external_id)), MIN(COALESCE(m.name, p.name)),
       MIN(COALESCE(m.category, p.category)), SUM(d.units), SUM(d.sales_amount)
FROM reporting_dailyproductsales d
JOIN catalogue_product p ON p.id = d.product_id
LEFT JOIN catalogue_shoemodel m ON m.id = p.shoe_model_id
WHERE d.run_id = %s AND d.business_date BETWEEN %s AND %s
GROUP BY m.id, CASE WHEN m.id IS NULL THEN p.id END
ORDER BY SUM(d.units) DESC, MIN(p.id)
LIMIT %s
"""

# Units and sales per shoe size across all models. Products without a size are left out.
SIZE_SQL = """
SELECT p.size, SUM(d.units), SUM(d.sales_amount)
FROM reporting_dailyproductsales d
JOIN catalogue_product p ON p.id = d.product_id
WHERE d.run_id = %s AND d.business_date BETWEEN %s AND %s AND p.size IS NOT NULL
GROUP BY p.size
ORDER BY p.size
"""

# Stock and lead time come from the run's sealed snapshot, never from mutable Product values. The flag
# compares stock / (units / 7) <= lead time as stock * 7 <= lead_time * units, so the threshold is exact.
# stock is cast to numeric first: a PostgreSQL integer stock * 7 overflows above about 307 million, which
# the schema allows (AQRY-001). `sufficient` is false when the run has fewer than seven complete dates.
COVERAGE_SQL = """
SELECT p.id, p.external_id, p.name, p.category, p.size, s.stock, s.lead_time_days,
       COALESCE(w.units, 0) AS units_7d,
       ROUND(COALESCE(w.units, 0) / %(dates)s::numeric, 2) AS avg_daily_units,
       CASE WHEN %(sufficient)s AND COALESCE(w.units, 0) > 0
            THEN ROUND(s.stock * %(dates)s::numeric / w.units, 2) END AS coverage_days,
       (%(sufficient)s AND COALESCE(w.units, 0) > 0
            AND s.stock::numeric * %(dates)s <= s.lead_time_days * w.units) AS flagged
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


class SizeSales(NamedTuple):
    size: Decimal
    units: int
    sales_amount: Decimal

    @property
    def label(self):
        return f"US {self.size.normalize():f}"


class TopSeller(NamedTuple):
    rank: int
    product_id: int         # lowest product ID of the shoe model (the tie break)
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
    size: Decimal | None
    stock: int
    lead_time_days: int
    units_7d: int
    avg_daily_units: Decimal
    coverage_days: Decimal | None
    status: str          # flagged | ok | unavailable | insufficient_history


class SegmentBreakdown(NamedTuple):
    segment_label: str
    cluster_id: int
    customers: int
    sales_amount: Decimal
    sales_share_percent: Decimal
    mean_recency_days: Decimal
    mean_frequency_orders: Decimal
    mean_monetary_total: Decimal


class SegmentOverview(NamedTuple):
    model_version: str
    k_clusters: int
    silhouette_score: Decimal | None
    customers: int
    sales_amount: Decimal
    segments: list[SegmentBreakdown]


class SegmentCustomer(NamedTuple):
    customer_id: int
    customer_reference: str
    segment_label: str
    recency_days: int
    frequency_orders: int
    monetary_total: Decimal


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


def size_sales(run, span):
    """Units and sales per shoe size over the span, smallest size first."""
    return [SizeSales(size, int(units), amount) for size, units, amount in _fetch_all(SIZE_SQL, [run.pk, span.start, span.end])]


def top_sellers(run, span, limit=10):
    """Top shoe models by completed units in the span (all sizes together); ties break on the lower product ID."""
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
    for product_id, external_id, name, category, size, stock, lead, units, average, days, flagged in rows:
        if not sufficient:
            status = "insufficient_history"
        elif units == 0:
            status = "unavailable"
        else:
            status = "flagged" if flagged else "ok"
        result.append(CoverageRow(product_id, external_id, name, category, size, stock, lead, int(units), average, days,
                                  status))
    return result


def customer_segment_overview(run):
    """Latest customer-segment snapshot for the run, or None when no optional ML output is loaded."""
    latest = (CustomerSegment.objects.filter(run=run)
              .values("model_version")
              .annotate(last_loaded=Max("created_at"))
              .order_by("-last_loaded", "-model_version")
              .first())
    if latest is None:
        return None

    model_version = latest["model_version"]
    rows = list(
        CustomerSegment.objects.filter(run=run, model_version=model_version)
        .values("segment_label", "cluster_id")
        .annotate(
            customers=Count("id"),
            sales_amount=Sum("monetary_total"),
            mean_recency_days=Avg("recency_days"),
            mean_frequency_orders=Avg("frequency_orders"),
            mean_monetary_total=Avg("monetary_total"),
            k_clusters=Max("k_clusters"),
            silhouette_score=Max("silhouette_score"),
        )
        .order_by("-sales_amount", "cluster_id")
    )
    if not rows:
        return None

    total_customers = sum(int(row["customers"]) for row in rows)
    total_sales = sum((row["sales_amount"] or Decimal("0") for row in rows), Decimal("0"))
    result = []
    for row in rows:
        sales = row["sales_amount"] or Decimal("0")
        share = (Decimal("0.0") if total_sales == 0 else
                 (Decimal(sales) / total_sales * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
        result.append(
            SegmentBreakdown(
                segment_label=row["segment_label"],
                cluster_id=int(row["cluster_id"]),
                customers=int(row["customers"]),
                sales_amount=sales,
                sales_share_percent=share,
                mean_recency_days=Decimal(row["mean_recency_days"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                mean_frequency_orders=Decimal(row["mean_frequency_orders"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                mean_monetary_total=Decimal(row["mean_monetary_total"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            ))

    return SegmentOverview(
        model_version=model_version,
        k_clusters=int(rows[0]["k_clusters"]),
        silhouette_score=rows[0]["silhouette_score"],
        customers=total_customers,
        sales_amount=total_sales,
        segments=result,
    )


def customer_segment_customers(run, *, model_version, limit=50, per_segment_limit=25):
    """Round-robin selection by within-label rank, then grouped display.

    Small groups release slots to remaining groups up to their per-group cap.
    If groups exceed slots, existing priority then label decides representation.
    """
    rows = (CustomerSegment.objects
            .filter(run=run, model_version=model_version)
            .annotate(
                segment_priority=Case(
                    When(segment_label="high_value", then=Value(0)),
                    When(segment_label="core", then=Value(1)),
                    When(segment_label="at_risk", then=Value(2)),
                    default=Value(9),
                    output_field=IntegerField(),
                ),
                segment_rank=Window(
                    expression=RowNumber(),
                    partition_by=[F("segment_label")],
                    order_by=[F("monetary_total").desc(), F("customer_id").asc()],
                ),
            )
            .filter(segment_rank__lte=per_segment_limit)
            .order_by("segment_rank", "segment_priority", "segment_label")[:limit])
    rows = sorted(rows, key=lambda row: (
        row.segment_priority, row.segment_label, -row.monetary_total, row.customer_id))
    return [SegmentCustomer(
        customer_id=row.customer_id,
        customer_reference=f"CUS-{row.customer_id}",
        segment_label=row.segment_label,
        recency_days=row.recency_days,
        frequency_orders=row.frequency_orders,
        monetary_total=row.monetary_total,
    ) for row in rows]


def _fetch_one(sql, params):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def _fetch_all(sql, params):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()
