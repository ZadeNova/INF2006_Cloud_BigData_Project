"""Independent verifier regressions; raw fixtures never call production analytics calculations."""
from datetime import date, datetime, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
from uuid import uuid4
import sys

import pytest
from django.contrib.auth import get_user_model
from django.db import connection

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))

from analytics_helpers import add_order, at, make_inventory, make_products, make_run
from reporting.models import AnalyticsRun

spec = importlib.util.spec_from_file_location("verify_refresh", Path(__file__).resolve().parents[1] / "verify_refresh.py")
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


@pytest.fixture
def raw_world():
    run = dict(id=uuid4(), summary_version=uuid4(), inventory_id=1, namespace="fixture", version="v1",
               window_start=at(2024, 2, 1, 0), cutoff=at(2024, 3, 8, 0))
    def line(day, quantity, price="1.01", status="completed", product=1):
        return dict(order_id=len(lines) + 1, status=status, placed_at=day, product_id=product,
                    quantity=quantity, unit_price=Decimal(price))
    lines = []
    # UTC 16:00 rolls into Singapore March 1; 15:59 remains February 29.
    lines.append(line(datetime(2024, 2, 29, 16, tzinfo=timezone.utc), 7))
    lines.append(line(datetime(2024, 2, 29, 15, 59, tzinfo=timezone.utc), 2))
    lines.append(line(at(2024, 3, 7), 7, "2.03"))
    lines.append(line(at(2024, 3, 8, 0), 99))
    lines.append(line(at(2024, 3, 2), 99, status="cancelled"))
    lines.append(line(at(2024, 3, 3), 99, status="refunded"))
    lines.append(line(at(2024, 1, 31), 99))
    snapshots = [dict(product_id=1, stock=14, lead_time_days=7),
                 dict(product_id=2, stock=15, lead_time_days=7)]
    return run, lines, snapshots


def test_independent_dates_status_historical_money_and_fixed_zero_filled_week(raw_world):
    daily, coverage, orders, lines = verify.recompute(*raw_world)
    assert daily == {(date(2024, 2, 29), 1): (2, Decimal("2.02")),
                     (date(2024, 3, 1), 1): (7, Decimal("7.07")),
                     (date(2024, 3, 7), 1): (7, Decimal("14.21"))}
    assert (orders, lines) == (3, 3)
    assert coverage[1] == dict(product_id=1, stock=14, lead_time_days=7, units_7d=14,
                              avg_daily_units=Decimal("2.00"), coverage_days=Decimal("7.00"), status="flagged")
    assert coverage[2]["coverage_days"] is None
    assert coverage[2]["status"] == "unavailable"
    raw_world[2][0]["stock"] = 15
    assert verify.recompute(*raw_world)[1][1]["status"] == "ok"


def test_partial_and_empty_history_keep_denominator_and_unavailable_coverage(raw_world):
    run, lines, snapshots = raw_world
    for source in ([lines[2]], []):
        coverage = verify.recompute(run, source, snapshots)[1]
        assert coverage[1]["avg_daily_units"] == (Decimal("1.00") if source else Decimal("0.00"))
        assert all(row["status"] == "insufficient_history" and row["coverage_days"] is None for row in coverage.values())


@pytest.mark.django_db
def test_database_run_selection_snapshot_values_and_no_cross_run_aggregation():
    products = make_products(names=("alpha",))
    inventory = make_inventory(products, values={"alpha": (14, 7)})
    owner = get_user_model().objects.create_user(username="verifier")
    add_order(owner, "sale", [(products["alpha"], 14, "1.01")], at(2024, 3, 1))
    run = make_run(inventory, [(date(2024, 3, 1), products["alpha"], 14, "14.14")])
    make_run(inventory, [(date(2024, 3, 1), products["alpha"], 999, "999.00")])
    products["alpha"].stock = 999
    products["alpha"].lead_time_days = 0
    products["alpha"].price = "999.00"
    products["alpha"].save()
    loaded, lines, snapshots, persisted = verify.load(connection, run.pk)
    assert loaded["id"] == run.pk
    assert persisted[0]["units"] == 14 and len(persisted) == 1
    daily, coverage, _, _ = verify.recompute(loaded, lines, snapshots)
    assert daily[(date(2024, 3, 1), products["alpha"].pk)] == (14, Decimal("14.14"))
    assert coverage[products["alpha"].pk]["status"] == "flagged"
    failed = make_run(inventory, [], status=AnalyticsRun.Status.FAILED)
    for invalid in (failed.pk, uuid4()):
        with pytest.raises(ValueError, match="completed"):
            verify.load(connection, invalid)


def test_cli_deliberate_cent_mismatch_fails_and_rejects_foreign_target(raw_world, monkeypatch, tmp_path, capsys):
    import json
    run, lines, snapshots = raw_world
    expected, coverage, _, _ = verify.recompute(*raw_world)
    persisted = [dict(business_date=day, product_id=product, units=units, sales_amount=amount)
                 for (day, product), (units, amount) in expected.items()]
    target = dict(run_id=str(run["id"]), summary_version=str(run["summary_version"]), inventory_id=1,
                  namespace="fixture", inventory_version="v1", rows=list(coverage.values()))
    assert verify.compare(run, lines, snapshots, persisted, target)["result"] == "PASS"
    persisted[0]["sales_amount"] += Decimal("0.01")
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps(target, default=str))
    from contextlib import nullcontext
    class Cursor:
        def execute(self, sql):
            pass
    class Connection:
        def cursor(self):
            return nullcontext(Cursor())
    monkeypatch.setattr(verify, "connect", lambda _: nullcontext(Connection()))
    monkeypatch.setattr(verify, "load", lambda *_: (run, lines, snapshots, persisted))
    assert verify.main(["--run-id", str(run["id"]), "--coverage-target", str(path)]) == 1
    summary = json.loads(capsys.readouterr().out)
    assert summary["sales_amount_mismatches"] == 1
    assert summary["maximum_absolute_monetary_difference"] == "0.01"
    target["run_id"] = str(uuid4())
    with pytest.raises(ValueError, match="metadata"):
        verify.compare(run, lines, snapshots, persisted, target)
