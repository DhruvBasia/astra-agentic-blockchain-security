"""
STEP 4: Sybil Agent
Role: Evaluates whether a joining node exhibits characteristics of Sybil identities.
Combines:
  1. Static Pre-Admission Indicators (Identity age, on-chain stake, subnet clustering)
  2. Dynamic Behavioural Indicators (Counterparty overlap, interaction concentration, coordinated timing)
Output: Sybil Risk Score (0.0 to 1.0) and explainable reasoning.
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict


class SybilAgent:
    """
    Evaluates Sybil attack risk using identity age, stake commitment,
    subnet collision patterns, and behavioural transaction correlation.
    """
    def __init__(self, name: str = "Sybil Risk Agent"):
        self.name = name

    def evaluate(self, sybil_evidence: Dict[str, Any], known_subnets: Dict[str, int] = None, blockchain_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculates Sybil Risk (0.0 to 1.0).
        Higher = More dangerous.
        """
        age_days = sybil_evidence.get("identity_age_days", 0)
        stake_eth = float(sybil_evidence.get("stake_eth", 0.0))
        subnet = sybil_evidence.get("ip_subnet", "")

        # 1. Identity Age Indicator (Primary Rule from Spec)
        if age_days < 7:
            # Very new identity -> high risk
            age_risk = 0.90 - (age_days * 0.05)
            age_flag = "HIGH_RISK_NEWBORN"
        elif age_days <= 30:
            # 7 to 30 days -> medium risk
            age_risk = 0.50 - ((age_days - 7) * 0.01)
            age_flag = "MEDIUM_RISK_PROBATION"
        else:
            # > 30 days -> low risk
            age_risk = max(0.05, 0.20 - ((age_days - 30) * 0.002))
            age_flag = "LOW_RISK_ESTABLISHED"

        # 2. Economic Stake Indicator (Sybils minimize capital outlay per identity)
        if stake_eth < 0.5:
            stake_risk = 0.85
        elif stake_eth < 5.0:
            stake_risk = 0.40
        else:
            stake_risk = max(0.02, 1.0 / (1.0 + stake_eth * 0.2))

        # 3. Subnet Clustering Indicator (Identity creation pattern)
        known_subnets = known_subnets or {}
        cluster_count = known_subnets.get(subnet, 0)
        if cluster_count >= 3:
            cluster_risk = 0.80
        elif cluster_count >= 1:
            cluster_risk = 0.40
        else:
            cluster_risk = 0.10

        # Baseline static pre-admission risk
        static_risk = (0.50 * age_risk) + (0.30 * stake_risk) + (0.20 * cluster_risk)

        # 4. Optional Behavioural Analysis (Integrated from AgenticAI_Minor)
        behavior_metrics = None
        if blockchain_data and "transactions" in blockchain_data and len(blockchain_data.get("transactions", [])) >= 2:
            behavior_metrics = self.analyze_behavioral_patterns(blockchain_data)
            behavior_risk = behavior_metrics["behavior_risk"]
            # Fuse static indicators (70%) with observed behaviour (30%)
            sybil_risk = (0.70 * static_risk) + (0.30 * behavior_risk)
        else:
            sybil_risk = static_risk

        sybil_risk = round(min(1.0, max(0.0, sybil_risk)), 3)

        explanation = (
            f"Sybil evaluation: Identity age is {age_days} days ({age_flag}, age_risk={round(age_risk, 2)}), "
            f"stake commitment is {stake_eth} ETH (stake_risk={round(stake_risk, 2)}). "
            f"Overall Sybil Risk: {sybil_risk}."
        )

        indicators = {
            "age_days": age_days,
            "age_flag": age_flag,
            "age_risk": round(age_risk, 3),
            "stake_risk": round(stake_risk, 3),
            "cluster_risk": round(cluster_risk, 3)
        }
        if behavior_metrics:
            indicators["behavioral"] = behavior_metrics

        return {
            "agent_name": self.name,
            "sybil_risk": sybil_risk,
            "indicators": indicators,
            "explanation": explanation
        }

    # =====================================================
    # Integrated Behavioural Analysis (AgenticAI_Minor)
    # =====================================================
    def analyze_behavioral_patterns(self, blockchain_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes coordination across accounts based on counterparties,
        concentration, and timestamp synchronization.
        """
        accounts = blockchain_data.get("accounts", [])
        transactions = blockchain_data.get("transactions", [])

        account_transactions = defaultdict(list)
        for tx in transactions:
            sender = tx.get("sender")
            if sender:
                account_transactions[sender].append(tx)

        active_addresses = list(account_transactions.keys())
        if len(active_addresses) < 2:
            return {
                "behavior_risk": 0.0,
                "behavior_similarity": 0.0,
                "interaction_concentration": 0.0,
                "timing_similarity": 0.0,
                "evidence": ["Fewer than two active accounts observed in transaction log."]
            }

        # 1. Counterparty similarity across active accounts
        similarity_scores = []
        for i in range(len(active_addresses)):
            for j in range(i + 1, len(active_addresses)):
                addr_a = active_addresses[i]
                addr_b = active_addresses[j]
                sim = self._calculate_similarity(account_transactions[addr_a], account_transactions[addr_b])
                similarity_scores.append(sim)
        behavior_similarity = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0

        # 2. Interaction concentration
        counterparty_counts = defaultdict(int)
        for tx in transactions:
            receiver = tx.get("receiver")
            if receiver:
                counterparty_counts[receiver] += 1
        total_interactions = sum(counterparty_counts.values())
        concentration = (max(counterparty_counts.values()) / total_interactions) if total_interactions > 0 else 0.0

        # 3. Timing similarity
        timing_similarity = self._calculate_timing_similarity(active_addresses, account_transactions)

        behavior_risk = (0.40 * behavior_similarity) + (0.35 * concentration) + (0.25 * timing_similarity)
        behavior_risk = min(max(behavior_risk, 0.0), 1.0)

        evidence = []
        if behavior_similarity >= 0.70:
            evidence.append("Multiple accounts show highly similar counterparty transaction behaviour.")
        if concentration >= 0.70:
            evidence.append("Transaction activity is tightly concentrated around a single counterparty.")
        if timing_similarity >= 0.70:
            evidence.append("Multiple accounts exhibit synchronized transaction execution timing.")
        if not evidence:
            evidence.append("No strong coordinated multi-account pattern identified.")

        return {
            "behavior_risk": round(behavior_risk, 3),
            "behavior_similarity": round(behavior_similarity, 3),
            "interaction_concentration": round(concentration, 3),
            "timing_similarity": round(timing_similarity, 3),
            "evidence": evidence
        }

    def _calculate_similarity(self, tx_a: List[Dict], tx_b: List[Dict]) -> float:
        if not tx_a or not tx_b:
            return 0.0
        rec_a = {tx["receiver"] for tx in tx_a if tx.get("receiver")}
        rec_b = {tx["receiver"] for tx in tx_b if tx.get("receiver")}
        if not rec_a or not rec_b:
            return 0.0
        intersection = rec_a.intersection(rec_b)
        union = rec_a.union(rec_b)
        receiver_sim = len(intersection) / len(union) if union else 0.0

        avg_a = sum(tx.get("value_eth", 0.0) for tx in tx_a) / len(tx_a)
        avg_b = sum(tx.get("value_eth", 0.0) for tx in tx_b) / len(tx_b)
        max_val = max(avg_a, avg_b, 1e-9)
        val_sim = max(0.0, min(1.0, 1.0 - (abs(avg_a - avg_b) / max_val)))

        return (0.70 * receiver_sim) + (0.30 * val_sim)

    def _calculate_timing_similarity(self, active_addresses: List[str], account_transactions: Dict[str, List]) -> float:
        timestamps = []
        for addr in active_addresses:
            times = [tx["timestamp"] for tx in account_transactions[addr] if tx.get("timestamp") is not None]
            if times:
                timestamps.append(times)
        if len(timestamps) < 2:
            return 0.0
        similarities = []
        for i in range(len(timestamps)):
            for j in range(i + 1, len(timestamps)):
                min_diff = min(abs(t_a - t_b) for t_a in timestamps[i] for t_b in timestamps[j])
                similarities.append(1.0 / (1.0 + min_diff))
        return sum(similarities) / len(similarities) if similarities else 0.0
