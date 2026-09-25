"""Dashboard read queries (PostgreSQL). Rows are inserted directly so every number is hand-checkable.

Run cutoff is 00:00 Asia/Singapore on 8 March 2024, so L is 7 March 2024 and the seven coverage dates are
1 to 7 March. Daily rows (date, product, units, sales amount) are listed in RUN_ROWS.
"""
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from analytics_helpers import (
    NS, OTHER_NS, SGT, add_order, at, load_segments, make_inventory, make_products, make_run)
from accounts.models import CustomerProfile
from catalogue.models import Product, ShoeModel
from reporting import queries, ranges, services
from reporting.models import AnalyticsRun
from reporting.ranges import Bucket, Span

pytestmark = pytest.mark.django_db
D = date
CATEGORIES = {"alpha": "Tools", "delta": "Tools", "beta": "Toys", "gamma": "Toys", "epsilon": "Toys"}
STOCK = {"alpha": (30, 7), "beta": (50, 7), "gamma": (50, 7), "delta": (49, 7), "epsilon": (50, 7)}


@pytest.fixture
def world():
    products = make_products(names=("alpha", "beta", "gamma", "delta", "epsilon"), categories=CATEGORIES)
    inventory = make_inventory(products, values=STOCK)
    rows = [
        (D(2024, 2, 28), products["alpha"], 5, "50.00"),
        (D(2024, 2, 29), products["alpha"], 2, "20.00"),        # the leap day
        (D(2024, 3, 1), products["alpha"], 7, "70.00"),
        (D(2024, 3, 2), products["beta"], 3, "60.00"),
        (D(2024, 3, 3), products["alpha"], 14, "140.00"),
        (D(2024, 3, 4), products["delta"], 49, "490.00"),
        (D(2024, 3, 5), products["epsilon"], 49, "490.00"),
        (D(2024, 3, 7), products["alpha"], 14, "140.00"),
    ]
    return products, inventory, make_run(inventory, rows)


WEEK = Span(D(2024, 3, 1), D(2024, 3, 7))


# --- run selection --------------------------------------------------------------------------

def test_no_completed_run_gives_none():
    assert queries.latest_completed_run(NS) is None


def test_latest_completed_run_ignores_failed_running_and_other_namespaces():
    products = make_products(names=("alpha",))
    inventory = make_inventory(products)
    old = make_run(inventory, [], finished_at=at(2024, 3, 8, 1))
    new = make_run(inventory, [], finished_at=at(2024, 3, 8, 2))
    make_run(inventory, [], finished_at=at(2024, 3, 8, 9), status=AnalyticsRun.Status.FAILED)
    make_run(inventory, [], status=AnalyticsRun.Status.RUNNING)
    other = make_inventory(make_products(OTHER_NS, names=("alpha",)), namespace=OTHER_NS, version="o-1")
    make_run(other, [], finished_at=at(2024, 3, 8, 12))
    assert queries.latest_completed_run(NS) == new != old


def test_history_start_is_the_earliest_row_or_none(world):
    _, inventory, run = world
    assert queries.history_start(run) == D(2024, 2, 28)
    assert queries.history_start(make_run(inventory, [])) is None


# --- summary --------------------------------------------------------------------------------

def test_sales_summary_for_a_span(world):
    _, _, run = world
    # 35 + 3 + 49 + 49 units; 350 + 60 + 490 + 490
    assert queries.sales_summary(run, WEEK) == (136, Decimal("1390.00"))


def test_sales_summary_includes_the_leap_day(world):
    _, _, run = world
    assert queries.sales_summary(run, Span(D(2024, 2, 28), D(2024, 3, 7))) == (143, Decimal("1460.00"))
    assert queries.sales_summary(run, Span(D(2024, 2, 29), D(2024, 2, 29))) == (2, Decimal("20.00"))


def test_sales_summary_of_an_empty_span_is_zero(world):
    _, _, run = world
    assert queries.sales_summary(run, Span(D(2024, 1, 1), D(2024, 1, 7))) == (0, Decimal("0"))


def test_summary_never_sums_across_runs(world):
    products, inventory, run = world
    make_run(inventory, [(D(2024, 3, 1), products["alpha"], 1000, "10000.00")])
    assert queries.sales_summary(run, WEEK) == (136, Decimal("1390.00"))


