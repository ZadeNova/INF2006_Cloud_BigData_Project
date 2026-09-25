"""Independent raw-table pandas cross-check; production coverage is an exported target."""
import argparse
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
import os
from pathlib import Path
import sys
from uuid import UUID

import pandas as pd
import psycopg

CENT = Decimal("0.01")


def fetch(connection, sql, params):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]


def load(connection, run_id):
    rows = fetch(connection, """SELECT r.id, r.summary_version, r.status, r.window_start, r.cutoff,
        r.inventory_id, v.namespace, v.version, v.sealed, v.cutoff AS inventory_cutoff
        FROM reporting_analyticsrun r JOIN reporting_inventoryversion v ON v.id = r.inventory_id
        WHERE r.id = %s""", [UUID(str(run_id))])
    if not rows or rows[0]["status"] != "completed":
        raise ValueError("Run must exist and be completed")
    run = rows[0]
    if not run["sealed"] or run["inventory_cutoff"] != run["cutoff"]:
        raise ValueError("Inventory must be sealed and cutoff aligned")
    products = fetch(connection, "SELECT id FROM catalogue_product WHERE namespace = %s", [run["namespace"]])
    snapshots = fetch(connection, "SELECT product_id, stock, lead_time_days FROM reporting_inventorysnapshot WHERE inventory_id = %s", [run["inventory_id"]])
    if not products or {p["id"] for p in products} != {s["product_id"] for s in snapshots}:
        raise ValueError("Inventory is missing or incomplete")
    # Deliberately leave status/date conversion to pandas, independent of the reporting view.
    lines = fetch(connection, """SELECT o.id AS order_id, o.status, o.placed_at,
        i.product_id, i.quantity, i.unit_price
        FROM orders_order o JOIN orders_orderitem i ON i.order_id = o.id
        WHERE o.namespace = %s AND o.placed_at >= %s AND o.placed_at < %s""",
        [run["namespace"], run["window_start"], run["cutoff"]])
    daily = fetch(connection, "SELECT business_date, product_id, units, sales_amount FROM reporting_dailyproductsales WHERE run_id = %s", [run["id"]])
    return run, lines, snapshots, daily


def recompute(run, lines, snapshots):
    cutoff = pd.Timestamp(run["cutoff"]).tz_convert("Asia/Singapore")
    start = pd.Timestamp(run["window_start"]).tz_convert("Asia/Singapore")
    latest = cutoff.date() - timedelta(days=1)
    first = latest - timedelta(days=6)
    frame = pd.DataFrame(lines, columns=["order_id", "status", "placed_at", "product_id", "quantity", "unit_price"])
    frame["business_date"] = pd.to_datetime(frame["placed_at"], utc=True).dt.tz_convert("Asia/Singapore").dt.date
    frame = frame[(frame["status"] == "completed") & (frame["business_date"] >= start.date()) & (frame["business_date"] <= latest)].copy()
    frame["sales_amount"] = [int(q) * Decimal(p) for q, p in zip(frame["quantity"], frame["unit_price"])]
    daily = {(day, int(product)): (int(group["quantity"].sum()), sum(group["sales_amount"], Decimal(0)))
             for (day, product), group in frame.groupby(["business_date", "product_id"])}
    history = min((key[0] for key in daily), default=None)
    sufficient = history is not None and history <= first
    dates = pd.date_range(first, latest).date
    coverage = {}
    for snapshot in snapshots:
        product = snapshot["product_id"]
        # Explicit seven-date spine: missing sparse rows contribute zero.
        units = sum(daily.get((day, product), (0, Decimal(0)))[0] for day in dates)
        stock, lead = snapshot["stock"], snapshot["lead_time_days"]
        average = (Decimal(units) / 7).quantize(CENT, rounding=ROUND_HALF_UP)
        days = (Decimal(stock) * 7 / units).quantize(CENT, rounding=ROUND_HALF_UP) if sufficient and units else None
        status = ("insufficient_history" if not sufficient else "unavailable" if not units else
                  "flagged" if stock * 7 <= lead * units else "ok")
        coverage[product] = dict(product_id=product, stock=stock, lead_time_days=lead, units_7d=units,
                                 avg_daily_units=average, coverage_days=days, status=status)
    return daily, coverage, int(frame["order_id"].nunique()), len(frame)


