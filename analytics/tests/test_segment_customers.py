import importlib.util
from pathlib import Path

import pandas as pd
from sklearn.preprocessing import StandardScaler


spec = importlib.util.spec_from_file_location(
    "segment_customers", Path(__file__).resolve().parents[1] / "segment_customers.py")
segment_customers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(segment_customers)


def test_segment_name_mapping_uses_recency_and_not_only_spend():
    profiles = pd.DataFrame([
        {"cluster_id": 1, "mean_monetary": 100.0, "mean_frequency": 2.0, "mean_recency": 40.0},
        {"cluster_id": 2, "mean_monetary": 95.0, "mean_frequency": 7.0, "mean_recency": 3.0},
        {"cluster_id": 3, "mean_monetary": 80.0, "mean_frequency": 1.0, "mean_recency": 120.0},
    ])
    labels = segment_customers._segment_name_mapping(profiles)
    assert labels[2] == "high_value"
    assert labels[1] == "core"
    assert labels[3] == "at_risk"


def test_fit_segments_and_build_output_include_stability_metrics():
    frame = pd.DataFrame([
        {"customer_id": 1, "recency_days": 5, "frequency_orders": 6, "monetary_total": 900.0, "monetary_log": 6.8},
        {"customer_id": 2, "recency_days": 6, "frequency_orders": 5, "monetary_total": 820.0, "monetary_log": 6.7},
        {"customer_id": 3, "recency_days": 4, "frequency_orders": 7, "monetary_total": 980.0, "monetary_log": 6.9},
        {"customer_id": 4, "recency_days": 80, "frequency_orders": 1, "monetary_total": 60.0, "monetary_log": 4.1},
        {"customer_id": 5, "recency_days": 75, "frequency_orders": 1, "monetary_total": 55.0, "monetary_log": 4.0},
        {"customer_id": 6, "recency_days": 90, "frequency_orders": 2, "monetary_total": 70.0, "monetary_log": 4.3},
    ])
    segmented, chosen_k, silhouette, stability_mean, stability_std = segment_customers.fit_segments(
        frame, min_k=2, max_k=2, random_seed=42, stability_seeds=(1, 2, 3, 4))
    output = segment_customers.build_output(
        segmented, "run-1", "rfm-kmeans-v1", chosen_k, silhouette, stability_mean, stability_std)

    assert output["k_clusters"] == 2
    assert output["stability_ari_mean"] is not None
    assert output["stability_ari_std"] is not None
    assert len(output["rows"]) == 6


def test_stability_excludes_published_seed_from_comparison():
    frame = pd.DataFrame([
        {"customer_id": 1, "recency_days": 5, "frequency_orders": 6, "monetary_total": 900.0, "monetary_log": 6.8},
        {"customer_id": 2, "recency_days": 6, "frequency_orders": 5, "monetary_total": 820.0, "monetary_log": 6.7},
        {"customer_id": 3, "recency_days": 4, "frequency_orders": 7, "monetary_total": 980.0, "monetary_log": 6.9},
        {"customer_id": 4, "recency_days": 80, "frequency_orders": 1, "monetary_total": 60.0, "monetary_log": 4.1},
        {"customer_id": 5, "recency_days": 75, "frequency_orders": 1, "monetary_total": 55.0, "monetary_log": 4.0},
        {"customer_id": 6, "recency_days": 90, "frequency_orders": 2, "monetary_total": 70.0, "monetary_log": 4.3},
    ])
    segmented, _, _, stability_mean, stability_std = segment_customers.fit_segments(
        frame, min_k=2, max_k=2, random_seed=42, stability_seeds=(42, 99, 123, 777))
    scaled = StandardScaler().fit_transform(
        frame[["recency_days", "frequency_orders", "monetary_log"]].to_numpy(dtype=float))
    expected_mean, expected_std = segment_customers._stability_against_published(
        scaled, 2, segmented["cluster_id"].to_numpy(), [99, 123, 777])
    assert stability_mean == expected_mean
    assert stability_std == expected_std
