"""Aggregate hold-out and subsample evidence for the published RFM segmentation recipe.

Time split: segment with orders before T - holdout_days, then measure each segment's completed
orders in [T - holdout_days, T). Subsample stability: refit on repeated 80% samples and compare
with the published labels. Writes aggregates only; no customer rows or identifiers.
"""
import argparse
from datetime import timedelta
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
from uuid import UUID

import numpy as np
import pandas as pd
import psycopg
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score

from segment_customers import connect, feature_matrix, fetch_rfm, fetch_run, fit_candidates, fit_segments


def fetch_outcomes(connection, namespace, start, end):
    """Completed orders per eligible customer in [start, end), with the trainer's eligibility rules."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT o.owner_id, COUNT(*), SUM(o.total)
            FROM orders_order o
            JOIN auth_user u ON u.id = o.owner_id
            WHERE NOT u.is_staff AND NOT u.is_superuser
              AND NOT EXISTS (
                  SELECT 1 FROM auth_user_groups ug
                  JOIN auth_group g ON g.id = ug.group_id
                  WHERE ug.user_id = u.id AND g.name = 'store_operator'
              )
              AND o.namespace = %s
              AND o.status = 'completed'
              AND o.placed_at >= %s AND o.placed_at < %s
            GROUP BY o.owner_id
        """, [namespace, start, end])
        rows = cursor.fetchall()
    frame = pd.DataFrame(rows, columns=["customer_id", "window_orders", "window_spend"])
    frame["window_orders"] = frame["window_orders"].astype(int)
    frame["window_spend"] = frame["window_spend"].astype(float)
    return frame


def holdout_outcomes(segmented, outcomes):
    """Per-segment repurchase and spend in the hold-out window for customers segmented before it."""
    joined = segmented[["customer_id", "segment_label"]].merge(outcomes, on="customer_id", how="left")
    joined["window_orders"] = joined["window_orders"].fillna(0).astype(int)
    joined["window_spend"] = joined["window_spend"].fillna(0.0)
    joined["repurchased"] = joined["window_orders"] > 0
    overall_rate = float(joined["repurchased"].mean())
    total_spend = float(joined["window_spend"].sum())
    segments = []
    for label, group in joined.groupby("segment_label", sort=True):
        rate = float(group["repurchased"].mean())
        spend = float(group["window_spend"].sum())
        segments.append({
            "segment_label": str(label),
            "customers": int(len(group)),
            "repurchase_rate": round(rate, 4),
            "repurchase_lift": None if overall_rate == 0 else round(rate / overall_rate, 3),
            "mean_window_orders": round(float(group["window_orders"].mean()), 3),
            "mean_window_spend": round(float(group["window_spend"].mean()), 2),
            "window_spend_share_percent": 0.0 if total_spend == 0 else round(spend / total_spend * 100, 1),
        })
    new_in_window = int((~outcomes["customer_id"].isin(segmented["customer_id"])).sum())
    return {
        "segmented_customers": int(len(joined)),
        "overall_repurchase_rate": round(overall_rate, 4),
        "overall_mean_window_spend": round(float(joined["window_spend"].mean()), 2),
        "customers_first_ordering_in_window_not_scored": new_in_window,
        "segments": segments,
    }


def subsample_stability(scaled, k_clusters, published_labels, repeats=20, fraction=0.8, seed=42):
    """ARI between published labels and refits on random subsamples, on the same customers."""
    rng = np.random.RandomState(seed)
    size = int(len(scaled) * fraction)
    scores = []
    for repeat in range(repeats):
        index = rng.choice(len(scaled), size=size, replace=False)
        labels = KMeans(n_clusters=k_clusters, random_state=repeat, n_init="auto").fit_predict(scaled[index])
        scores.append(adjusted_rand_score(published_labels[index], labels))
    return {"k": k_clusters, "repeats": repeats, "fraction": fraction,
            "ari_mean": round(float(np.mean(scores)), 4), "ari_min": round(float(np.min(scores)), 4),
            "ari_std": round(float(np.std(scores, ddof=0)), 4)}


def feature_diagnostics(scaled):
    """Skew of each model input and their pairwise correlation (both unchanged by standardising)."""
    frame = pd.DataFrame(scaled, columns=["recency", "frequency", "value"])
    corr = frame.corr()
    return {"skew": {name: round(float(frame[name].skew()), 3) for name in frame},
            "correlation": {"recency_frequency": round(float(corr.loc["recency", "frequency"]), 3),
                            "recency_value": round(float(corr.loc["recency", "value"]), 3),
                            "frequency_value": round(float(corr.loc["frequency", "value"]), 3)}}


