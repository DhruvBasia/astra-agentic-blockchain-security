class TrustCalculator:

    def calculate(self, sybil_result):

        sybil_risk = sybil_result["risk_score"]

        # Convert current Sybil risk into
        # a provisional positive trust value.
        sybil_trust = 1 - sybil_risk

        # Current prototype uses Sybil evidence only.
        provisional_trust = sybil_trust

        if provisional_trust >= 0.70:
            trust_level = "HIGH"

        elif provisional_trust >= 0.40:
            trust_level = "MEDIUM"

        else:
            trust_level = "LOW"

        return {
            "sybil_risk": sybil_risk,
            "provisional_trust": provisional_trust,
            "trust_level": trust_level
        }