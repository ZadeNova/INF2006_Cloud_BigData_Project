import json
from decimal import Decimal
from datetime import datetime, timezone

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from analytics_helpers import add_order, at, make_inventory, make_products, make_run
from reporting.models import CustomerSegment
from reporting.segment_contract import (FORMAT, FEATURE_SCHEMA, batch_id, model_version,
                                       run_binding, source_binding)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def source_environment(monkeypatch):
    monkeypatch.setenv("ML_SOURCE_ID", "11111111-1111-1111-1111-111111111111")


def payload(run, rows, preprocessing="log_frequency"):
    from django.db import connection
    training = {
        "algorithm": "sklearn-kmeans", "feature_schema": FEATURE_SCHEMA,
        "preprocessing": preprocessing, "min_k": 2, "max_k": 4, "seed": 42,
        "stability_seeds": [42, 99, 123, 777], "n_init": "auto",
        "selection": "highest-valid-silhouette-smaller-k-tie", "silhouette_sample_limit": 5000,
        "provenance": {"python": "test-runtime", "dependencies": {name: "test-version" for name in
                        ("numpy", "pandas", "scikit-learn", "scipy", "psycopg", "joblib", "threadpoolctl")},
                       "code_sha256": {path: "0" * 64 for path in (
                           "analytics/segment_customers.py", "analytics/requirements.txt", "src/reporting/segment_contract.py")}},
    }
    data = {"run_id": str(run.pk), "model_version": model_version(training), "rows": rows,
            "k_clusters": rows[0]["k_clusters"], "silhouette_score": rows[0]["silhouette_score"],
            "format": FORMAT, "status": "completed", "training": training,
            "source": source_binding(connection), "generated_at": datetime.now(timezone.utc).isoformat(),
            "run": run_binding({"run_id": run.pk, "cutoff": run.cutoff, "namespace": run.inventory.namespace,
                                "inventory_version": run.inventory.version, "summary_version": run.summary_version})}
    data["batch_id"] = batch_id(data)
    return data


@pytest.fixture
def snapshot(tmp_path):
    products = make_products()
    run = make_run(make_inventory(products), [])
    user = get_user_model().objects.create_user(username="eligible")
    add_order(user, "eligible-order", [(products["alpha"], 1, "10.00")], at(2024, 3, 7))
    row = {"customer_id": user.pk, "cluster_id": 0, "segment_label": "core",
           "recency_days": 1, "frequency_orders": 1, "monetary_total": "10.00",
           "k_clusters": 2, "silhouette_score": None}
    data = payload(run, [row])
    path = tmp_path / "snapshot.json"
    def load(data=data, **kwargs):
        path.write_text(json.dumps(data), encoding="utf-8")
        call_command("load_customer_segments", run_id=str(run.pk), input=path, **kwargs)
    load()
    return run, user, products, data, load


@pytest.mark.parametrize("field,value", [
    ("customer_id", 2147483648),      # auth.User uses a PostgreSQL integer PK
    ("customer_id", True),             # bool is an int subclass, not a JSON integer ID
    ("cluster_id", 0.5),                # no fractional truncation
    ("recency_days", "1"),             # no numeric-string coercion
    ("recency_days", -1),
    ("frequency_orders", 2147483648),
    ("frequency_orders", 0),
    ("cluster_id", 2),                  # cluster must be below k
    ("segment_label", {}),              # no implicit string conversion
    ("segment_label", "x" * 41),
    ("segment_label", "\u0000"),
    ("segment_label", "\ud800"),
    ("monetary_total", "NaN"),
    ("monetary_total", "10000000000000000.00"),
    ("monetary_total", "1.001"),         # no silent decimal rounding
    ("silhouette_score", "1.0001"),
    ("k_clusters", 3),                  # coherent run metadata
    ("silhouette_score", "0.5"),
])
def test_invalid_assignment_preserves_published_snapshot(snapshot, field, value):
    run, _, _, data, load = snapshot
    before = list(CustomerSegment.objects.filter(run=run).values())
    data["rows"][0][field] = value
    with pytest.raises(CommandError, match="invalid or inconsistent"):
        load()
    assert list(CustomerSegment.objects.filter(run=run).values()) == before


