"""
Sybil Attack Pre-Admission Agent.
Analyzes funding graphs, burst sibling creation, closed-loop transfers,
counterparty Jaccard similarity, and account freshness.
Uses Noisy-OR combination of indicator scores.
"""

import math
import statistics
from typing import List, Dict, Any, Optional
from astra.pre_admission.types import AgentOutput, IndicatorScore
from astra.blockchain.backend import TxRecord


class SybilAgent:
    """Specialized agent detecting Sybil clusters and pseudonymous identity creation."""

    def __init__(self, name: str = "Sybil Agent"):
        self.name = name

    def evaluate(
        self,
        candidate_address: str,
        all_transactions: List[TxRecord],
        current_time: float,
        known_exchange_addresses: Optional[List[str]] = None
    ) -> AgentOutput:
        c_addr = candidate_address.lower()
        exchanges = set(a.lower() for a in (known_exchange_addresses or []))

        # ------------------------------------------------------------------
        # 1. Feature Extraction: Funding Graph
        # ------------------------------------------------------------------
        incoming_txs = [tx for tx in all_transactions if tx.to.lower() == c_addr and tx.status == 1]
        incoming_txs.sort(key=lambda x: x.timestamp)

        funder = None
        funder_tx = None
        candidate_funding_time = current_time
        candidate_funded_amount = 0.0

        if incoming_txs:
            funder_tx = incoming_txs[0]
            funder = funder_tx.sender.lower()
            candidate_funding_time = funder_tx.timestamp
            candidate_funded_amount = funder_tx.value_eth

        is_exchange_hub = funder in exchanges if funder else False

        # Layered funding: the funder is itself a pass-through account that received its
        # money shortly before and forwarded most of it on. Exchanges and self-funded
        # wallets have no such incoming hop. When a hop is found, siblings are searched
        # over 24 hours instead of 5 minutes, because layering is used to spread funding out.
        funder_is_hop = False
        hop_source = None
        if funder and not is_exchange_hub:
            funder_incoming = [
                tx for tx in all_transactions
                if tx.to.lower() == funder and tx.status == 1 and tx.timestamp <= candidate_funding_time
            ]
            if 1 <= len(funder_incoming) <= 2:
                last_in = max(funder_incoming, key=lambda t: t.timestamp)
                received = sum(t.value_eth for t in funder_incoming)
                forwarded = sum(
                    t.value_eth for t in all_transactions
                    if t.sender.lower() == funder and t.status == 1
                    and last_in.timestamp <= t.timestamp <= last_in.timestamp + 86400.0
                )
                if (candidate_funding_time - last_in.timestamp) <= 86400.0 and received > 0 and forwarded >= 0.40 * received:
                    funder_is_hop = True
                    hop_source = last_in.sender.lower()
        sibling_window = 86400.0 if funder_is_hop else 300.0

        # Find burst siblings: other accounts funded by the same funder inside the window
        burst_siblings = []
        if funder and not is_exchange_hub:
            funder_outgoing = [
                tx for tx in all_transactions
                if tx.sender.lower() == funder and tx.to.lower() != c_addr and tx.status == 1
            ]
            for tx in funder_outgoing:
                if abs(tx.timestamp - candidate_funding_time) <= sibling_window:
                    burst_siblings.append(tx)

        # Coefficient of variation (CV) of amounts among burst-funded accounts
        sibling_amounts = [tx.value_eth for tx in burst_siblings] + ([candidate_funded_amount] if funder else [])
        if len(sibling_amounts) >= 2:
            mean_amt = statistics.mean(sibling_amounts)
            stdev_amt = statistics.stdev(sibling_amounts)
            amount_cv = (stdev_amt / mean_amt) if mean_amt > 1e-9 else 0.0
        else:
            amount_cv = 1.0

        # Burst siblings indicator: requires low CV (near identical funding amounts)
        burst_count = len(burst_siblings) if amount_cv < 0.25 else 0
        if burst_count >= 3:
            s_burst = 0.95
        elif burst_count == 2:
            s_burst = 0.75
        elif burst_count == 1:
            s_burst = 0.80 if funder_is_hop else 0.40   # one sibling through a hop is a deliberate split
        else:
            s_burst = 0.05

        s_layered = 0.90 if funder_is_hop else 0.05

        # ------------------------------------------------------------------
        # 2. Closed-Loop Transfers
        # ------------------------------------------------------------------
        related_accounts = set()
        if funder and not is_exchange_hub:
            related_accounts.add(funder)
        if hop_source:
            related_accounts.add(hop_source)
        for tx in burst_siblings:
            related_accounts.add(tx.to.lower())

        candidate_txs = [tx for tx in all_transactions if tx.sender.lower() == c_addr or tx.to.lower() == c_addr]
        counterparties = set()
        closed_loop_interactions = 0
        for tx in candidate_txs:
            other = tx.to.lower() if tx.sender.lower() == c_addr else tx.sender.lower()
            if other != c_addr:
                counterparties.add(other)
                if other in related_accounts:
                    closed_loop_interactions += 1

        total_interactions = max(1, len(candidate_txs))
        closed_loop_ratio = closed_loop_interactions / total_interactions if counterparties else 0.0
        s_closed = min(1.0, closed_loop_ratio * 1.5)

        # ------------------------------------------------------------------
        # 3. Activity Similarity with Siblings (Jaccard on counterparties)
        # ------------------------------------------------------------------
        similarity_scores = []
        for sib in burst_siblings:
            sib_addr = sib.to.lower()
            sib_cps = {
                (tx.to.lower() if tx.sender.lower() == sib_addr else tx.sender.lower())
                for tx in all_transactions
                if (tx.sender.lower() == sib_addr or tx.to.lower() == sib_addr)
            } - {sib_addr, funder}
            cand_cps = counterparties - {funder}

            union = sib_cps.union(cand_cps)
            if union:
                jaccard = len(sib_cps.intersection(cand_cps)) / len(union)
                similarity_scores.append(jaccard)

        avg_similarity = statistics.mean(similarity_scores) if similarity_scores else 0.0
        s_sim = avg_similarity

        # ------------------------------------------------------------------
        # 4. Account Freshness
        # ------------------------------------------------------------------
        earliest_tx = incoming_txs[0] if incoming_txs else None
        age_days = (current_time - earliest_tx.timestamp) / 86400.0 if earliest_tx else 0.0
        if age_days < 7.0:
            s_fresh = 0.85
        elif age_days <= 30.0:
            s_fresh = 0.40
        else:
            s_fresh = 0.05

        # ------------------------------------------------------------------
        # 5. Noisy-OR Combination
        # risk = 1 - Π(1 - w_i * s_i)
        # ------------------------------------------------------------------
        indicators = [
            IndicatorScore(
                name="Burst Funding Siblings",
                raw_value=f"{burst_count} siblings (CV={amount_cv:.2f})",
                score=s_burst,
                weight=0.35,
                description="Accounts funded by the same upstream entity within 5 minutes with identical amounts"
            ),
            IndicatorScore(
                name="Closed-Loop Transfer Ratio",
                raw_value=f"{closed_loop_ratio:.1%}",
                score=s_closed,
                weight=0.25,
                description="Fraction of candidate transactions circulating exclusively among sibling cluster"
            ),
            IndicatorScore(
                name="Activity Similarity",
                raw_value=f"{avg_similarity:.2f}",
                score=s_sim,
                weight=0.25,
                description="Counterparty Jaccard similarity across sibling accounts"
            ),
            IndicatorScore(
                name="Account Freshness",
                raw_value=f"{age_days:.1f} days",
                score=s_fresh,
                weight=0.15,
                description="Time elapsed since first on-chain funding"
            ),
            IndicatorScore(
                name="Layered Funding",
                raw_value=f"hop via {funder[:10]}... from {hop_source[:10]}..." if funder_is_hop else "direct",
                score=s_layered,
                weight=0.20,
                description="Funding routed through a pass-through account that forwarded most of what it received"
            )
        ]

        # Noisy-OR calculation
        prod = 1.0
        for ind in indicators:
            prod *= (1.0 - ind.weight * ind.score)
        
        # Scale risk so combined indicators reflect full range
        risk = max(0.0, min(1.0, 1.0 - prod))
        # Rescale normalized noisy-OR
        max_possible_prod = 1.0
        for ind in indicators:
            max_possible_prod *= (1.0 - ind.weight * 1.0)
        norm_factor = 1.0 - max_possible_prod
        if norm_factor > 0:
            risk = min(1.0, risk / norm_factor)

        risk = round(risk, 3)

        # ------------------------------------------------------------------
        # 6. Evidence Generation
        # ------------------------------------------------------------------
        evidence = []
        critical = False

        window_label = "24h" if funder_is_hop else "5m"
        if funder and is_exchange_hub:
            evidence.append(f"Funded by known exchange hub {funder[:10]}...; funding-graph clustering not applicable.")
        elif funder and burst_count == 0:
            evidence.append(f"Funded by {funder[:10]}...; no other accounts funded by this source within {window_label}.")
        elif funder:
            evidence.append(f"Common funder identified: {funder[:10]}... (funded {burst_count + 1} accounts within {window_label})")
        else:
            evidence.append("No prior funding transaction detected on ledger.")

        if funder_is_hop:
            evidence.append(
                f"Layered funding: {funder[:10]}... received its funds from {hop_source[:10]}... within 24h "
                f"and forwarded them on (pass-through hop)."
            )
            if burst_count >= 1:
                critical = True

        if burst_count >= 2 or (burst_count >= 1 and funder_is_hop):
            evidence.append(f"Detected {burst_count} sibling account(s) funded with near-identical value (CV={amount_cv:.2f}).")
            if burst_count >= 3:
                critical = True

        if closed_loop_ratio > 0.40:
            evidence.append(f"High closed-loop circular transfer ratio: {closed_loop_ratio:.1%} of transactions are internal.")

        if avg_similarity > 0.60:
            evidence.append(f"High counterparty similarity ({avg_similarity:.2f}) observed across cluster members.")

        if age_days < 7.0:
            evidence.append(f"Candidate account is newborn ({age_days:.1f} days old).")

        summary = f"Sybil Risk: {risk:.2f}. " + (
            f"Detected cluster with {burst_count} burst siblings." if burst_count > 0 else "No significant Sybil clustering."
        )

        return AgentOutput(
            agent_name=self.name,
            risk=risk,
            indicators=indicators,
            evidence=evidence,
            summary=summary,
            critical=critical
        )
