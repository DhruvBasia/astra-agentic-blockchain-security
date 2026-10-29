"""
Smoke tests for the shared benchmark dataset, the decision-rule calibration and
the learned-classifier baseline, on small populations so they run quickly.
"""

import json
import os
from astra.evaluation.dataset import (
    AGENT_LEVEL_FEATURES, build_population, classification_metrics, feature_matrix,
    indicator_feature_names, labels, policy_predictions,
)
from astra.evaluation.calibration import run_calibration, search_rule
from astra.evaluation.ml_baseline import run_ml_baseline


def test_population_records_are_complete():
    pop = build_population(seed=5, n=30)
    assert len(pop) == sum(max(1, int(round(c * 30 / 125.0))) for _, c in __import__("astra.evaluation.dataset", fromlist=["PROFILE_MIX"]).PROFILE_MIX)
    assert any(r.is_attacker for r in pop) and any(not r.is_attacker for r in pop)
    names = indicator_feature_names(pop)
    assert names[:9] == AGENT_LEVEL_FEATURES
    X = feature_matrix(pop, names)
    assert all(len(row) == len(names) for row in X)
    assert all(0.0 <= v <= 1.0 for row in X for v in row)
    assert len(labels(pop)) == len(pop)


def test_policy_predictions_match_recorded_actions():
    pop = build_population(seed=5, n=30)
    for r, flagged in zip(pop, policy_predictions(pop, "formula")):
        assert flagged == (1 if r.action_formula.value == "REJECT" else 0)
    m = classification_metrics([1, 1, 0, 0], [1, 0, 0, 1])
    assert m["confusion_matrix"] == {"TP": 1, "FP": 1, "TN": 1, "FN": 1}
    assert m["recall"] == 0.5 and m["fpr"] == 0.5


def test_calibration_fits_and_writes(tmp_path):
    pop = build_population(seed=5, n=30)
    rule = search_rule(pop)
    assert 0.5 <= rule.tv <= 0.9 and 0.3 <= rule.w_pt <= 0.8
    assert abs(rule.w_pt + rule.w_ar - 1.0) < 1e-9

    out = run_calibration(train_seed=5, test_seeds=(6,), n=30, output_dir=str(tmp_path))
    assert os.path.isfile(os.path.join(tmp_path, "calibration.json"))
    assert os.path.isfile(os.path.join(tmp_path, "calibration.md"))
    assert set(out["mean_over_test_seeds"]) == {
        "formula_default", "escalation_default", "formula_calibrated", "escalation_calibrated"
    }


def test_ml_baseline_runs_and_writes(tmp_path):
    out = run_ml_baseline(seed=5, train_seed=6, n=40, folds=3, output_dir=str(tmp_path))
    with open(os.path.join(tmp_path, "ml_baseline.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    for proto in ("cross_validation", "cross_seed"):
        for view in ("agent_level", "indicator_level"):
            for model in ("logistic_regression", "random_forest", "isolation_forest"):
                m = data["models"][proto][view][model]
                assert 0.0 <= m["accuracy"] <= 1.0 and 0.0 <= m["recall"] <= 1.0
    assert set(out["learned_agent_weights"]["learned"]) == set(AGENT_LEVEL_FEATURES)
