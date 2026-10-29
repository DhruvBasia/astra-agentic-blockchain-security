"""
STEP 6: Finney Agent
Role: Evaluates observable indicators associated with Finney double-spending behaviour
(conflicting transactions, block withholding signals, zero-conf settlement attempts).
Output: Finney Risk Score (0.0 to 1.0) and explainable reasoning.
"""

from typing import Dict, Any


class FinneyAgent:
    """
    Evaluates Finney double-spending risk using conflicting spend indicators
    and block withholding telemetry.
    """
    def __init__(self, name: str = "Finney Risk Agent"):
        self.name = name

    def evaluate(self, finney_evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates Finney Risk (0.0 to 1.0).
        Higher = More dangerous.
        """
        has_conflicts = bool(finney_evidence.get("has_conflicting_spends", False))
        is_withholding = bool(finney_evidence.get("withholding_block_flag", False))
        zero_conf = bool(finney_evidence.get("zero_conf_spend_detected", False))

        # 1. Conflicting Spend Detection (UTXO / Nonce collision)
        conflict_risk = 0.92 if has_conflicts else 0.05

        # 2. Block Withholding Timing Pattern
        withhold_risk = 0.88 if is_withholding else 0.04

        # 3. Unconfirmed Settlement Risk
        zero_conf_risk = 0.75 if zero_conf else 0.02

        # Combine Finney Indicators
        if has_conflicts and is_withholding:
            finney_risk = 0.95
            finney_flag = "CRITICAL_FINNEY_DOUBLE_SPEND_SIGNATURE"
        elif has_conflicts or is_withholding:
            finney_risk = 0.75
            finney_flag = "SUSPICIOUS_SPEND_CONCURRENCY"
        else:
            finney_risk = 0.05
            finney_flag = "CLEAN_SETTLEMENT_HISTORY"

        finney_risk = round(min(1.0, max(0.0, finney_risk)), 3)

        explanation = (
            f"Finney evaluation: Conflicting spend detected={has_conflicts} (risk={round(conflict_risk, 2)}), "
            f"block withholding flag={is_withholding} (risk={round(withhold_risk, 2)}). "
            f"Classification: {finney_flag}. Overall Finney Risk: {finney_risk}."
        )

        return {
            "agent_name": self.name,
            "finney_risk": finney_risk,
            "indicators": {
                "has_conflicting_spends": has_conflicts,
                "withholding_block_flag": is_withholding,
                "finney_flag": finney_flag,
                "conflict_risk": round(conflict_risk, 3),
                "withhold_risk": round(withhold_risk, 3)
            },
            "explanation": explanation
        }
