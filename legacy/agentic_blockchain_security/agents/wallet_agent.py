"""
STEP 5: Attack Wallet Agent
Role: Analyzes abnormal or malicious wallet patterns (DoS spam, high failure rate).
Output: Wallet Risk Score (0.0 to 1.0) and explainable reasoning.
"""

from typing import Dict, Any


class WalletAgent:
    """
    Evaluates wallet risk using transaction velocity, failure ratio,
    and historical abuse records.
    """
    def __init__(self, name: str = "Wallet Risk Agent"):
        self.name = name

    def evaluate(self, wallet_evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates Wallet Risk (0.0 to 1.0).
        Higher = More dangerous.
        """
        freq = float(wallet_evidence.get("tx_frequency_per_min", 1.0))
        failed_ratio = float(wallet_evidence.get("failed_tx_ratio", 0.0))
        previously_flagged = bool(wallet_evidence.get("previously_flagged", False))

        # 1. Transaction Frequency / Velocity Burst Indicator
        if freq < 5.0:
            freq_risk = 0.05
            freq_flag = "NORMAL_VELOCITY"
        elif freq <= 20.0:
            freq_risk = 0.35
            freq_flag = "MODERATE_VELOCITY"
        elif freq <= 50.0:
            freq_risk = 0.65
            freq_flag = "HIGH_VELOCITY_SUSPICIOUS"
        else:
            freq_risk = min(1.0, 0.85 + ((freq - 50.0) * 0.003))
            freq_flag = "ABNORMAL_SPAM_BURST"

        # 2. Failed / Reverted Transaction Ratio Indicator
        if failed_ratio < 0.05:
            fail_risk = 0.02
        elif failed_ratio < 0.20:
            fail_risk = 0.30
        else:
            fail_risk = min(1.0, 0.70 + (failed_ratio * 0.25))

        # 3. Previous Blacklist / Abuse Flag
        flag_risk = 0.95 if previously_flagged else 0.05

        # Weighted Wallet Risk Score
        wallet_risk = (0.50 * freq_risk) + (0.30 * fail_risk) + (0.20 * flag_risk)
        wallet_risk = round(min(1.0, max(0.0, wallet_risk)), 3)

        explanation = (
            f"Wallet evaluation: Velocity is {freq} tx/min ({freq_flag}, freq_risk={round(freq_risk, 2)}), "
            f"failed transaction ratio is {round(failed_ratio * 100, 1)}% (fail_risk={round(fail_risk, 2)}), "
            f"flagged_history={previously_flagged}. Overall Wallet Risk: {wallet_risk}."
        )

        return {
            "agent_name": self.name,
            "wallet_risk": wallet_risk,
            "indicators": {
                "tx_frequency_per_min": freq,
                "freq_flag": freq_flag,
                "freq_risk": round(freq_risk, 3),
                "fail_risk": round(fail_risk, 3),
                "flag_risk": round(flag_risk, 3)
            },
            "explanation": explanation
        }
