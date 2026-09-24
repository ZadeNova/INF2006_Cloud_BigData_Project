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
            WHERE o.namespace = %s
              AND o.status = 'completed'
              AND o.placed_at < %s
            GROUP BY o.owner_id
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
    """Assign readable segment names using recency+frequency+monetary, not spend alone."""
    profile = profiles.copy()
    for source, target in (("mean_monetary", "z_monetary"),
                           ("mean_frequency", "z_frequency"),
                           ("mean_recency", "z_recency")):
        std = profile[source].std(ddof=0)
        profile[target] = 0.0 if std == 0 else (profile[source] - profile[source].mean()) / std
    profile["business_score"] = profile["z_monetary"] + profile["z_frequency"] - profile["z_recency"]
    ordered = profile.sort_values(["business_score", "cluster_id"], ascending=[False, True])["cluster_id"].tolist()
    labels = {}
    if len(ordered) == 1:
        labels[ordered[0]] = "core"
        return labels
    labels[ordered[0]] = "high_value"
    if len(ordered) == 2:
        labels[ordered[1]] = "core"
        return labels
    labels[ordered[1]] = "core"
    labels[ordered[-1]] = "at_risk"
    extra = 1
    for cluster_id in ordered[2:-1]:
        labels[cluster_id] = f"cluster_{extra}"
        extra += 1
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


def fit_segments(frame, min_k=2, max_k=6, random_seed=42, stability_seeds=(42, 99, 123, 777)):
    features = frame[["recency_days", "frequency_orders", "monetary_log"]].to_numpy(dtype=float)
    if len(features) < min_k:
        raise ValueError(f"Need at least {min_k} customers for clustering")
    scaled = StandardScaler().fit_transform(features)
    upper = min(max_k, len(features) - 1)
    if upper < min_k:
        upper = min_k

    candidates = []
    for k in range(min_k, upper + 1):
        model = KMeans(n_clusters=k, random_state=random_seed, n_init="auto")
        labels = model.fit_predict(scaled)
        score = silhouette_score(scaled, labels) if k > 1 and len(features) > k else -1.0
        candidates.append((score, k, labels))
    score, chosen_k, labels = max(candidates, key=lambda item: (item[0], -item[1]))
    silhouette = None if score < 0 else float(score)
    frame = frame.copy()
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
    parser.add_argument("--model-version", default="rfm-kmeans-v1")
    parser.add_argument("--min-k", default=2, type=int)
    parser.add_argument("--max-k", default=6, type=int)
    parser.add_argument("--seed", default=42, type=int)
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args(argv)
    try:
        with connect(args.database_url) as connection:
            run = fetch_run(connection, args.run_id)
            frame = fetch_rfm(connection, run["namespace"], run["cutoff"])
        segmented, chosen_k, silhouette, stability_ari_mean, stability_ari_std = fit_segments(
            frame, min_k=args.min_k, max_k=args.max_k, random_seed=args.seed)
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
