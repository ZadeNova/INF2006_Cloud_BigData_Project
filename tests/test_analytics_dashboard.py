"""Backend contract before Luna supplies templates: inspect unrendered TemplateResponses.

Access failures use the real HTTP client. Successful HTML, escaping and json_script
checks belong to frontend integration; no placeholder production templates are used.
"""
from datetime import date
from decimal import Decimal
from importlib import import_module
import json
import re
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.migrations import AlterModelOptions
from django.urls import resolve, reverse

from analytics_helpers import NS, OTHER_NS, SGT, add_order, at, load_segments, make_inventory, make_products, make_run
from accounts.models import CustomerProfile
from catalogue.models import Product
from reporting import queries, services
from reporting.models import AnalyticsRun
from reporting.ranges import Span

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def namespace(settings):
    settings.DEMO_NAMESPACE = NS


@pytest.fixture
def operator():
    user = get_user_model().objects.create_user(username="operator")
    user.user_permissions.add(Permission.objects.get(content_type__app_label="reporting", codename="view_analytics"))
    return user


@pytest.fixture
def dashboard(rf, operator):
    def request(params=None, htmx=False):
        req = rf.get(reverse("reporting:dashboard"), params or {}, headers={"HX-Request": "true"} if htmx else {})
        req.user = operator
        return resolve(req.path).func(req)
    return request


@pytest.fixture
def world(operator):
    products = make_products()
    cutoff = at(2024, 5, 8, 0)
    inventory = make_inventory(products, cutoff=cutoff, values={"alpha": (7, 7)})
    # History supports even the shifted weekly YTD comparison; engine arithmetic
    # itself is covered in test_analytics_queries/ranges/refresh.
    add_order(operator, "history", [(products["alpha"], 1, "10.00")], at(2023, 8, 1))
    add_order(operator, "previous", [(products["alpha"], 2, "10.00")], at(2024, 4, 30))
    add_order(operator, "selected", [(products["alpha"], 7, "10.00")], at(2024, 5, 7))
    run = services.refresh_analytics(namespace=NS, as_of=cutoff.date(), inventory_version=inventory.version).run
    return products, inventory, run


def test_permission_migration_and_seed_are_idempotent(monkeypatch):
    migration = import_module("reporting.migrations.0004_analyticsrun_permissions").Migration
    assert len(migration.operations) == 1
    assert isinstance(migration.operations[0], AlterModelOptions)
    assert AnalyticsRun._meta.permissions == [("view_analytics", "Can view sales and inventory analytics")]
    monkeypatch.setenv("DEMO_OPERATOR_PASSWORD", "test-only-password")
    call_command("seed_demo", no_products=True)
    call_command("seed_demo", no_products=True)
    group = Group.objects.get(name="store_operator")
    assert set(group.permissions.values_list("content_type__app_label", "codename")) == {
        ("catalogue", "toggle_product_active"), ("reporting", "view_analytics")}
    assert get_user_model().objects.get(username="demo-operator").has_perm("reporting.view_analytics")


def test_seed_explains_missing_analytics_permission(monkeypatch):
    monkeypatch.setenv("DEMO_OPERATOR_PASSWORD", "test-only-password")
    Permission.objects.filter(content_type__app_label="reporting", codename="view_analytics").delete()
    with pytest.raises(CommandError, match=r"reporting.view_analytics.*migrate"):
        call_command("seed_demo", no_products=True)


