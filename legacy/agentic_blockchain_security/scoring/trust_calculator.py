"""
STEPS 8, 9, 10: Trust Calculator & Policy Engine
Implements:
1. Attack Level (AL) Aggregation: AL = 0.30(SR) + 0.20(WR) + 0.20(FR) + 0.30(ER)
2. Positive Trust (PT) Score: PT = 0.25(I) + 0.20(T) + 0.20(N) + 0.20(H) + 0.15(B)
3. Final Trust Factor (TF): TF = 0.60(PT) + 0.40(1 - AL)
4. Deterministic Threshold Policy: TV = 0.70 (TF > TV => ACCEPT)
5. Critical Attack Override: If any individual risk >= 0.90 => REJECT immediately.
"""

from typing import Dict, Any


class TrustCalculator:
    """
    Deterministic mathematical scoring engine combining positive trust metrics,
    attack risks, and safety overrides according to project specification.
    """
    def __init__(
        self,
        tv_threshold: float = 0.70,
        critical_risk_threshold: float = 0.90,
        attack_weights: Dict[str, float] = None,
        positive_weights: Dict[str, float] = None
    ):
        self.tv_threshold = tv_threshold
        self.critical_risk_threshold = critical_risk_threshold
        self.attack_weights = attack_weights or {
            "sybil": 0.30,
            "wallet": 0.20,
            "finney": 0.20,
            "eclipse": 0.30
        }
        self.positive_weights = positive_weights or {
            "identity": 0.25,      # I
            "transaction": 0.20,   # T
            "network": 0.20,       # N
            "historical": 0.20,    # H
            "consistency": 0.15    # B
        }

    def compute_attack_level(self, sr: float, wr: float, fr: float, er: float) -> float:
        """
        AL = 0.30(SR) + 0.20(WR) + 0.20(FR) + 0.30(ER)
        """
        al = (
            self.attack_weights["sybil"] * sr +
            self.attack_weights["wallet"] * wr +
            self.attack_weights["finney"] * fr +
            self.attack_weights["eclipse"] * er
        )
        return round(min(1.0, max(0.0, al)), 3)

    def compute_positive_trust(self, i: float, t: float, n: float, h: float, b: float) -> float:
        """
        PT = 0.25(I) + 0.20(T) + 0.20(N) + 0.20(H) + 0.15(B)
        """
        pt = (
            self.positive_weights["identity"] * i +
            self.positive_weights["transaction"] * t +
            self.positive_weights["network"] * n +
            self.positive_weights["historical"] * h +
            self.positive_weights["consistency"] * b
        )
        return round(min(1.0, max(0.0, pt)), 3)

    def compute_trust_factor(self, pt: float, al: float) -> float:
        """
        TF = 0.60(PT) + 0.40(1 - AL)
        """
        tf = (0.60 * pt) + (0.40 * (1.0 - al))
        return round(min(1.0, max(0.0, tf)), 3)

    def evaluate_admission(
        self,
        sr: float,
        wr: float,
        fr: float,
        er: float,
        i: float,
        t: float,
        n: float,
        h: float,
        b: float
    ) -> Dict[str, Any]:
        """
        Executes end-to-end evaluation including Critical Override check.
        """
        # 1. Attack Level
        al = self.compute_attack_level(sr, wr, fr, er)

        # 2. Positive Trust
        pt = self.compute_positive_trust(i, t, n, h, b)

        # 3. Final Trust Factor
        tf = self.compute_trust_factor(pt, al)

        # 4. Critical Attack Override Check
        critical_override = False
        critical_reasons = []
        if sr >= self.critical_risk_threshold:
            critical_override = True
            critical_reasons.append(f"Sybil Risk ({sr}) >= {self.critical_risk_threshold}")
        if wr >= self.critical_risk_threshold:
            critical_override = True
            critical_reasons.append(f"Wallet Risk ({wr}) >= {self.critical_risk_threshold}")
        if fr >= self.critical_risk_threshold:
            critical_override = True
            critical_reasons.append(f"Finney Risk ({fr}) >= {self.critical_risk_threshold}")
        if er >= self.critical_risk_threshold:
            critical_override = True
            critical_reasons.append(f"Eclipse Risk ({er}) >= {self.critical_risk_threshold}")

        # 5. Final Deterministic Policy Decision
        if critical_override:
            decision = "REJECT"
            reason = "CRITICAL_ATTACK_OVERRIDE: " + "; ".join(critical_reasons)
        elif tf > self.tv_threshold:
            decision = "ACCEPT"
            reason = f"Trust Factor ({tf}) > Threshold Value ({self.tv_threshold})"
        else:
            decision = "REJECT"
            reason = f"Trust Factor ({tf}) <= Threshold Value ({self.tv_threshold})"

        return {
            "decision": decision,
            "tf": tf,
            "tv": self.tv_threshold,
            "al": al,
            "pt": pt,
            "risk_scores": {"SR": sr, "WR": wr, "FR": fr, "ER": er},
            "positive_parameters": {"I": i, "T": t, "N": n, "H": h, "B": b},
            "critical_override": critical_override,
            "reason": reason
        }