# --- bucketed series ------------------------------------------------------------------------

def test_daily_buckets_include_the_leap_day(world):
    _, _, run = world
    series = queries.bucket_sales(run, ranges.buckets(Span(D(2024, 2, 28), D(2024, 3, 2)), "daily"))
    assert [(item.start, item.units, item.sales_amount) for item in series] == [
        (D(2024, 2, 28), 5, Decimal("50.00")), (D(2024, 2, 29), 2, Decimal("20.00")),
        (D(2024, 3, 1), 7, Decimal("70.00")), (D(2024, 3, 2), 3, Decimal("60.00"))]


def test_dates_without_sales_are_zero_filled(world):
    _, _, run = world
    series = queries.bucket_sales(run, ranges.buckets(Span(D(2024, 3, 4), D(2024, 3, 6)), "daily"))
    assert [(item.units, item.sales_amount) for item in series] == [
        (49, Decimal("490.00")), (49, Decimal("490.00")), (0, Decimal("0"))]


def test_weekly_buckets_clip_to_the_span(world):
    _, _, run = world
    series = queries.bucket_sales(run, ranges.buckets(WEEK, "weekly"))
    assert series == [
        queries.BucketSales(D(2024, 3, 1), D(2024, 3, 3), 24, Decimal("270.00")),     # Fri to Sun
        queries.BucketSales(D(2024, 3, 4), D(2024, 3, 7), 112, Decimal("1120.00")),   # Mon to Thu
    ]
    assert sum(item.units for item in series) == queries.sales_summary(run, WEEK).units


def test_comparison_series_lines_up_bucket_by_bucket(world):
    _, _, run = world
    selected = ranges.buckets(WEEK, "daily")
    previous = queries.bucket_sales(run, ranges.shift_buckets(selected, WEEK.length))
    # 23 to 29 February: only the 28th (5 units) and the leap day (2 units) have sales
    assert [item.units for item in previous] == [0, 0, 0, 0, 0, 5, 2]
    assert previous[0].start == D(2024, 2, 23) and previous[-1].end == D(2024, 2, 29)


def test_no_buckets_means_no_query(world, django_assert_num_queries):
    _, _, run = world
    with django_assert_num_queries(0):
        assert queries.bucket_sales(run, []) == []


# --- category and top sellers ---------------------------------------------------------------

def test_category_sales_are_ordered_by_sales_amount(world):
    _, _, run = world
    assert queries.category_sales(run, WEEK) == [
        queries.CategorySales("Tools", 84, Decimal("840.00")),     # alpha 35 + delta 49
        queries.CategorySales("Toys", 52, Decimal("550.00")),      # beta 3 + epsilon 49
    ]


def test_top_sellers_rank_by_units_and_break_ties_on_product_id(world):
    products, _, run = world
    assert products["delta"].pk < products["epsilon"].pk
    sellers = queries.top_sellers(run, WEEK)
    assert [(item.rank, item.external_id, item.units) for item in sellers] == [
        (1, "delta", 49), (2, "epsilon", 49), (3, "alpha", 35), (4, "beta", 3)]     # gamma sold nothing
    assert sellers[0] == queries.TopSeller(1, products["delta"].pk, "delta", "Delta", "Tools", 49, Decimal("490.00"))


def test_top_sellers_group_every_size_of_a_shoe_and_size_sales_split_them(world):
    products, _, _ = world
    model = ShoeModel.objects.create(namespace=NS, external_id="S1", name="Runner", category="Running")
    small, large = (Product.objects.create(namespace=NS, external_id=f"S1-{size}", name="Runner", category="Running",
                                           price="10.00", cost="4.00", stock=5, lead_time_days=7, shoe_model=model,
                                           size=size) for size in ("8.0", "9.5"))
    # 30 + 25 units across two sizes outrank delta's 49 as one shoe; alpha and the others have no size.
    inventory = make_inventory({**products, "small": small, "large": large}, version="inv-sizes")
    run = make_run(inventory, [(D(2024, 3, 6), small, 30, "300.00"), (D(2024, 3, 7), large, 25, "250.00"),
                               (D(2024, 3, 4), products["delta"], 49, "490.00")])
    sellers = queries.top_sellers(run, WEEK)
    assert sellers[0] == queries.TopSeller(1, small.pk, "S1", "Runner", "Running", 55, Decimal("550.00"))
    assert [item.external_id for item in sellers] == ["S1", "delta"]
    assert queries.size_sales(run, WEEK) == [queries.SizeSales(Decimal("8.0"), 30, Decimal("300.00")),
                                             queries.SizeSales(Decimal("9.5"), 25, Decimal("250.00"))]
    assert [row.label for row in queries.size_sales(run, WEEK)] == ["US 8", "US 9.5"]


