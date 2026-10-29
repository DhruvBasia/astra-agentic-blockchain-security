"""
Learned-classifier baseline for the ASTRA admission decision.

Compares the hand-written Trust Factor rule with three scikit-learn models
trained on the same evidence the agents produce:

  Logistic regression  - supervised, linear; its coefficients on the agent-level
                         features are directly comparable to the hand weights.
  Random forest        - supervised, non-linear.
  Isolation forest     - unsupervised anomaly detector; sees no labels at all.

Two feature views:
  agent-level   S, W, F, E risks and the I, T, N, H, B trust components (9 features)
  indicator-level  every indicator score produced by the four agents, plus the above

Two protocols, both on the simulated ledger:
  cross-validation  stratified 5-fold on the seed-42 population
  cross-seed        train on a seed-7 population, test on the seed-42 population
"""

import json
import os
from typing import Dict, List, Sequence

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from astra.config import ASTRAConfig, DEFAULT_CONFIG
from astra.evaluation.dataset import (
    AGENT_LEVEL_FEATURES, CandidateRecord, build_population, classification_metrics,
    feature_matrix, indicator_feature_names, labels, policy_predictions,
)


def _models(random_state: int, contamination: float) -> Dict[str, object]:
    return {
        "logistic_regression": make_pipeline(
            StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=2000, random_state=random_state)
        ),
        "random_forest": RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=random_state),
        "isolation_forest": IsolationForest(n_estimators=300, contamination=contamination, random_state=random_state),
    }


def _fit_predict(name: str, model, X_train, y_train, X_test) -> List[int]:
    if name == "isolation_forest":
        model.fit(X_train)                                  # unsupervised: labels never seen
        return [1 if p == -1 else 0 for p in model.predict(X_test)]
    model.fit(X_train, y_train)
    return [int(p) for p in model.predict(X_test)]


def _learned_weights(X: np.ndarray, y: Sequence[int], names: Sequence[str], random_state: int) -> Dict[str, float]:
    """Standardised logistic-regression coefficients, sign flipped so positive = more trust."""
    pipe = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=2000, random_state=random_state))
    pipe.fit(X, y)
    coef = pipe.named_steps["logisticregression"].coef_[0]
    return {name: round(float(-c), 3) for name, c in zip(names, coef)}


