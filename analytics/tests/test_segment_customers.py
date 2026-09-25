import importlib.util
from pathlib import Path

import pandas as pd
import numpy as np
import pytest
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
    assert labels[2] == "1_recent_more_orders_lower_spend"
    assert labels[1] == "2_recent_fewer_orders_higher_spend"
    assert labels[3] == "3_older_fewer_orders_lower_spend"
    pair = segment_customers._segment_name_mapping(profiles.iloc[[0, 2]])
    assert pair[1] == "1_recent_more_orders_higher_spend"
    assert pair[3] == "2_older_fewer_orders_lower_spend"
    assert all(len(label) <= 40 for label in labels.values())


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
        frame, min_k=2, max_k=2, random_seed=42, stability_seeds=(42, 99, 123, 777), preprocessing="baseline")
    scaled = StandardScaler().fit_transform(
        frame.assign(monetary_log=np.log1p(frame.monetary_total))[["recency_days", "frequency_orders", "monetary_log"]].to_numpy(dtype=float))
    expected_mean, expected_std = segment_customers._stability_against_published(
        scaled, 2, segmented["cluster_id"].to_numpy(), [99, 123, 777])
    assert stability_mean == expected_mean
    assert stability_std == expected_std


@pytest.mark.parametrize("bounds", [(1, 3), (3, 2), (2, 32768), (True, 3)])
def test_candidate_bounds(bounds):
    with pytest.raises(ValueError, match="cluster bounds"):
        segment_customers.fit_candidates(np.ones((5, 3)), *bounds)


def test_infeasible_candidates_record_reasons_without_fitting():
    candidates, labels = segment_customers.fit_candidates(np.ones((3, 3)), 2, 3)
    assert [row["invalid_reason"] for row in candidates] == [
        "k exceeds distinct feature vectors", "k must be smaller than customer count"]
    assert labels == {}


def test_actual_label_collapse_is_invalid(monkeypatch):
    monkeypatch.setattr(segment_customers.KMeans, "fit_predict", lambda self, data: np.zeros(len(data)))
    candidates, labels = segment_customers.fit_candidates(np.arange(18).reshape(6, 3), 2, 2)
    assert candidates[0]["actual_clusters"] == 1
    assert candidates[0]["silhouette"] is None
    assert "actual fitted labels" in candidates[0]["invalid_reason"]
    assert labels == {}


def test_silhouette_sample_with_one_label_records_reason(monkeypatch):
    data = np.arange(15003).reshape(5001, 3)
    labels = np.zeros(len(data), dtype=int)
    labels[np.random.RandomState(42).permutation(len(data))[-1]] = 1
    monkeypatch.setattr(segment_customers.KMeans, "fit_predict", lambda self, values: labels)
    candidates, fitted = segment_customers.fit_candidates(data, 2, 2)
    assert candidates[0]["actual_clusters"] == 2
    assert candidates[0]["invalid_reason"] == "silhouette sample cannot define metric"
    assert fitted == {}


def test_negative_silhouette_is_valid_and_best_candidate_wins(monkeypatch):
    monkeypatch.setattr(segment_customers, "silhouette_score", lambda data, labels, **kw: -0.2 if len(set(labels)) == 2 else -0.1)
    frame = pd.DataFrame({"customer_id": range(12), "recency_days": range(12),
                          "frequency_orders": range(1, 13), "monetary_total": range(20, 32)})
    _, k, score, _, _ = segment_customers.fit_segments(frame, max_k=3, stability_seeds=())
    assert (k, score) == (3, -0.1)


def test_deterministic_assignments_ignore_input_order_and_timestamp():
    frame = pd.DataFrame({"customer_id": range(18), "recency_days": [1, 2, 3, 40, 50, 60] * 3,
                          "frequency_orders": [8, 7, 9, 1, 2, 1] * 3,
                          "monetary_total": [900, 800, 1100, 20, 40, 30] * 3})
    def output(data):
        fitted, k, score, mean, std = segment_customers.fit_segments(data)
        payload = segment_customers.build_output(fitted, "run", "v2", k, score, mean, std)
        payload.pop("generated_at")
        return payload
    assert output(frame) == output(frame.sample(frac=1, random_state=7))


def test_no_valid_candidate_preserves_previous_output(tmp_path, monkeypatch):
    from contextlib import nullcontext
    output = tmp_path / "segments.json"
    output.write_text("previous valid output")
    frame = pd.DataFrame({"customer_id": [1, 2, 3], "recency_days": [1] * 3,
                          "frequency_orders": [1] * 3, "monetary_total": [10] * 3})
    monkeypatch.setattr(segment_customers, "connect", lambda url: nullcontext(None))
    monkeypatch.setattr(segment_customers, "fetch_run", lambda *args: {"namespace": "test", "cutoff": None})
    monkeypatch.setattr(segment_customers, "fetch_rfm", lambda *args: frame)
    assert segment_customers.main(["--run-id", "00000000-0000-0000-0000-000000000001", "--output", str(output)]) == 1
    assert output.read_text() == "previous valid output"