def test_top_sellers_limit(world):
    _, _, run = world
    assert [item.external_id for item in queries.top_sellers(run, WEEK, limit=2)] == ["delta", "epsilon"]


# --- coverage and flags ---------------------------------------------------------------------

def test_coverage_of_every_product_sorted_by_urgency(world):
    products, _, run = world
    rows = {row.external_id: row for row in queries.coverage(run)}
    # the documented example: 35 units in seven dates is 5 a day; stock 30 covers 6 days; lead time 7 flags it
    assert rows["alpha"] == queries.CoverageRow(
        products["alpha"].pk, "alpha", "Alpha", "Tools", None, 30, 7, 35, Decimal("5.00"), Decimal("6.00"), "flagged")
    # exactly at the threshold: 49 units is 7 a day, stock 49 covers exactly 7 days, lead time 7 flags it
    assert (rows["delta"].coverage_days, rows["delta"].status) == (Decimal("7.00"), "flagged")
    # one unit more stock and it is no longer flagged: 50 / 7 = 7.14 days
    assert (rows["epsilon"].coverage_days, rows["epsilon"].status) == (Decimal("7.14"), "ok")
    assert (rows["beta"].units_7d, rows["beta"].avg_daily_units, rows["beta"].coverage_days, rows["beta"].status) == (
        3, Decimal("0.43"), Decimal("116.67"), "ok")
    # no sales in the seven dates: coverage is unavailable, not infinite, and never flagged
    assert (rows["gamma"].units_7d, rows["gamma"].coverage_days, rows["gamma"].status) == (0, None, "unavailable")
    assert [row.external_id for row in queries.coverage(run)] == ["alpha", "delta", "epsilon", "beta", "gamma"]


def test_coverage_ignores_sales_before_the_seven_dates(world):
    _, _, run = world
    # alpha also sold 5 units on 28 February and 2 on 29 February: neither counts
    assert {row.external_id: row.units_7d for row in queries.coverage(run)}["alpha"] == 35


def test_coverage_uses_the_snapshot_not_live_stock(world):
    products, _, run = world
    before = queries.coverage(run)
    Product.objects.filter(pk=products["alpha"].pk).update(stock=0, lead_time_days=1)
    assert queries.coverage(run) == before


def test_seven_dates_across_the_leap_day():
    # cutoff 2 March 2024: L is 1 March and the seven dates are 24 February to 1 March, spanning 29 February
    products = make_products(names=("alpha",))
    cutoff = datetime(2024, 3, 2, tzinfo=SGT)
    inventory = make_inventory(products, cutoff=cutoff, version="leap", values={"alpha": (30, 7)})
    run = make_run(inventory, [
        (D(2024, 2, 23), products["alpha"], 100, "1000.00"),    # just outside
        (D(2024, 2, 24), products["alpha"], 7, "70.00"),
        (D(2024, 2, 29), products["alpha"], 7, "70.00"),
        (D(2024, 3, 1), products["alpha"], 7, "70.00"),
    ])
    (row,) = queries.coverage(run)
    assert (row.units_7d, row.avg_daily_units, row.coverage_days, row.status) == (21, Decimal("3.00"), Decimal("10.00"), "ok")


@pytest.mark.parametrize("first_date, expected", [
    (D(2024, 3, 1), "ok"),                       # history from 1 March: exactly seven complete dates
    (D(2024, 3, 2), "insufficient_history"),     # only six
])
def test_seven_complete_dates_of_history_are_required(first_date, expected):
    products = make_products(names=("alpha",))
    inventory = make_inventory(products, values={"alpha": (30, 7)})
    run = make_run(inventory, [(first_date, products["alpha"], 7, "70.00")])
    (row,) = queries.coverage(run)
    assert row.status == expected
    if expected == "insufficient_history":
        assert row.coverage_days is None and row.units_7d == 7      # the units are still reported; no number, no flag