def test_anonymous_and_expired_htmx_login(client, operator):
    url = reverse("reporting:dashboard")
    assert url == "/analytics/"
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == reverse("accounts:login") + "?next=/analytics/"
    assert "no-store" in response["Cache-Control"]
    client.force_login(operator)
    client.logout()
    response = client.get(url, headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert response["HX-Redirect"] == reverse("accounts:login")
    assert "no-store" in response["Cache-Control"]


@pytest.mark.parametrize("htmx", [False, True])
def test_customer_is_forbidden_even_with_htmx(client, htmx):
    client.force_login(get_user_model().objects.create_user(username="customer"))
    response = client.get(reverse("reporting:dashboard"), headers={"HX-Request": "true"} if htmx else {})
    assert response.status_code == 403
    assert "HX-Redirect" not in response
    assert "no-store" in response["Cache-Control"]


def test_get_only(client, operator):
    client.force_login(operator)
    response = client.post(reverse("reporting:dashboard"))
    assert response.status_code == 405
    assert response["Allow"] == "GET"
    assert "no-store" in response["Cache-Control"]


def test_empty_state_and_full_fragment_selection(dashboard, operator, django_assert_num_queries):
    assert operator.has_perm("reporting.view_analytics")  # exclude framework auth queries
    for htmx, template in [(False, "reporting/dashboard.html"), (True, "reporting/_panel.html")]:
        with django_assert_num_queries(1):
            response = dashboard(htmx=htmx)
        assert response.status_code == 200
        assert response.template_name == template
        assert not response.is_rendered
        assert response.context_data["run"] is None
        assert response.context_data["empty_message"]
        assert response.context_data["range_key"] == "30d"
        assert response.context_data["range_message"] == ""
        assert "no-store" in response["Cache-Control"]
        assert "no-cache" in response["Cache-Control"]
        assert "Expires" in response


def test_rendered_empty_state_is_successful(client, operator):
    client.force_login(operator)
    response = client.get(reverse("reporting:dashboard"))
    body = response.content.decode()
    assert response.status_code == 200
    assert "No completed analytics run yet" in body
    assert "Run the analytics refresh after a sealed inventory snapshot is available." in body
    assert 'data-chart="trend"' not in body


def test_range_is_derived_from_run_cutoff(world, dashboard):
    # Each key's arithmetic is tested in test_analytics_ranges.py; here the view must end the span at L.
    context = dashboard({"range": "90d"}).context_data
    assert context["span"] == Span(date(2024, 2, 8), date(2024, 5, 7))
    assert context["latest_complete_date"] == date(2024, 5, 7)


def test_invalid_parameters_and_trusted_namespace(world, dashboard):
    other_inventory = make_inventory(make_products(OTHER_NS), namespace=OTHER_NS)
    other_run = make_run(other_inventory, [])
    with patch("reporting.views.queries.latest_completed_run", wraps=queries.latest_completed_run) as latest:
        context = dashboard({"range": "bad", "compare": "true", "namespace": OTHER_NS,
                             "run": str(other_run.pk), "run_id": str(other_run.pk), "cutoff": "2099-01-01",
                             "from": "2099-01-01", "to": "2099-01-02"}).context_data
    latest.assert_called_once_with(NS)
    assert context["run"].pk == world[2].pk
    assert context["range_key"] == "30d" and context["range_message"]
    assert context["span"] == Span(date(2024, 4, 8), date(2024, 5, 7))
    assert context["compare"] is False
    assert context["comparison_summary"] is None


def test_sales_context_and_shifted_weekly_comparison(world, dashboard):
    context = dashboard({"range": "7d", "compare": "1"}).context_data
    assert context["summary"] == queries.Summary(7, Decimal("70.00"))
    assert context["comparison_summary"] == queries.Summary(2, Decimal("20.00"))
    assert context["categories"][0].sales_amount == Decimal("70.00")
    assert context["top_sellers"][0].product_id == world[0]["alpha"].pk
    weekly = dashboard({"range": "ytd", "compare": "1"}).context_data
    assert weekly["granularity"] == "weekly" and weekly["comparison_available"]
    assert len(weekly["series"]) == len(weekly["comparison_series"])
    for selected, previous in zip(weekly["series"], weekly["comparison_series"], strict=True):
        assert (selected.start - previous.start).days == weekly["span"].length
        assert (selected.end - previous.end).days == weekly["span"].length


def test_zero_sales_comparison_is_available_for_na_display(world, dashboard, client, operator):
    context = dashboard({"range": "30d", "compare": "1"}).context_data
    assert context["comparison_available"]
    assert context["comparison_summary"] == queries.Summary(0, Decimal("0"))
    client.force_login(operator)
    body = client.get(reverse("reporting:dashboard"), {"range": "30d", "compare": "1"}).content.decode()
    assert "n/a" in body


def test_unavailable_comparison_and_partial_history(dashboard, operator):
    products = make_products()
    inventory = make_inventory(products)
    add_order(operator, "short", [(products["alpha"], 7, "10.00")], at(2024, 3, 7))
    services.refresh_analytics(namespace=NS, as_of=inventory.cutoff.astimezone(SGT).date(), inventory_version=inventory.version)
    context = dashboard({"compare": "1"}).context_data
    assert not context["comparison_available"]
    assert context["comparison_summary"] is None and context["comparison_series"] == []
    assert context["coverage_counts"]["insufficient_history"] == 3
    assert all(row.avg_daily_units is None and row.coverage_days is None
               and row.status == "insufficient_history" for row in context["coverage"])


def test_coverage_is_fixed_and_ignores_live_stock(world, dashboard):
    before = dashboard({"range": "7d"}).context_data
    Product.objects.filter(namespace=NS).update(stock=10000, lead_time_days=0)
    after = dashboard({"range": "ytd", "compare": "1"}).context_data
    assert before["coverage"] == after["coverage"]
    assert before["coverage_counts"] == after["coverage_counts"]
    assert after["coverage"][0].status == "flagged"
    assert after["coverage"][0].stock == 7


def test_query_count_stays_bounded_and_tables_are_capped(world, dashboard, operator, django_assert_num_queries):
    assert operator.has_perm("reporting.view_analytics")
    with django_assert_num_queries(14):
        small = dashboard({"range": "7d", "compare": "1"})
    assert small.context_data["comparison_available"]
    extra = make_products(names=tuple(f"extra-{i}" for i in range(30)))
    all_products = {**world[0], **extra}
    inventory = make_inventory(all_products, cutoff=world[1].cutoff, version="larger")
    for i, product in enumerate(extra.values()):
        add_order(operator, f"extra-{i}", [(product, 1, "10.00")], at(2024, 5, 7))
    services.refresh_analytics(namespace=NS, as_of=inventory.cutoff.astimezone(SGT).date(), inventory_version=inventory.version)
    with django_assert_num_queries(14):
        large = dashboard({"range": "7d", "compare": "1"})
    context = large.context_data
    assert len(context["coverage"]) == 25
    assert sum(context["coverage_counts"].values()) == 33
    assert len(context["top_sellers"]) == 10


def test_rendered_full_and_fragment_include_accessible_charts_and_preserve_controls(client, world, operator):
    client.force_login(operator)
    full = client.get(reverse("reporting:dashboard"), {"range": "7d", "compare": "1"})
    assert full.status_code == 200
    body = full.content.decode()
    assert "<html" in body and 'id="analytics-panel"' in body
    assert 'data-chart="trend"' in body and 'data-chart="categories"' in body
    assert 'id="analytics-trend-data"' in body and 'id="analytics-category-data"' in body
    assert 'hx-get="/analytics/?range=30d&amp;compare=1"' in body
    assert 'aria-current="page"' in body
    assert "View trend data table" in body and "View category data table" in body
    assert "Top ten sellers" in body and "Replenishment attention" in body
    trend_json = re.search(r'id="analytics-trend-data" type="application/json">(.*?)</script>', body, re.S)
    assert trend_json and json.loads(trend_json.group(1))["comparison"]

    fragment = client.get(reverse("reporting:dashboard"), {"range": "7d", "compare": "1"},
                          headers={"HX-Request": "true"})
    fragment_body = fragment.content.decode()
    assert fragment.status_code == 200
    assert 'id="analytics-panel"' in fragment_body and "<html" not in fragment_body
    assert 'hx-target="#analytics-panel"' in fragment_body


def test_invalid_range_is_visible_in_rendered_panel(client, world, operator):
    client.force_login(operator)
    body = client.get(reverse("reporting:dashboard"), {"range": "tomorrow"}).content.decode()
    assert "Range adjusted" in body
    assert "showing the last 30 complete dates" in body
    assert 'aria-current="page"' in body


def test_rendered_dashboard_escapes_product_names_and_shows_status_labels(client, world, operator):
    world[0]["alpha"].name = '<img src=x onerror="alert(1)">'
    world[0]["alpha"].save(update_fields=["name"])
    client.force_login(operator)
    response = client.get(reverse("reporting:dashboard"), {"range": "7d"})
    body = response.content.decode()
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in body
    assert '<img src=x onerror="alert(1)">' not in body
    assert "Replenishment attention" in body
    assert "Flagged" in body or "On track" in body or "No recent sales; coverage unavailable" in body


def test_rendered_insufficient_history_hides_coverage_metrics(client, operator):
    products = make_products()
    inventory = make_inventory(products)
    add_order(operator, "short-rendered", [(products["alpha"], 1, "10.00")], at(2024, 3, 7))
    services.refresh_analytics(namespace=NS, as_of=inventory.cutoff.astimezone(SGT).date(),
                               inventory_version=inventory.version)
    client.force_login(operator)
    body = client.get(reverse("reporting:dashboard"), {"compare": "1"}).content.decode()
    coverage = body.split('id="coverage-title"', 1)[1]
    assert "Insufficient history" in coverage
    assert "0.00 days" not in coverage
    assert "0.14" not in coverage
    assert "Previous-period category comparison is unavailable because there is insufficient history." in body
    assert "Previous-period sellers unavailable: insufficient history." in body


def test_operator_nav_is_permission_guarded(client, operator):
    client.force_login(operator)
    assert 'href="/analytics/"' in client.get(reverse("foundation-preview")).content.decode()
    customer = get_user_model().objects.create_user(username="ordinary")
    client.force_login(customer)
    assert 'href="/analytics/"' not in client.get(reverse("foundation-preview")).content.decode()


def test_pruned_selected_run_rebuilds_complete_context(world, dashboard):
    products, inventory, old_run = world
    replacement = make_run(inventory, [
        (date(2023, 8, 1), products["beta"], 1, "5.00"),
        (date(2024, 4, 30), products["beta"], 3, "15.00"),
        (date(2024, 5, 7), products["beta"], 11, "55.00"),
    ])
    expected = dashboard({"range": "7d", "compare": "1"}).context_data
    selections = iter([old_run, replacement])

    def select_then_prune(namespace):
        selected = next(selections)
        AnalyticsRun.objects.filter(pk=old_run.pk).delete()
        return selected

    with patch("reporting.views.queries.latest_completed_run", side_effect=select_then_prune) as select:
        context = dashboard({"range": "7d", "compare": "1"}).context_data
    assert select.call_count == 2
    assert context["run"].pk == replacement.pk
    assert context == expected


def test_category_comparison_aligns_prior_only_categories(dashboard):
    products = make_products()
    products["alpha"].category = "Selected"
    products["alpha"].save(update_fields=["category"])
    products["beta"].category = "Prior only"
    products["beta"].save(update_fields=["category"])
    inventory = make_inventory(products, cutoff=at(2024, 5, 8, 0))
    make_run(inventory, [
        (date(2024, 4, 24), products["beta"], 2, "20.00"),
        (date(2024, 5, 7), products["alpha"], 7, "70.00"),
    ])
    context = dashboard({"range": "7d", "compare": "1"}).context_data
    assert context["category_chart"] == {
        "labels": ["Selected", "Prior only"], "values": [70.0, 0.0], "units": [7, 0],
        "comparison": {"values": [0.0, 20.0], "units": [0, 2]},
    }
    assert [(row["selected"].units, row["comparison"].units) for row in context["category_rows"]] == [(7, 0), (0, 2)]
    assert context["comparison_top_sellers"][0].product_id == products["beta"].pk


def test_dashboard_shows_ml_segment_panel_when_assignments_exist(client, operator):
    products = make_products()
    inventory = make_inventory(products, cutoff=at(2024, 5, 8, 0))
    run = make_run(inventory, [(date(2024, 5, 7), products["alpha"], 7, "70.00")])
    second = get_user_model().objects.create_user(username="import-" + ("a" * 60))
    CustomerProfile.objects.create(
        user=second, namespace=NS, external_id="C000002", source_signup_at=at(2024, 1, 1), channel="web", country="SG")
    load_segments(run, [
        (operator, 0, "high_value", 2, 6, "450.00"),
        (second, 1, "at_risk", 48, 1, "40.00"),
    ])

    client.force_login(operator)
    body = client.get(reverse("reporting:dashboard"), {"range": "7d"}).content.decode()
    assert "Customer segments" in body
    assert "Segmented customers" in body
    assert "Top customers by segment (up to 25 each, max 50)" in body
    assert "Customer ref" in body and "Login username" in body
    assert "high_value" in body and "at_risk" in body
    assert "demo-operator" not in body
    assert "C000002" in body and "import-" in body and "…" in body
    assert "Silhouette 0.5123" in body


def test_rendered_comparison_includes_category_series_and_previous_sellers(client, operator):
    products = make_products()
    products["alpha"].category = "Selected"
    products["alpha"].save(update_fields=["category"])
    products["beta"].category = "Prior only"
    products["beta"].save(update_fields=["category"])
    inventory = make_inventory(products, cutoff=at(2024, 5, 8, 0))
    make_run(inventory, [
        (date(2024, 4, 24), products["beta"], 2, "20.00"),
        (date(2024, 5, 7), products["alpha"], 7, "70.00"),
    ])
    client.force_login(operator)
    body = client.get(reverse("reporting:dashboard"), {"range": "7d", "compare": "1"}).content.decode()

    category_json = re.search(r'id="analytics-category-data" type="application/json">(.*?)</script>', body, re.S)
    assert category_json
    assert json.loads(category_json.group(1))["comparison"] == {
        "values": [0.0, 20.0], "units": [0, 2]}
    assert "Selected sales value" in body and "Previous sales value" in body
    assert "Previous units" in body and "Prior only" in body
    assert "Previous period top sellers" in body and "Beta" in body
    assert body.count('scope="col"') >= 16 and body.count('scope="row"') >= 4
    assert body.count('tabindex="0"') >= 5


def test_repeated_pruning_returns_bounded_retry_response(world, dashboard):
    run = world[2]
    AnalyticsRun.objects.filter(pk=run.pk).delete()
    with patch("reporting.views.queries.latest_completed_run", return_value=run) as select:
        response = dashboard()
    assert select.call_count == 3
    assert response.status_code == 503
    assert "no-store" in response["Cache-Control"]
    assert b"Please retry" in response.content