@pytest.mark.parametrize("change", ["missing_run", "invalid_run", "missing_k", "bad_model", "duplicate", "empty_rows", "mismatched_run", "k_bound"])
def test_invalid_snapshot_identity_or_shape_is_rejected(snapshot, change):
    run, _, _, data, load = snapshot
    if change == "missing_run":
        del data["run_id"]
    elif change == "invalid_run":
        data["run_id"] = "private-value"
    elif change == "missing_k":
        del data["k_clusters"]
    elif change == "bad_model":
        data["model_version"] = "x" * 101
    elif change == "k_bound":
        data["k_clusters"] = 32768
    elif change == "empty_rows":
        data["rows"] = []
    elif change == "mismatched_run":
        from uuid import uuid4
        data["run_id"] = str(uuid4())
    else:
        data["rows"].append(data["rows"][0].copy())
    with pytest.raises(CommandError) as error:
        load()
    assert "private-value" not in str(error.value)
    assert CustomerSegment.objects.filter(run=run).count() == 1


def test_model_option_asserts_payload_identity(snapshot):
    _, _, _, _, load = snapshot
    with pytest.raises(CommandError, match="metadata"):
        load(model_version="different-model")


def test_average_order_value_recipe_loads_and_unknown_recipe_is_rejected(snapshot):
    run, _, _, data, load = snapshot
    aov = payload(run, data["rows"], preprocessing="log_rfm_aov")
    load(aov)
    assert set(CustomerSegment.objects.filter(run=run).values_list("model_version", flat=True)) >= {aov["model_version"]}
    with pytest.raises(CommandError, match="completed batch"):
        load(payload(run, data["rows"], preprocessing="made_up"))


@pytest.mark.parametrize("change", ["legacy", "source", "run", "version", "checksum"])
def test_batch_provenance_or_integrity_rejection_preserves_assignments(snapshot, change):
    run, _, _, data, load = snapshot
    before = list(CustomerSegment.objects.filter(run=run).values())
    if change == "legacy":
        del data["status"]
    elif change == "source":
        data["source"]["source_id"] = "22222222-2222-2222-2222-222222222222"
        data["batch_id"] = batch_id(data)  # Integrity alone cannot establish source association.
    elif change == "run":
        data["run"]["cutoff"] = "2024-03-09T00:00:00+00:00"
        data["batch_id"] = batch_id(data)
    elif change == "version":
        data["model_version"] = "arbitrary-label"
        data["batch_id"] = batch_id(data)
    else:
        data["rows"][0]["monetary_total"] = "11.00"
    with pytest.raises(CommandError, match="completed batch"):
        load()
    assert list(CustomerSegment.objects.filter(run=run).values()) == before


def test_source_configuration_is_required_at_import(snapshot, monkeypatch):
    run, _, _, _, load = snapshot
    monkeypatch.delenv("ML_SOURCE_ID")
    with pytest.raises(CommandError, match="completed batch"):
        load()
    assert CustomerSegment.objects.filter(run=run).count() == 1


def test_rejects_incomplete_customer_snapshot(snapshot):
    _, _, products, _, load = snapshot
    other = get_user_model().objects.create_user(username="omitted")
    add_order(other, "omitted-order", [(products["alpha"], 1, "10.00")], at(2024, 3, 6))
    with pytest.raises(CommandError, match="regenerate"):
        load()


@pytest.mark.parametrize("content", ['[]', '{"rows": [], "rows": []}', '{broken', b'\xff', '{"n":1e999999999999999999999999999999999999}'])
def test_malformed_input_is_sanitised(tmp_path, content):
    path = tmp_path / "input.json"
    path.write_bytes(content if isinstance(content, bytes) else content.encode())
    with pytest.raises(CommandError, match="valid JSON object"):
        call_command("load_customer_segments", run_id="bad", input=path)


