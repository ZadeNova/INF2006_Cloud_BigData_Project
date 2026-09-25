"""Actual standalone SQL and producer output against the Django import contract."""
import importlib.util
import json
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import connection

from accounts.models import CustomerProfile
from analytics_helpers import at, make_inventory, make_products, make_run
from orders.models import Order
from reporting.models import CustomerSegment

spec = importlib.util.spec_from_file_location(
    "segment_customers", Path(__file__).resolve().parents[1] / "segment_customers.py")
segment_customers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(segment_customers)


@pytest.mark.django_db
def test_rfm_sql_eligibility_and_export_import_agree(tmp_path, monkeypatch):
    monkeypatch.setenv("ML_SOURCE_ID", "11111111-1111-1111-1111-111111111111")
    run = make_run(make_inventory(make_products()), [])
    users = {name: get_user_model().objects.create_user(username=name) for name in (
        "local", "imported", "repeat", "staff", "superuser", "operator",
        "foreign", "cancelled", "refunded", "cutoff", "future", "no-orders")}
    users["staff"].is_staff = True
    users["staff"].save()
    users["superuser"].is_superuser = True
    users["superuser"].save()
    users["operator"].groups.add(Group.objects.create(name="store_operator"))
    users["local"].groups.add(Group.objects.create(name="unrelated-group"))
    CustomerProfile.objects.create(user=users["imported"], namespace=run.inventory.namespace,
                                   external_id="imported", source_signup_at=at(2024, 1, 1))
    for name, user in reversed(list(users.items())):
        if name == "no-orders":
            continue
        Order.objects.create(
            owner=user, external_id=name, namespace="foreign" if name == "foreign" else run.inventory.namespace,
            total="10.00", status=name if name in {"cancelled", "refunded"} else "completed",
            placed_at=run.cutoff if name == "cutoff" else (
                at(2024, 3, 9) if name == "future" else at(2024, 3, 7)))
    Order.objects.create(owner=users["repeat"], external_id="repeat-extra", namespace=run.inventory.namespace,
                         total="35.25", status="completed", placed_at=at(2024, 3, 6))
    # Mixed ineligible orders for an eligible owner must not contribute to RFM.
    Order.objects.create(owner=users["repeat"], external_id="foreign-extra", namespace="foreign", total="999.00",
                         status="completed", placed_at=at(2024, 3, 7))
    Order.objects.create(owner=users["repeat"], external_id="cancelled-extra", namespace=run.inventory.namespace, total="999.00",
                         status="cancelled", placed_at=at(2024, 3, 7))
    Order.objects.create(owner=users["repeat"], external_id="cutoff-extra", namespace=run.inventory.namespace, total="999.00",
                         status="completed", placed_at=run.cutoff)
    metadata = segment_customers.fetch_run(connection, run.pk)
    frame = segment_customers.fetch_rfm(connection, metadata["namespace"], metadata["cutoff"])
    expected = sorted(users[name].pk for name in ("local", "imported", "repeat"))
    assert frame["customer_id"].tolist() == expected
    repeat = frame.set_index("customer_id").loc[users["repeat"].pk]
    assert repeat["frequency_orders"] == 2
    assert repeat["monetary_total"] == 45.25
    assert repeat["recency_days"] == 0
    assert not CustomerProfile.objects.filter(user=users["local"]).exists()
    fitted, k, score, stability_mean, stability_std = segment_customers.fit_segments(
        frame, min_k=2, max_k=2, stability_seeds=())
    training = segment_customers.training_config()
    version = segment_customers.model_version(training)
    data = segment_customers.build_output(fitted, run.pk, version, k, score,
                                         stability_mean, stability_std)
    segment_customers.complete_export(data, metadata, segment_customers.source_binding(connection), training)
    path = tmp_path / "export.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    call_command("load_customer_segments", input=path, run_id=str(run.pk), model_version=version)
    assert list(CustomerSegment.objects.filter(run=run).order_by("customer_id").values_list(
        "customer_id", flat=True)) == expected
