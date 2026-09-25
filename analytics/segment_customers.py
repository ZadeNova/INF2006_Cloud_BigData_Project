"""Offline RFM customer segmentation with K-means for one completed analytics run."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from uuid import UUID

import numpy as np
import pandas as pd
import psycopg
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler


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


def fetch_run(connection, run_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT r.id, r.cutoff, r.status, v.namespace
            FROM reporting_analyticsrun r
            JOIN reporting_inventoryversion v ON v.id = r.inventory_id
            WHERE r.id = %s
        """, [UUID(str(run_id))])
        row = cursor.fetchone()
    if row is None or row[2] != "completed":
        raise ValueError("Run must exist and be completed")
    return {"run_id": str(row[0]), "cutoff": row[1], "namespace": row[3]}


def fetch_rfm(connection, namespace, cutoff):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT o.owner_id,
                   MAX(o.placed_at) AS last_order_at,
                   COUNT(*) AS frequency_orders,
                   SUM(o.total) AS monetary_total
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
              AND o.placed_at < %s
            GROUP BY o.owner_id
            ORDER BY o.owner_id
        """, [namespace, cutoff])
        rows = cursor.fetchall()
    if not rows:
        raise ValueError("No completed customer orders exist before the cutoff")
    frame = pd.DataFrame(rows, columns=["customer_id", "last_order_at", "frequency_orders", "monetary_total"])
    cutoff_ts = pd.Timestamp(cutoff).tz_convert("Asia/Singapore")
    frame["recency_days"] = (cutoff_ts - pd.to_datetime(frame["last_order_at"], utc=True)
                             .dt.tz_convert("Asia/Singapore")).dt.days
    frame["frequency_orders"] = frame["frequency_orders"].astype(int)
    frame["monetary_total"] = frame["monetary_total"].astype(float)
    frame["monetary_log"] = np.log1p(frame["monetary_total"])
    return frame


def _segment_name_mapping(profiles):
    """Describe relative profile means, without a loyalty or churn claim.

    Ranks make labels unique even when two profiles have the same description;
    ties are resolved by cluster ID. All labels fit the serving field's 40 chars.
    """
    ordered = profiles.sort_values(["mean_recency", "mean_frequency", "mean_monetary", "cluster_id"],
                                  ascending=[True, False, False, True])
    middle = profiles[["mean_recency", "mean_frequency", "mean_monetary"]].median()
    labels = {}
    for rank, row in enumerate(ordered.itertuples(index=False), 1):
        recency = "recent" if row.mean_recency <= middle["mean_recency"] else "older"
        frequency = "more_orders" if row.mean_frequency > middle["mean_frequency"] else "fewer_orders"
        spend = "higher_spend" if row.mean_monetary > middle["mean_monetary"] else "lower_spend"
        labels[row.cluster_id] = f"{rank}_{recency}_{frequency}_{spend}"
    return labels


def _stability_against_published(scaled, k_clusters, published_labels, seeds):
    if len(scaled) <= k_clusters or len(seeds) < 1:
        return None, None
    scores = []
    for seed in seeds:
        labels = KMeans(n_clusters=k_clusters, random_state=seed, n_init="auto").fit_predict(scaled)
        scores.append(adjusted_rand_score(published_labels, labels))
    if not scores:
        return None, None
    return float(np.mean(scores)), float(np.std(scores, ddof=0))


def feature_matrix(frame, preprocessing="baseline"):
    features = frame[["recency_days", "frequency_orders", "monetary_total"]].to_numpy(dtype=float)
    if not np.isfinite(features).all() or (features < 0).any():
        raise ValueError("RFM features must be finite and nonnegative")
    features[:, 2] = np.log1p(features[:, 2])
    if preprocessing == "log_frequency":
        features[:, 1] = np.log1p(features[:, 1])
    elif preprocessing != "baseline":
        raise ValueError("Unknown preprocessing")
    return StandardScaler().fit_transform(features)


def fit_candidates(scaled, min_k=2, max_k=4, random_seed=42):
    if isinstance(min_k, bool) or isinstance(max_k, bool) or not isinstance(min_k, int) or not isinstance(max_k, int) or not 2 <= min_k <= max_k <= 32767:
        raise ValueError("Require integer cluster bounds 2 <= min_k <= max_k <= 32767")
    distinct = len(np.unique(scaled, axis=0))
    candidates, fitted = [], {}
    for k in range(min_k, max_k + 1):
        item = {"k": k, "seed": random_seed, "silhouette": None, "invalid_reason": None,
                "actual_clusters": 0, "cluster_sizes": []}
        if k >= len(scaled):
            item["invalid_reason"] = "k must be smaller than customer count"
        elif k > distinct:
            item["invalid_reason"] = "k exceeds distinct feature vectors"
        else:
            labels = KMeans(n_clusters=k, random_state=random_seed, n_init="auto").fit_predict(scaled)
            _, sizes = np.unique(labels, return_counts=True)
            item["actual_clusters"] = len(sizes)
            item["cluster_sizes"] = sizes.tolist()
            if not 2 <= len(sizes) < len(scaled):
                item["invalid_reason"] = "actual fitted labels cannot define silhouette"
            elif len(sizes) != k:
                item["invalid_reason"] = "fit collapsed below requested k"
            else:
                sample = np.random.RandomState(random_seed).permutation(len(scaled))[:5000]
                if not 2 <= len(np.unique(labels[sample])) < len(sample):
                    item["invalid_reason"] = "silhouette sample cannot define metric"
                    candidates.append(item)
                    continue
                score = float(silhouette_score(scaled[sample], labels[sample]))
                if np.isfinite(score):
                    item["silhouette"] = score
                    fitted[k] = labels
                else:
                    item["invalid_reason"] = "silhouette is nonfinite"
        candidates.append(item)
    return candidates, fitted


def fit_segments(frame, min_k=2, max_k=4, random_seed=42, stability_seeds=(42, 99, 123, 777),
                 preprocessing="log_frequency"):
    frame = frame.sort_values("customer_id", kind="stable").copy()
    scaled = feature_matrix(frame, preprocessing)
    candidates, fitted = fit_candidates(scaled, min_k, max_k, random_seed)
    valid = [item for item in candidates if item["invalid_reason"] is None]
    if not valid:
        raise ValueError("No valid clustering candidate: " + json.dumps(candidates))
    selected = max(valid, key=lambda item: (item["silhouette"], -item["k"]))
    chosen_k, silhouette = selected["k"], selected["silhouette"]
    labels = fitted[chosen_k]
    frame["cluster_id"] = labels
    profiles = frame.groupby("cluster_id", as_index=False).agg(
        mean_monetary=("monetary_total", "mean"),
        mean_recency=("recency_days", "mean"),
        mean_frequency=("frequency_orders", "mean"),
    ).reset_index(drop=True)
    mapping = _segment_name_mapping(profiles)
    frame["segment_label"] = frame["cluster_id"].map(mapping)
    comparison_seeds = [seed for seed in dict.fromkeys(stability_seeds) if seed != random_seed]
    stability_mean, stability_std = _stability_against_published(
        scaled, chosen_k, labels, comparison_seeds)
    return frame, chosen_k, silhouette, stability_mean, stability_std


def build_output(frame, run_id, model_version, k_clusters, silhouette, stability_ari_mean, stability_ari_std):
    total_sales = float(frame["monetary_total"].sum())
    grouped = (frame.groupby(["segment_label", "cluster_id"], as_index=False)
               .agg(customers=("customer_id", "count"),
                    sales_amount=("monetary_total", "sum"),
                    mean_recency_days=("recency_days", "mean"),
                    mean_frequency_orders=("frequency_orders", "mean"),
                    mean_monetary_total=("monetary_total", "mean"))
               .sort_values(["sales_amount", "cluster_id"], ascending=[False, True]))

    rows = [{
        "customer_id": int(item.customer_id),
        "cluster_id": int(item.cluster_id),
        "segment_label": str(item.segment_label),
        "recency_days": int(item.recency_days),
        "frequency_orders": int(item.frequency_orders),
        "monetary_total": f"{item.monetary_total:.2f}",
        "k_clusters": int(k_clusters),
        "silhouette_score": None if silhouette is None else round(float(silhouette), 4),
    } for item in frame.itertuples(index=False)]

    segment_profiles = [{
        "segment_label": str(item.segment_label),
        "cluster_id": int(item.cluster_id),
        "customers": int(item.customers),
        "sales_amount": f"{item.sales_amount:.2f}",
        "sales_share_percent": 0.0 if total_sales == 0 else round(float(item.sales_amount) / total_sales * 100, 1),
        "mean_recency_days": round(float(item.mean_recency_days), 2),
        "mean_frequency_orders": round(float(item.mean_frequency_orders), 2),
        "mean_monetary_total": round(float(item.mean_monetary_total), 2),
    } for item in grouped.itertuples(index=False)]

    return {
        "run_id": str(run_id),
        "model_version": model_version,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "k_clusters": int(k_clusters),
        "silhouette_score": None if silhouette is None else round(float(silhouette), 4),
        "stability_ari_mean": None if stability_ari_mean is None else round(float(stability_ari_mean), 4),
        "stability_ari_std": None if stability_ari_std is None else round(float(stability_ari_std), 4),
        "rows": rows,
        "segment_profiles": segment_profiles,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, type=UUID)
    parser.add_argument("--output", required=True, type=Path, help="JSON output consumed by load_customer_segments")
    parser.add_argument("--model-version", default="rfm-kmeans-v2")
    parser.add_argument("--min-k", default=2, type=int)
    parser.add_argument("--max-k", default=4, type=int)
    parser.add_argument("--preprocessing", choices=("baseline", "log_frequency"), default="log_frequency")
    parser.add_argument("--seed", default=42, type=int)
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args(argv)
    try:
        with connect(args.database_url) as connection:
            run = fetch_run(connection, args.run_id)
            frame = fetch_rfm(connection, run["namespace"], run["cutoff"])
        segmented, chosen_k, silhouette, stability_ari_mean, stability_ari_std = fit_segments(
            frame, min_k=args.min_k, max_k=args.max_k, random_seed=args.seed, preprocessing=args.preprocessing)
        payload = build_output(
            segmented, run["run_id"], args.model_version, chosen_k, silhouette, stability_ari_mean, stability_ari_std)
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps({
            "result": "PASS",
            "run_id": run["run_id"],
            "model_version": args.model_version,
            "customers": len(segmented),
            "k_clusters": chosen_k,
            "silhouette_score": None if silhouette is None else round(float(silhouette), 4),
            "stability_ari_mean": None if stability_ari_mean is None else round(float(stability_ari_mean), 4),
            "stability_ari_std": None if stability_ari_std is None else round(float(stability_ari_std), 4),
            "output": str(args.output),
        }, indent=2))
        return 0
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    except TypeError:
        print("FAIL: invalid input", file=sys.stderr)
        return 1
    except psycopg.Error:
        print("FAIL: database unavailable or invalid query", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