def test_replay_replacement_and_versions_are_independent(snapshot):
    run, _, _, data, load = snapshot
    first_version = data["model_version"]
    load(model_version=first_version)
    assert CustomerSegment.objects.filter(run=run).count() == 1
    data["training"]["seed"] = 99
    data["model_version"] = model_version(data["training"])
    data["batch_id"] = batch_id(data)
    load()
    other = CustomerSegment.objects.get(run=run, model_version=data["model_version"])
    data["training"]["seed"] = 42
    data["model_version"] = first_version
    data["rows"][0].update(cluster_id=1, monetary_total="70.00")
    data["silhouette_score"] = data["rows"][0]["silhouette_score"] = "-0.25"
    data["batch_id"] = batch_id(data)
    load()
    assert CustomerSegment.objects.filter(run=run).count() == 2
    replacement = CustomerSegment.objects.get(run=run, model_version=first_version)
    assert (replacement.cluster_id, replacement.monetary_total, replacement.silhouette_score) == (
        1, Decimal("70.00"), Decimal("-0.25"))
    other.refresh_from_db()
    assert other.monetary_total == Decimal("10.00")


def test_cluster_labels_must_agree(snapshot):
    run, _, products, data, load = snapshot
    other = get_user_model().objects.create_user(username="second")
    add_order(other, "second", [(products["alpha"], 1, "10.00")], at(2024, 3, 7))
    data["rows"].append(dict(data["rows"][0], customer_id=other.pk, segment_label="different"))
    with pytest.raises(CommandError, match="consistent segment label"):
        load()
    assert CustomerSegment.objects.filter(run=run).count() == 1


def test_foreign_customer_rejected_without_replacing_snapshot(snapshot):
    run, user, _, data, load = snapshot
    other = get_user_model().objects.create_user(username="no-orders")
    data["rows"][0]["customer_id"] = other.pk
    with pytest.raises(CommandError, match="eligible customers"):
        load()
    assert CustomerSegment.objects.get(run=run).customer_id == user.pk


def test_unknown_run_is_sanitised(snapshot, tmp_path):
    from uuid import uuid4
    _, _, _, data, _ = snapshot
    data["run_id"] = str(uuid4())
    path = tmp_path / "unknown.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CommandError, match="run does not exist"):
        call_command("load_customer_segments", input=path, run_id=data["run_id"])


def test_database_failure_rolls_back_replacement_and_is_sanitised(snapshot, monkeypatch):
    from django.db import DatabaseError
    run, _, _, _, load = snapshot
    before = list(CustomerSegment.objects.filter(run=run).values())
    def fail(*args, **kwargs):
        raise DatabaseError("private database credentials and payload")
    monkeypatch.setattr(CustomerSegment.objects, "bulk_create", fail)
    with pytest.raises(CommandError, match="check database availability") as error:
        load()
    assert "private" not in str(error.value)
    assert list(CustomerSegment.objects.filter(run=run).values()) == before


def test_numeric_json_decimal_is_not_rounded_during_parsing(snapshot, tmp_path):
    run, _, _, data, _ = snapshot
    path = tmp_path / "precise.json"
    path.write_text(json.dumps(data).replace('"10.00"', '10.0000000000000001'), encoding="utf-8")
    with pytest.raises(CommandError, match="invalid or inconsistent"):
        call_command("load_customer_segments", run_id=str(run.pk), input=path)
    assert CustomerSegment.objects.get(run=run).monetary_total == Decimal("10.00")


@pytest.mark.django_db(transaction=True)
def test_concurrent_loaders_replace_one_complete_set(snapshot, tmp_path):
    import threading
    from django.db import connection
    from db_helpers import wait_until_blocked
    run, _, products, data, _ = snapshot
    other = get_user_model().objects.create_user(username="concurrent-second")
    add_order(other, "concurrent-second", [(products["alpha"], 1, "10.00")], at(2024, 3, 7))
    data["rows"].append(dict(data["rows"][0], customer_id=other.pk))
    paths = []
    for name, value in (("first", "20.00"), ("second", "30.00")):
        for row in data["rows"]:
            row["monetary_total"] = value
        data["batch_id"] = batch_id(data)
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(data), encoding="utf-8")
        paths.append(path)
    deleted, release = threading.Event(), threading.Event()
    errors = []
    def pause_after_delete(execute, sql, params, many, context):
        result = execute(sql, params, many, context)
        if sql.startswith('DELETE FROM "reporting_customersegment"'):
            deleted.set()
            assert release.wait(15), "test did not release first loader"
        return result
    def attempt(path, pause=False):
        try:
            if pause:
                with connection.execute_wrapper(pause_after_delete):
                    call_command("load_customer_segments", run_id=str(run.pk), input=path)
            else:
                call_command("load_customer_segments", run_id=str(run.pk), input=path)
        except Exception as error:
            errors.append(error)
        finally:
            connection.close()
    first = threading.Thread(target=attempt, args=(paths[0], True))
    second = threading.Thread(target=attempt, args=(paths[1],))
    first.start()
    try:
        assert deleted.wait(10)
        second.start()
        wait_until_blocked()
        # Uncommitted deletion is invisible to readers.
        assert CustomerSegment.objects.filter(run=run).count() == 1
    finally:
        release.set()
        first.join(15)
        if second.ident is not None:
            second.join(15)
    assert not first.is_alive() and not second.is_alive()
    assert not errors, errors
    assert list(CustomerSegment.objects.filter(run=run).values_list(
        "monetary_total", flat=True)) == [Decimal("30.00"), Decimal("30.00")]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("changed", ["status", "eligibility"])