@pytest.mark.parametrize("stock, lead, expected", [
    (400_000_000, 7, "ok"),                       # stock * 7 would overflow a PostgreSQL integer (AQRY-001)
    (2_147_483_647, 2_147_483_647, "flagged"),    # largest valid stock and lead time; exactly at the threshold
])
def test_very_large_valid_stock_does_not_overflow_the_flag_arithmetic(stock, lead, expected):
    products = make_products(names=("alpha",))
    inventory = make_inventory(products, values={"alpha": (stock, lead)})
    run = make_run(inventory, [(D(2024, 3, 1), products["alpha"], 7, "70.00")])     # 1 unit a day
    (row,) = queries.coverage(run)
    assert row.coverage_days == Decimal(stock).quantize(Decimal("0.01"))
    assert row.status == expected


def test_a_run_with_no_sales_at_all_has_insufficient_history():
    products = make_products(names=("alpha", "beta"))
    run = make_run(make_inventory(products), [])
    assert {row.status for row in queries.coverage(run)} == {"insufficient_history"}


def test_coverage_lists_every_product_in_the_inventory_even_without_sales(world):
    _, _, run = world
    assert len(queries.coverage(run)) == 5


# --- query budget and integration -----------------------------------------------------------

def test_queries_use_a_fixed_number_of_statements(world, django_assert_num_queries):
    _, _, run = world
    with django_assert_num_queries(2):        # history start, then one statement for every product
        queries.coverage(run)
    with django_assert_num_queries(1):
        queries.top_sellers(run, WEEK)
    with django_assert_num_queries(1):
        queries.category_sales(run, WEEK)
    with django_assert_num_queries(1):
        queries.bucket_sales(run, ranges.buckets(WEEK, "daily"))


def test_queries_read_what_refresh_analytics_published():
    owner = get_user_model().objects.create_user(username="query-user")
    products = make_products(names=("alpha", "beta"))
    make_inventory(products)
    add_order(owner, "o1", [(products["alpha"], 2, "10.00")], at(2024, 3, 5))
    add_order(owner, "o2", [(products["beta"], 3, "5.00")], at(2024, 3, 6))
    add_order(owner, "o3", [(products["beta"], 9, "5.00")], at(2024, 3, 6), status="cancelled")
    services.refresh_analytics(namespace=NS, as_of=D(2024, 3, 8))
    run = queries.latest_completed_run(NS)
    assert queries.sales_summary(run, Span(D(2024, 3, 5), D(2024, 3, 7))) == (5, Decimal("35.00"))
    assert [(item.external_id, item.units) for item in queries.top_sellers(run, WEEK)] == [("beta", 3), ("alpha", 2)]


def test_customer_segment_overview_returns_none_when_unloaded(world):
    _, _, run = world
    assert queries.customer_segment_overview(run) is None


def test_customer_segment_overview_groups_rows_and_sales_share(world):
    _, _, run = world
    owner = get_user_model().objects.create_user(username="segment-owner")
    second = get_user_model().objects.create_user(username="segment-owner-2")
    load_segments(run, [
        (owner, 0, "high_value", 2, 8, "900.00"),
        (second, 1, "at_risk", 35, 1, "100.00"),
    ], silhouette="0.6000")

    overview = queries.customer_segment_overview(run)
    assert overview.model_version == "rfm-kmeans-v1"
    assert overview.k_clusters == 3
    assert overview.silhouette_score == Decimal("0.6000")
    assert overview.customers == 2
    assert overview.sales_amount == Decimal("1000.00")
    assert [(item.segment_label, item.customers, item.sales_share_percent)
            for item in overview.segments] == [("high_value", 1, Decimal("90.0")), ("at_risk", 1, Decimal("10.0"))]


