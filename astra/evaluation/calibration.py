"""
Threshold and weight calibration for the Trust Factor decision rule.

The chapter chose TV = 0.70 and TF = 0.60*PT + 0.40*(1-AR) by judgement.
This module learns the two free parameters of that rule, the threshold TV and
the PT weight w_pt (the AR weight is 1 - w_pt), on a calibration population
generated from one seed, and then reports how the learned rule performs on
populations generated from other seeds that were never used for fitting.

Objective on the calibration population: balanced accuracy of the formula-only
policy; ties are broken by the widest margin between the threshold and the
nearest candidate, so the chosen rule is the least fragile of the equally good ones.
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Sequence, Tuple

from astra.config import ASTRAConfig, DEFAULT_CONFIG
from astra.evaluation.dataset import (
    CandidateRecord, build_population, classification_metrics, labels, policy_predictions,
)

TV_GRID = [round(0.50 + 0.005 * i, 3) for i in range(81)]        # 0.500 .. 0.900
W_PT_GRID = [round(0.30 + 0.05 * i, 2) for i in range(11)]       # 0.30 .. 0.80


@dataclass
class CalibratedRule:
    tv: float
    w_pt: float
    w_ar: float
    train_balanced_accuracy: float
    train_margin: float


def _margin(records: Sequence[CandidateRecord], tv: float, w_pt: float) -> float:
    return min(abs((w_pt * r.pt + (1.0 - w_pt) * (1.0 - r.ar)) - tv) for r in records)


def search_rule(train: Sequence[CandidateRecord]) -> CalibratedRule:
    y = labels(train)
    best: Tuple[float, float, float, float] = (-1.0, -1.0, 0.70, 0.60)   # (bal_acc, margin, tv, w_pt)
    for w_pt in W_PT_GRID:
        for tv in TV_GRID:
            m = classification_metrics(y, policy_predictions(train, "formula", tv=tv, w_pt=w_pt))
            key = (m["balanced_accuracy"], _margin(train, tv, w_pt), tv, w_pt)
            if key[:2] > best[:2]:
                best = key
    bal_acc, margin, tv, w_pt = best
    return CalibratedRule(tv=tv, w_pt=w_pt, w_ar=round(1.0 - w_pt, 2),
                          train_balanced_accuracy=bal_acc, train_margin=round(margin, 4))


def evaluate_rules(records: Sequence[CandidateRecord], rule: CalibratedRule) -> Dict[str, Dict]:
    y = labels(records)
    return {
        "formula_default": classification_metrics(y, policy_predictions(records, "formula")),
        "escalation_default": classification_metrics(y, policy_predictions(records, "escalation")),
        "formula_calibrated": classification_metrics(y, policy_predictions(records, "formula", tv=rule.tv, w_pt=rule.w_pt)),
        "escalation_calibrated": classification_metrics(y, policy_predictions(records, "escalation", tv=rule.tv, w_pt=rule.w_pt)),
    }


def run_calibration(
    train_seed: int = 7,
    test_seeds: Sequence[int] = (42, 1, 2, 3, 4),
    n: int = 120,
    config: ASTRAConfig = DEFAULT_CONFIG,
    output_dir: str = "results",
    populations: Dict[int, List[CandidateRecord]] = None,
) -> Dict:
    """Fits the rule on `train_seed`, scores it on every test seed, writes JSON + Markdown."""
    populations = populations if populations is not None else {}

    def pop(seed: int) -> List[CandidateRecord]:
        if seed not in populations:
            populations[seed] = build_population(seed=seed, n=n, config=config)
        return populations[seed]

    rule = search_rule(pop(train_seed))
    per_seed = {seed: evaluate_rules(pop(seed), rule) for seed in test_seeds}

    def mean_of(policy: str, metric: str) -> float:
        return round(sum(per_seed[s][policy][metric] for s in test_seeds) / len(test_seeds), 4)

    policies = ("formula_default", "escalation_default", "formula_calibrated", "escalation_calibrated")
    metrics = ("accuracy", "balanced_accuracy", "precision", "recall", "fpr")
    summary = {p: {m: mean_of(p, m) for m in metrics} for p in policies}

    result = {
        "protocol": {
            "train_seed": train_seed, "test_seeds": list(test_seeds), "n_per_population": n,
            "objective": "balanced accuracy of the formula-only policy, ties broken by widest threshold margin",
            "grid": {"tv": [TV_GRID[0], TV_GRID[-1], 0.005], "w_pt": [W_PT_GRID[0], W_PT_GRID[-1], 0.05]},
        },
        "default_rule": {"tv": config.threshold_tv, "w_pt": config.weight_tf_pt, "w_ar": config.weight_tf_ar},
        "calibrated_rule": asdict(rule),
        "per_test_seed": {str(s): per_seed[s] for s in test_seeds},
        "mean_over_test_seeds": summary,
    }

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "calibration.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    with open(os.path.join(output_dir, "calibration.md"), "w", encoding="utf-8") as f:
        f.write(format_markdown(result))
    return result


def format_markdown(result: Dict) -> str:
    rule, default = result["calibrated_rule"], result["default_rule"]
    proto = result["protocol"]
    lines = [
        "# ASTRA Decision-Rule Calibration",
        "",
        f"Fitted on seed {proto['train_seed']} (n = {proto['n_per_population']}); "
        f"scored on unseen seeds {', '.join(map(str, proto['test_seeds']))}.",
        "",
        "| Rule | TV | w_PT | w_AR |",
        "| :--- | ---: | ---: | ---: |",
        f"| Default (judgement) | {default['tv']:.3f} | {default['w_pt']:.2f} | {default['w_ar']:.2f} |",
        f"| Calibrated (learned) | {rule['tv']:.3f} | {rule['w_pt']:.2f} | {rule['w_ar']:.2f} |",
        "",
        f"Calibration-set balanced accuracy: {rule['train_balanced_accuracy']:.1%}, "
        f"threshold margin: {rule['train_margin']:.3f}.",
        "",
        "## Mean over unseen test seeds",
        "",
        "| Policy | Accuracy | Balanced acc. | Precision | Recall | FPR |",
        "| :--- | ---: | ---: | ---: | ---: | ---: |",
    ]
    names = {
        "formula_default": "Formula alone, default rule",
        "escalation_default": "Formula + escalation, default rule",
        "formula_calibrated": "Formula alone, calibrated rule",
        "escalation_calibrated": "Formula + escalation, calibrated rule",
    }
    for key, label in names.items():
        m = result["mean_over_test_seeds"][key]
        lines.append(
            f"| {label} | {m['accuracy']:.1%} | {m['balanced_accuracy']:.1%} | "
            f"{m['precision']:.1%} | {m['recall']:.1%} | {m['fpr']:.1%} |"
        )
    lines += ["", "## Per seed (formula alone, default vs calibrated)", "",
              "| Seed | Default acc. | Default recall | Default FPR | Calibrated acc. | Calibrated recall | Calibrated FPR |",
              "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for seed, res in result["per_test_seed"].items():
        d, c = res["formula_default"], res["formula_calibrated"]
        lines.append(f"| {seed} | {d['accuracy']:.1%} | {d['recall']:.1%} | {d['fpr']:.1%} | "
                     f"{c['accuracy']:.1%} | {c['recall']:.1%} | {c['fpr']:.1%} |")
    lines.append("")
    return "\n".join(lines)
