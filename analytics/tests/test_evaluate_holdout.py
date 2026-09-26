import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ANALYTICS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ANALYTICS))
spec = importlib.util.spec_from_file_location("evaluate_holdout", ANALYTICS / "evaluate_holdout.py")
evaluate_holdout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate_holdout)


def test_holdout_outcomes_aggregate_per_segment_and_skip_window_only_customers():
    segmented = pd.DataFrame({"customer_id": [1, 2, 3, 4],
                              "segment_label": ["a", "a", "b", "b"]})
    outcomes = pd.DataFrame({"customer_id": [1, 2, 3, 99],
                             "window_orders": [2, 1, 1, 5],
                             "window_spend": [300.0, 100.0, 100.0, 999.0]})

    result = evaluate_holdout.holdout_outcomes(segmented, outcomes)

    assert result["segmented_customers"] == 4
    assert result["overall_repurchase_rate"] == 0.75
    assert result["customers_first_ordering_in_window_not_scored"] == 1
    a, b = result["segments"]
    assert (a["segment_label"], a["customers"], a["repurchase_rate"]) == ("a", 2, 1.0)
    assert a["repurchase_lift"] == pytest.approx(1.333, abs=1e-3)
    assert (a["mean_window_orders"], a["mean_window_spend"], a["window_spend_share_percent"]) == (1.5, 200.0, 80.0)
    assert (b["repurchase_rate"], b["mean_window_spend"], b["window_spend_share_percent"]) == (0.5, 50.0, 20.0)


def test_holdout_outcomes_with_no_repurchase_has_no_lift():
    segmented = pd.DataFrame({"customer_id": [1, 2], "segment_label": ["a", "b"]})
    outcomes = pd.DataFrame({"customer_id": pd.Series([], dtype=int),
                             "window_orders": pd.Series([], dtype=int),
                             "window_spend": pd.Series([], dtype=float)})

    result = evaluate_holdout.holdout_outcomes(segmented, outcomes)

    assert result["overall_repurchase_rate"] == 0.0
    assert all(item["repurchase_lift"] is None for item in result["segments"])
    assert all(item["window_spend_share_percent"] == 0.0 for item in result["segments"])


def test_subsample_stability_is_high_for_well_separated_clusters():
    rng = np.random.RandomState(0)
    scaled = np.vstack([rng.normal(-5, 0.3, size=(60, 3)), rng.normal(5, 0.3, size=(60, 3))])
    published = np.array([0] * 60 + [1] * 60)

    result = evaluate_holdout.subsample_stability(scaled, 2, published, repeats=5)

    assert (result["k"], result["repeats"], result["fraction"]) == (2, 5, 0.8)
    assert result["ari_min"] == 1.0
    assert result["ari_mean"] == 1.0


def test_feature_diagnostics_reports_skew_and_pairwise_correlation():
    scaled = np.array([[1.0, 2.0, 3.0], [2.0, 4.0, 1.0], [3.0, 6.0, 2.0], [4.0, 8.0, 9.0]])

    result = evaluate_holdout.feature_diagnostics(scaled)

    assert set(result["skew"]) == {"recency", "frequency", "value"}
    assert result["correlation"]["recency_frequency"] == 1.0
    assert -1.0 <= result["correlation"]["frequency_value"] <= 1.0