def evaluate(connection, run_id, holdout_days, repeats, preprocessing="log_rfm_aov"):
    run = fetch_run(connection, run_id)
    cutoff = run["cutoff"]
    split = cutoff - timedelta(days=holdout_days)

    early = fetch_rfm(connection, run["namespace"], split)
    segmented, k_early, silhouette_early, _, _ = fit_segments(early, preprocessing=preprocessing)
    outcomes = fetch_outcomes(connection, run["namespace"], split, cutoff)
    time_split = {"split_at": split.isoformat(), "window_end": cutoff.isoformat(), "holdout_days": holdout_days,
                  "k_clusters": k_early, "silhouette": round(float(silhouette_early), 4),
                  **holdout_outcomes(segmented, outcomes)}

    full = fetch_rfm(connection, run["namespace"], cutoff)
    scaled = feature_matrix(full.sort_values("customer_id", kind="stable"), preprocessing)
    candidates, fitted = fit_candidates(scaled)
    segmented_full, k_full, silhouette_full, _, _ = fit_segments(full, preprocessing=preprocessing)
    sizes = segmented_full["segment_label"].value_counts()
    stability = [subsample_stability(scaled, item["k"], fitted[item["k"]], repeats=repeats)
                 for item in candidates if item["invalid_reason"] is None]

    return {
        "result": "evaluated", "run_id": run["run_id"], "namespace": run["namespace"],
        "cutoff": cutoff.isoformat(), "inventory_version": run["inventory_version"],
        "recipe": {"preprocessing": preprocessing, "k_range": [2, 4], "seed": 42,
                   "model_inputs": {"baseline": "recency, frequency, log1p total spend",
                                    "log_frequency": "recency, log1p frequency, log1p total spend",
                                    "log_rfm_aov": "log1p recency, log1p frequency, log1p average order value"}[preprocessing],
                   "selection": "highest-valid-silhouette-smaller-k-tie",
                   "note": "Same functions as analytics/segment_customers.py; evaluation does not change any published file."},
        "features": feature_diagnostics(scaled),
        "full_cohort": {"k_clusters": k_full, "silhouette": round(float(silhouette_full), 4),
                        "candidates_valid": sum(item["invalid_reason"] is None for item in candidates),
                        "candidates": len(candidates),
                        "smallest_segment_share_percent": round(float(sizes.min() / sizes.sum() * 100), 1),
                        "segment_sizes": {str(label): int(count) for label, count in sizes.sort_index().items()}},
        "time_split": time_split,
        "subsample_stability": {"customers": int(len(full)), "published_seed": 42, "candidates": stability},
        "identity": {"python": platform.python_version(),
                     "dependencies": {name: importlib.metadata.version(name)
                                      for name in ("numpy", "pandas", "scikit-learn", "scipy", "psycopg")}},
        "limitations": [
            "Synthetic order history: repurchase differences describe the generator, not real customers",
            "Descriptive association between segment and later orders, not a trained predictor or causal effect",
            "Lifetime features favour long-tenure customers (review M-04)",
            ("Log recency and average order value address review M-03" if preprocessing == "log_rfm_aov"
             else "Raw recency and total spend kept (review M-03)"),
            "Current database cohort, not an immutable historical snapshot",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--holdout-days", default=90, type=int)
    parser.add_argument("--repeats", default=20, type=int)
    parser.add_argument("--preprocessing", choices=("baseline", "log_frequency", "log_rfm_aov"), default="log_rfm_aov")
    args = parser.parse_args(argv)
    if not 1 <= args.holdout_days <= 365 or not 1 <= args.repeats <= 200:
        print("FAIL: --holdout-days must be 1..365 and --repeats 1..200", file=sys.stderr)
        return 1
    try:
        with connect() as connection:
            result = evaluate(connection, args.run_id, args.holdout_days, args.repeats, args.preprocessing)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (ValueError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error:
        print("FAIL: database unavailable or invalid query", file=sys.stderr)
        return 1
    print(json.dumps({"result": "PASS", "output": str(args.output), "preprocessing": args.preprocessing,
                      "features": result["features"], "full_cohort": result["full_cohort"],
                      "time_split": {key: result["time_split"][key] for key in
                                     ("split_at", "k_clusters", "overall_repurchase_rate", "segments")},
                      "subsample_stability": result["subsample_stability"]["candidates"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