def test_status_and_cohort_are_checked_after_acquiring_run_lock(snapshot, changed):
    import threading
    from django.db import connection, transaction
    from db_helpers import wait_until_blocked
    from reporting.models import AnalyticsRun
    run, user, _, _, load = snapshot
    errors = []
    def attempt():
        try:
            load()
        except Exception as error:
            errors.append(error)
        finally:
            connection.close()
    thread = threading.Thread(target=attempt)
    try:
        with transaction.atomic():
            AnalyticsRun.objects.select_for_update().get(pk=run.pk)
            thread.start()
            wait_until_blocked()
            if changed == "status":
                AnalyticsRun.objects.filter(pk=run.pk).update(status="failed")
            else:
                get_user_model().objects.filter(pk=user.pk).update(is_staff=True)
    finally:
        if thread.ident is not None:
            thread.join(15)
    assert not thread.is_alive()
    assert len(errors) == 1 and isinstance(errors[0], CommandError)
    assert ("not completed" if changed == "status" else "eligible customers") in str(errors[0])
    assert CustomerSegment.objects.get(run=run).customer_id == user.pk


@pytest.mark.django_db(transaction=True)
def test_dashboard_reads_one_assignment_set_during_replacement(snapshot, rf, settings, monkeypatch):
    import threading
    from django.contrib.auth.models import Permission
    from django.db import connection
    from db_helpers import wait_until_blocked
    from reporting import queries
    from reporting.views import AnalyticsDashboardView

    run, _, _, data, load = snapshot
    settings.DEMO_NAMESPACE = run.inventory.namespace
    operator = get_user_model().objects.create_user(username="reader")
    operator.user_permissions.add(Permission.objects.get(codename="view_analytics"))
    data["rows"][0]["monetary_total"] = "20.00"
    data["batch_id"] = batch_id(data)
    overview_read, release = threading.Event(), threading.Event()
    errors, contexts = [], []
    original = queries.customer_segment_overview

    def pause_after_overview(selected_run):
        result = original(selected_run)
        overview_read.set()
        assert release.wait(15), "test did not release dashboard"
        return result

    monkeypatch.setattr(queries, "customer_segment_overview", pause_after_overview)

    def read():
        try:
            request = rf.get("/analytics/")
            request.user = operator
            contexts.append(AnalyticsDashboardView.as_view()(request).context_data)
        except Exception as error:
            errors.append(error)
        finally:
            connection.close()

    def replace():
        try:
            load()
        except Exception as error:
            errors.append(error)
        finally:
            connection.close()

    reader = threading.Thread(target=read)
    writer = threading.Thread(target=replace)
    reader.start()
    try:
        assert overview_read.wait(10)
        writer.start()
        wait_until_blocked()
    finally:
        release.set()
        reader.join(15)
        if writer.ident is not None:
            writer.join(15)
    assert not reader.is_alive() and not writer.is_alive()
    assert not errors, errors
    assert contexts[0]["segment_overview"].sales_amount == Decimal("10.00")
    assert contexts[0]["segment_customers"][0].monetary_total == Decimal("10.00")
    assert CustomerSegment.objects.get(run=run).monetary_total == Decimal("20.00")
