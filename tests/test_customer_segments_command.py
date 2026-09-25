import json
from datetime import date
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from analytics_helpers import make_inventory, make_products, make_run
from reporting.models import CustomerSegment

pytestmark = pytest.mark.django_db


def payload(run_id, model_version, rows):
    return {"run_id": str(run_id), "model_version": model_version, "rows": rows}


def test_load_customer_segments_inserts_rows(tmp_path):
    products = make_products()
    run = make_run(make_inventory(products), [(date(2024, 3, 7), products["alpha"], 2, "20.00")])
    first = get_user_model().objects.create_user(username="seg-user-1")
    second = get_user_model().objects.create_user(username="seg-user-2")
    file = tmp_path / "segments.json"
    file.write_text(json.dumps(payload(run.pk, "rfm-kmeans-v1", [
        {"customer_id": first.pk, "cluster_id": 0, "segment_label": "high_value",
         "recency_days": 2, "frequency_orders": 6, "monetary_total": "450.00",
         "k_clusters": 3, "silhouette_score": "0.5123"},
        {"customer_id": second.pk, "cluster_id": 1, "segment_label": "at_risk",
         "recency_days": 40, "frequency_orders": 1, "monetary_total": "50.00",
         "k_clusters": 3, "silhouette_score": "0.5123"},
    ])), encoding="utf-8")

    out = StringIO()
    call_command("load_customer_segments", "--run-id", str(run.pk), "--input", str(file), stdout=out)
    assert "Loaded 2 customer segment rows" in out.getvalue()
    assert CustomerSegment.objects.filter(run=run, model_version="rfm-kmeans-v1").count() == 2


def test_load_customer_segments_replaces_same_model_version(tmp_path):
    products = make_products()
    run = make_run(make_inventory(products), [(date(2024, 3, 7), products["alpha"], 2, "20.00")])
    user = get_user_model().objects.create_user(username="seg-user-replace")
    file = tmp_path / "segments.json"
    file.write_text(json.dumps(payload(run.pk, "rfm-kmeans-v1", [
        {"customer_id": user.pk, "cluster_id": 0, "segment_label": "high_value",
         "recency_days": 1, "frequency_orders": 2, "monetary_total": "10.00",
         "k_clusters": 3, "silhouette_score": "0.4000"},
    ])), encoding="utf-8")
    call_command("load_customer_segments", "--run-id", str(run.pk), "--input", str(file))
    file.write_text(json.dumps(payload(run.pk, "rfm-kmeans-v1", [
        {"customer_id": user.pk, "cluster_id": 2, "segment_label": "core",
         "recency_days": 3, "frequency_orders": 4, "monetary_total": "70.00",
         "k_clusters": 3, "silhouette_score": "0.5000"},
    ])), encoding="utf-8")
    call_command("load_customer_segments", "--run-id", str(run.pk), "--input", str(file))

    row = CustomerSegment.objects.get(run=run, model_version="rfm-kmeans-v1")
    assert row.cluster_id == 2
    assert row.segment_label == "core"
    assert row.monetary_total == Decimal("70.00")


def test_load_customer_segments_rejects_mismatched_run_id(tmp_path):
    products = make_products()
    run = make_run(make_inventory(products), [(date(2024, 3, 7), products["alpha"], 2, "20.00")])
    other = make_run(make_inventory(products, version="inv-2"), [])
    user = get_user_model().objects.create_user(username="seg-user-mismatch")
    file = tmp_path / "segments.json"
    file.write_text(json.dumps(payload(other.pk, "rfm-kmeans-v1", [
        {"customer_id": user.pk, "cluster_id": 0, "segment_label": "high_value",
         "recency_days": 2, "frequency_orders": 2, "monetary_total": "20.00",
         "k_clusters": 3, "silhouette_score": "0.5000"},
    ])), encoding="utf-8")

    with pytest.raises(CommandError, match="does not match --run-id"):
        call_command("load_customer_segments", "--run-id", str(run.pk), "--input", str(file))
