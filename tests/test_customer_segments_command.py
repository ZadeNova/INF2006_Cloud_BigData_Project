import json
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from analytics_helpers import add_order, at, make_inventory, make_products, make_run
from reporting.models import CustomerSegment

pytestmark = pytest.mark.django_db


def payload(run_id, model_version, rows):
    return {"run_id": str(run_id), "model_version": model_version, "rows": rows,
            "k_clusters": rows[0]["k_clusters"], "silhouette_score": rows[0]["silhouette_score"]}


@pytest.fixture
def snapshot(tmp_path):
    products = make_products()
    run = make_run(make_inventory(products), [])
    user = get_user_model().objects.create_user(username="eligible")
    add_order(user, "eligible-order", [(products["alpha"], 1, "10.00")], at(2024, 3, 7))
    row = {"customer_id": user.pk, "cluster_id": 0, "segment_label": "core",
           "recency_days": 1, "frequency_orders": 1, "monetary_total": "10.00",
           "k_clusters": 2, "silhouette_score": None}
    data = payload(run.pk, "test-model", [row])
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
    load(model_version="test-model")
    assert CustomerSegment.objects.filter(run=run).count() == 1
    data["model_version"] = "other-model"
    load()
    other = CustomerSegment.objects.get(run=run, model_version="other-model")
    data["model_version"] = "test-model"
    data["rows"][0].update(cluster_id=1, monetary_total="70.00")
    data["silhouette_score"] = data["rows"][0]["silhouette_score"] = "-0.25"
    load()
    assert CustomerSegment.objects.filter(run=run).count() == 2
    replacement = CustomerSegment.objects.get(run=run, model_version="test-model")
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
