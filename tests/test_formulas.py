"""
Unit tests for ASTRA mathematical trust factor formulas and configuration.
"""

import pytest
from astra.config import ASTRAConfig


def test_trust_factor_exact_formula():
    cfg = ASTRAConfig()
    # Test Clean Case: AR=0.0, PT=1.0 -> TF = 0.60(1.0) + 0.40(1 - 0) = 1.00
    ar = 0.0
    pt = 1.0
    tf = round((cfg.weight_tf_pt * pt) + (cfg.weight_tf_ar * (1.0 - ar)), 3)
    assert tf == 1.0

    # Test Worst Case: AR=1.0, PT=0.0 -> TF = 0.60(0.0) + 0.40(0.0) = 0.00
    ar = 1.0
    pt = 0.0
    tf = round((cfg.weight_tf_pt * pt) + (cfg.weight_tf_ar * (1.0 - ar)), 3)
    assert tf == 0.0

    # Test Intermediate Case: AR=0.20, PT=0.80
    # TF = 0.60(0.80) + 0.40(0.80) = 0.48 + 0.32 = 0.80
    ar = 0.20
    pt = 0.80
    tf = round((cfg.weight_tf_pt * pt) + (cfg.weight_tf_ar * (1.0 - ar)), 3)
    assert tf == 0.80
    assert tf >= cfg.threshold_tv  # ACCEPT


def test_attack_risk_formula():
    cfg = ASTRAConfig()
    # S=0.8, W=0.2, F=0.1, E=0.9
    # AR = 0.30(0.8) + 0.20(0.2) + 0.20(0.1) + 0.30(0.9)
    # AR = 0.24 + 0.04 + 0.02 + 0.27 = 0.57
    s, w, f, e = 0.8, 0.2, 0.1, 0.9
    ar = round(cfg.weight_sybil * s + cfg.weight_wallet * w + cfg.weight_finney * f + cfg.weight_eclipse * e, 3)
    assert ar == 0.57


def test_positive_trust_formula():
    cfg = ASTRAConfig()
    # I=0.8, T=0.7, N=0.9, H=0.6, B=0.8
    # PT = 0.25(0.8) + 0.20(0.7) + 0.20(0.9) + 0.20(0.6) + 0.15(0.8)
    # PT = 0.20 + 0.14 + 0.18 + 0.12 + 0.12 = 0.76
    i, t, n, h, b = 0.8, 0.7, 0.9, 0.6, 0.8
    pt = round(
        cfg.weight_pt_i * i
        + cfg.weight_pt_t * t
        + cfg.weight_pt_n * n
        + cfg.weight_pt_h * h
        + cfg.weight_pt_b * b,
        3
    )
    assert pt == 0.76