def compare(run, lines, snapshots, persisted, target):
    metadata = {"run_id": str(run["id"]), "summary_version": str(run["summary_version"]),
                "inventory_id": run["inventory_id"], "namespace": run["namespace"], "inventory_version": run["version"]}
    if any(target.get(key) != value for key, value in metadata.items()):
        raise ValueError("Coverage target metadata does not match selected run")
    expected, coverage, orders, count = recompute(run, lines, snapshots)
    actual = {(r["business_date"], r["product_id"]): (r["units"], r["sales_amount"]) for r in persisted}
    keys = expected.keys() | actual.keys()
    units = sum(expected.get(k, (0, 0))[0] != actual.get(k, (0, 0))[0] for k in keys)
    differences = [abs(expected.get(k, (0, Decimal(0)))[1] - actual.get(k, (0, Decimal(0)))[1]) for k in keys]
    target_rows = {}
    for row in target["rows"]:
        row = dict(row)
        for field in ("avg_daily_units", "coverage_days"):
            if row[field] is not None:
                row[field] = Decimal(row[field])
        target_rows[row["product_id"]] = row
    coverage_mismatches = sum(coverage.get(k) != target_rows.get(k) for k in coverage.keys() | target_rows.keys())
    row_mismatches = len(expected.keys() ^ actual.keys()) + len(persisted) - len(actual)
    duplicate_targets = len(target["rows"]) - len(target_rows)
    summary = dict(**metadata, window_start=str(run["window_start"]), cutoff=str(run["cutoff"]),
        latest_complete_date=str(pd.Timestamp(run["cutoff"]).tz_convert("Asia/Singapore").date() - timedelta(days=1)),
        raw_completed_orders=orders, raw_completed_lines=count, expected_daily_rows=len(expected), persisted_daily_rows=len(persisted),
        daily_row_mismatches=row_mismatches, units_mismatches=units, sales_amount_mismatches=sum(d != 0 for d in differences),
        coverage_flag_mismatches=coverage_mismatches + duplicate_targets,
        insufficient_history_products=sum(r["status"] == "insufficient_history" for r in coverage.values()),
        no_recent_sales_products=sum(r["units_7d"] == 0 for r in coverage.values()),
        flagged_products=sum(r["status"] == "flagged" for r in coverage.values()),
        maximum_absolute_monetary_difference=str(max(differences, default=Decimal(0))))
    summary["result"] = "FAIL" if row_mismatches or units or any(differences) or coverage_mismatches or duplicate_targets else "PASS"
    return summary


def connect(database_url=None):
    if database_url:
        return psycopg.connect(database_url, connect_timeout=10)
    required = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST")
    if any(not os.environ.get(name) for name in required):
        raise ValueError("Missing PostgreSQL environment configuration")
    options = dict(dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"],
                   password=os.environ["POSTGRES_PASSWORD"], host=os.environ["POSTGRES_HOST"],
                   port=os.environ.get("POSTGRES_PORT", "5432"), connect_timeout=10)
    for name in ("SSLMODE", "SSLROOTCERT"):
        if os.environ.get("POSTGRES_" + name):
            options[name.lower()] = os.environ["POSTGRES_" + name]
    return psycopg.connect(**options)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    parser.add_argument("--coverage-target", required=True, type=Path, help="JSON from export_coverage.py")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args(argv)
    try:
        target = json.loads(args.coverage_target.read_text(encoding="utf-8"))
        with connect(args.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            summary = compare(*load(connection, args.run_id), target)
        print(json.dumps(summary, indent=2))
        return 0 if summary["result"] == "PASS" else 1
    except (ValueError, KeyError, TypeError, ArithmeticError, OSError, psycopg.Error):
        # Database exceptions may contain credentials or raw data; never echo them.
        print("FAIL: invalid input, unavailable database, or invalid run/inventory/coverage target", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
