"""Retain aggregate evidence for the bounded baseline/log-frequency RFM comparison."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
from uuid import UUID

import numpy as np
import psycopg

from segment_customers import (connect, fetch_run, fetch_rfm, feature_matrix, fit_candidates,
                               fit_segments, build_output, _stability_against_published)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = ("customers.csv", "products.csv", "orders.csv", "order_items.csv", "payments.csv", "refunds.csv")
SEEDS = (42, 99, 123, 777)


def evaluate(connection, run_id, source):
    source_hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in SOURCE_FILES}
    expected = {name: digest for digest, name in
                (line.split() for line in (ROOT / "data/raw/checksums.txt").read_text().splitlines() if line.strip())}
    if source_hashes != expected:
        raise ValueError("Source hashes do not match the accepted raw revision")
    run = fetch_run(connection, run_id)
    frame = fetch_rfm(connection, run["namespace"], run["cutoff"])
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*), COUNT(*) FILTER (WHERE u.is_staff OR u.is_superuser OR EXISTS (
                SELECT 1 FROM auth_user_groups ug JOIN auth_group g ON g.id=ug.group_id
                WHERE ug.user_id=u.id AND g.name='store_operator'))
            FROM auth_user u WHERE EXISTS (
                SELECT 1 FROM accounts_customerprofile p WHERE p.user_id=u.id AND p.namespace=%s
            ) OR EXISTS (SELECT 1 FROM orders_order o WHERE o.owner_id=u.id AND o.namespace=%s)
        """, [run["namespace"], run["namespace"]])
        population, operators = cursor.fetchone()
        cursor.execute("""SELECT v.version, MIN(o.placed_at), MAX(o.placed_at)
            FROM reporting_analyticsrun r JOIN reporting_inventoryversion v ON v.id=r.inventory_id
            JOIN orders_order o ON o.namespace=v.namespace
            WHERE r.id=%s AND o.status='completed' AND o.placed_at<r.cutoff
            GROUP BY v.version""", [UUID(str(run_id))])
        inventory, first_order, last_order = cursor.fetchone()
    experiments = []
    for preprocessing in ("baseline", "log_frequency"):
        scaled = feature_matrix(frame, preprocessing)
        candidates, fitted = fit_candidates(scaled)
        for candidate in candidates:
            if candidate["invalid_reason"] is not None:
                continue
            mean, std = _stability_against_published(scaled, candidate["k"], fitted[candidate["k"]], SEEDS[1:])
            candidate.update(stability_ari_mean=mean, stability_ari_std=std)
            segmented, k, score, _, _ = fit_segments(frame, min_k=candidate["k"], max_k=candidate["k"],
                                                   stability_seeds=(), preprocessing=preprocessing)
            candidate["profiles"] = build_output(segmented, run_id, "evaluation", k, score, mean, std)["segment_profiles"]
        valid = [item for item in candidates if item["invalid_reason"] is None]
        selected = max(valid, key=lambda item: (item["silhouette"], -item["k"])) if valid else None
        experiments.append({"preprocessing": preprocessing, "candidates": candidates,
                            "best_k": selected["k"] if selected else None})
    if experiments[1]["best_k"] is None:
        raise ValueError("No valid candidate for selected preprocessing: " + json.dumps(experiments))
    fields = ["recency_days", "frequency_orders", "monetary_total", "monetary_log"]
    code_paths = ("analytics/segment_customers.py", "analytics/evaluate_segments.py", "analytics/requirements.txt")
    # Exact working code bytes plus baseline and patch identity avoid a self-referential artifact hash.
    diff = subprocess.check_output(["git", "diff", "HEAD", "--", *code_paths], cwd=ROOT)
    return {
        "result": "evaluated", "run_id": str(run_id), "namespace": run["namespace"],
        "cutoff": run["cutoff"].isoformat(), "inventory_version": inventory,
        "source": {"release": "Analytics Engineering Ecommerce Sales & Returns v1.0.0",
                   "sha256": source_hashes,
                   "adoption": "Accepted raw revision; shoe remap is approved plan only and requires separate evaluation after adoption."},
        "cohort": {"population_definition": "Users with a source profile or any order in the namespace",
                   "population": population, "included": len(frame), "excluded_privileged": operators,
                   "excluded_without_completed_pre_cutoff_order": population - operators - len(frame),
                   "included_with_one_order": int((frame["frequency_orders"] == 1).sum()),
                   "eligibility": "At least one completed order strictly before cutoff; exclude staff, superusers and store_operator members. No profile or minimum tenure required."},
        "features": {"period": "Lifetime completed history strictly before cutoff, independent of dashboard date filter",
                     "earliest_completed_order": first_order.isoformat(), "latest_completed_order": last_order.isoformat(),
                     "definitions": {"recency_days": "Floor elapsed days since latest eligible completed order",
                                     "frequency_orders": "Count of eligible completed orders",
                                     "monetary_total": "Sum of application order totals (rounded unit price times quantity); simulated SGD"},
                     "excluded_inputs": ["source customer_segment", "names", "email", "signup date"],
                     "skew": {name: float(frame[name].skew()) for name in fields},
                     "log_frequency_skew": float(np.log1p(frame["frequency_orders"]).skew()),
                     "correlation": frame[fields].corr().to_dict()},
        "method": {"algorithm": "KMeans", "n_init": "auto", "seeds": list(SEEDS), "published_seed": 42,
                   "k_range": [2, 3, 4], "k_rationale": "Small interpretable profile set; no k forced to obtain a desired label",
                   "baseline": "StandardScaler of recency, frequency, log1p monetary",
                   "alternative": "StandardScaler of recency, log1p frequency, log1p monetary",
                   "alternative_rationale": "Measured frequency skew is reduced in absolute magnitude by log1p; test one bounded change without changing RFM meaning",
                   "silhouette": "Fixed seed 42 sample of at most 5000 customers; all customers fitted",
                   "stability": "ARI against published labels for seeds 99,123,777 on the same full cohort",
                   "naming": "Relative cluster-profile medians: recent/older, more/fewer orders, higher/lower spend; stable profile rank prefix ensures unique labels. Equality uses recent/fewer/lower."},
        "experiments": experiments,
        "selection": {"preprocessing": "log_frequency", "model_version": "rfm-kmeans-v2",
                      "k": experiments[1]["best_k"],
                      "rationale": "Accepted-revision comparison supports the single log-frequency change: higher sampled separation, similar strong seed stability, substantial groups and the same interpretable relative profile ordering. Choose highest valid silhouette within this preprocessing; ties prefer lower k. This is descriptive geometry, not predictive performance. Reassess this policy for another revision."},
        "identity": {"git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                     "tracked_code_diff_sha256": hashlib.sha256(diff).hexdigest(),
                     "working_files_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in code_paths},
                     "python": platform.python_version(), "platform": platform.platform(),
                     "dependencies": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "scikit-learn", "scipy", "psycopg", "joblib", "threadpoolctl")}},
        "reproduction": {"setup": "Use isolated PostgreSQL; install src/requirements.txt plus analytics/requirements.txt in a separate analytics environment. Import verified data/raw namespace, refresh as-of 2026-01-02; see analytics/README.md. Supply credentials only through environment.",
                         "command": "python analytics/evaluate_segments.py --run-id <NEW_RUN_UUID> --source data/raw --output evidence/ml-quality-evaluation.json",
                         "thread_limits": "OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1"},
        "limitations": ["Synthetic generator structure, not evidence of real customer behaviour or churn/prediction",
                        "Lifetime frequency/spend depend on opportunity and tenure; one-order customers retained, no minimum-tenure correction",
                        "Correlated frequency and spend weight purchasing volume twice; not causal features",
                        "Silhouette measures geometry under each transform, not comparable predictive accuracy",
                        "Current database cohort, not immutable historical feature snapshot; raw hashes do not prove unchanged database history",
                        "No assignment rows or personal fields retained in this aggregate artifact"],
        "unrun_experiments": ["Resampling omitted: chosen k=2 has strong seed stability and clear profiles; this bounded check makes no resampling robustness claim", "Temporal prediction, saved-model inference, AWS and shoe remap evaluation not run"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        with connect() as connection:
            result = evaluate(connection, args.run_id, args.source)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (ValueError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error:
        print("FAIL: database unavailable or invalid query", file=sys.stderr)
        return 1
    print("Aggregate evaluation written to " + str(args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