def run_ml_baseline(
    seed: int = 42,
    train_seed: int = 7,
    n: int = 120,
    folds: int = 5,
    config: ASTRAConfig = DEFAULT_CONFIG,
    output_dir: str = "results",
    populations: Dict[int, List[CandidateRecord]] = None,
) -> Dict:
    populations = populations if populations is not None else {}

    def pop(s: int) -> List[CandidateRecord]:
        if s not in populations:
            populations[s] = build_population(seed=s, n=n, config=config)
        return populations[s]

    test_pop, train_pop = pop(seed), pop(train_seed)
    y_test, y_train = labels(test_pop), labels(train_pop)
    # Attacker share of the training population, capped at the 0.5 scikit-learn allows.
    contamination = min(0.5, round(sum(y_train) / len(y_train), 3))

    views = {
        "agent_level": list(AGENT_LEVEL_FEATURES),
        "indicator_level": indicator_feature_names(train_pop + test_pop),
    }

    results: Dict[str, Dict] = {"cross_validation": {}, "cross_seed": {}}
    for view, names in views.items():
        X_test = np.array(feature_matrix(test_pop, names))
        X_train = np.array(feature_matrix(train_pop, names))

        # Protocol 1: stratified k-fold on the test-seed population
        cv_preds = {m: [0] * len(test_pop) for m in _models(seed, contamination)}
        skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
        for fold_train, fold_test in skf.split(X_test, y_test):
            for name, model in _models(seed, contamination).items():
                preds = _fit_predict(name, model, X_test[fold_train], [y_test[i] for i in fold_train], X_test[fold_test])
                for i, p in zip(fold_test, preds):
                    cv_preds[name][i] = p
        results["cross_validation"][view] = {m: classification_metrics(y_test, p) for m, p in cv_preds.items()}

        # Protocol 2: train on one seed, test on another
        results["cross_seed"][view] = {
            name: classification_metrics(y_test, _fit_predict(name, model, X_train, y_train, X_test))
            for name, model in _models(seed, contamination).items()
        }

    formula = {
        "formula_default": classification_metrics(y_test, policy_predictions(test_pop, "formula")),
        "escalation_default": classification_metrics(y_test, policy_predictions(test_pop, "escalation")),
    }

    learned = _learned_weights(np.array(feature_matrix(train_pop, views["agent_level"])), y_train,
                               views["agent_level"], seed)

    out = {
        "protocol": {
            "test_seed": seed, "train_seed": train_seed, "n_per_population": n, "cv_folds": folds,
            "isolation_forest_contamination": contamination,
            "feature_views": {k: len(v) for k, v in views.items()},
        },
        "formula_on_test_population": formula,
        "models": results,
        "learned_agent_weights": {
            "note": "Standardised logistic-regression coefficients fitted on the training seed; "
                    "positive favours admission. Compare signs and relative sizes with the hand weights.",
            "hand_weights": {
                "risk:Sybil": -config.weight_sybil, "risk:Wallet": -config.weight_wallet,
                "risk:Finney": -config.weight_finney, "risk:Eclipse": -config.weight_eclipse,
                "pt:I": config.weight_pt_i, "pt:T": config.weight_pt_t, "pt:N": config.weight_pt_n,
                "pt:H": config.weight_pt_h, "pt:B": config.weight_pt_b,
            },
            "learned": learned,
        },
    }

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "ml_baseline.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    with open(os.path.join(output_dir, "ml_baseline.md"), "w", encoding="utf-8") as f:
        f.write(format_markdown(out))
    return out


MODEL_LABELS = {
    "logistic_regression": "Logistic regression",
    "random_forest": "Random forest",
    "isolation_forest": "Isolation forest (unsupervised)",
}


def _row(label: str, m: Dict) -> str:
    return (f"| {label} | {m['accuracy']:.1%} | {m['balanced_accuracy']:.1%} | {m['precision']:.1%} | "
            f"{m['recall']:.1%} | {m['fpr']:.1%} |")


def format_markdown(out: Dict) -> str:
    p = out["protocol"]
    header = ["| Decision rule | Accuracy | Balanced acc. | Precision | Recall | FPR |",
              "| :--- | ---: | ---: | ---: | ---: | ---: |"]
    lines = [
        "# ASTRA Learned-Classifier Baseline",
        "",
        f"Test population: seed {p['test_seed']} (n = {p['n_per_population']}). "
        f"Cross-seed training population: seed {p['train_seed']}. "
        f"Cross-validation: stratified {p['cv_folds']}-fold on the test population. "
        f"Isolation-forest contamination: {p['isolation_forest_contamination']}.",
        "",
        "## Hand-written rule on the test population", "",
    ] + header + [
        _row("Formula alone (TF >= TV)", out["formula_on_test_population"]["formula_default"]),
        _row("Formula + escalation", out["formula_on_test_population"]["escalation_default"]),
    ]
    for proto, title in (("cross_validation", "Cross-validation on the test population"),
                         ("cross_seed", "Trained on another seed, tested on the test population")):
        lines += ["", f"## {title}"]
        for view, label in (("agent_level", "agent-level features (9)"), ("indicator_level", "indicator-level features")):
            lines += ["", f"### {label}", ""] + header
            for model, m in out["models"][proto][view].items():
                lines.append(_row(MODEL_LABELS[model], m))
    lw = out["learned_agent_weights"]
    lines += ["", "## Hand weights vs learned weights (agent-level)", "",
              "| Feature | Hand weight | Learned coefficient |", "| :--- | ---: | ---: |"]
    for name in lw["hand_weights"]:
        lines.append(f"| {name} | {lw['hand_weights'][name]:+.2f} | {lw['learned'][name]:+.3f} |")
    lines += ["", lw["note"], ""]
    return "\n".join(lines)