def test_customer_segment_customers_caps_per_segment_and_prioritises_high_value(world):
    _, _, run = world
    users = [get_user_model().objects.create_user(username=f"segment-user-{index}") for index in range(6)]
    load_segments(run, [
        (users[0], 0, "core", 10, 2, "200.00"),
        (users[1], 0, "core", 9, 3, "190.00"),
        (users[2], 0, "core", 8, 4, "180.00"),
        (users[3], 1, "high_value", 3, 7, "500.00"),
        (users[4], 1, "high_value", 4, 6, "450.00"),
        (users[5], 2, "at_risk", 30, 1, "50.00"),
    ])

    rows = queries.customer_segment_customers(run, model_version="rfm-kmeans-v1", limit=5, per_segment_limit=2)
    assert [(item.segment_label, item.monetary_total) for item in rows] == [
        ("high_value", Decimal("500.00")),
        ("high_value", Decimal("450.00")),
        ("core", Decimal("200.00")),
        ("core", Decimal("190.00")),
        ("at_risk", Decimal("50.00")),
    ]


@pytest.mark.parametrize("sizes,limit,cap,expected", [
    ([30, 30, 30], 50, 25, [17, 17, 16]),
    ([1, 30, 30], 10, 25, [1, 5, 4]),
    ([30, 30, 30], 80, 25, [25, 25, 25]),
    ([2, 2, 2, 2, 2], 4, 25, [1, 1, 1, 1, 0]),
    ([2, 2, 2], 0, 25, [0, 0, 0]),
])
def test_segment_sample_balances_bounded_capacity_deterministically(world, sizes, limit, cap, expected,
                                                                   django_assert_num_queries):
    _, _, run = world
    labels = ["high_value", "core", "at_risk", "alpha", "zeta"]
    assignments = []
    expected_ids = []
    for group, size in enumerate(sizes):
        users = get_user_model().objects.bulk_create([
            get_user_model()(username=f"sample-{group}-{index}") for index in range(size)])
        # Equal monetary values exercise the stable customer-ID tie break.
        assignments.extend((user, group, labels[group], 1, 1, "10.00") for user in reversed(users))
        expected_ids.extend(user.pk for user in users[:expected[group]])
    load_segments(run, assignments, k_clusters=max(3, len(sizes)))
    with django_assert_num_queries(1 if limit else 0):
        rows = queries.customer_segment_customers(run, model_version="rfm-kmeans-v1",
                                                  limit=limit, per_segment_limit=cap)
    counts = Counter(row.segment_label for row in rows)
    assert [counts[label] for label in labels[:len(sizes)]] == expected
    assert [row.customer_id for row in rows] == expected_ids
    assert queries.customer_segment_customers(run, model_version="rfm-kmeans-v1",
                                              limit=limit, per_segment_limit=cap) == rows


def test_segment_references_are_stable_internal_ids_without_customer_identity_fields(world,
                                                                                     django_assert_num_queries):
    _, inventory, run = world
    users = [get_user_model().objects.create_user(username=f"private-login-{index}",
             email=f"private-{index}@example.test", first_name="PrivateFirst", last_name="PrivateLast")
             for index in range(2)]
    CustomerProfile.objects.create(user=users[0], namespace=NS, external_id="source-private@example.test",
                                   source_signup_at=at(2024, 1, 1), channel="web", country="SG")
    assignments = [(user, index, label, 2, 1, "10.00")
                   for index, (user, label) in enumerate(zip(users, ["high_value", "core"]))]
    load_segments(run, assignments)
    load_segments(run, [(users[0], 0, "wrong_model", 2, 1, "999.00")], model_version="other")
    other_run = make_run(inventory, [])
    load_segments(other_run, [(users[0], 0, "wrong_run", 2, 1, "999.00")])
    with django_assert_num_queries(1):
        rows = queries.customer_segment_customers(run, model_version="rfm-kmeans-v1")
    assert [row.customer_reference for row in rows] == [f"CUS-{user.pk}" for user in users]
    assert set(rows[0]._fields) == {"customer_id", "customer_reference", "segment_label",
                                   "recency_days", "frequency_orders", "monetary_total"}
    users[0].username = "renamed-private-login"
    users[0].save(update_fields=["username"])
    assert queries.customer_segment_customers(run, model_version="rfm-kmeans-v1") == rows
