"""
Finney Attack Pre-Admission Agent.
Evaluates conflicting mempool sightings vs on-chain transactions by (sender, nonce).
Distinguishes benign fee bumps (same recipient, higher fee) from malicious double-spends.
Detects hidden/pre-mined block withholding anomalies and abnormal publication delay.
Uses Noisy-OR combination of indicator scores.
"""

from typing import List, Dict, Any, Optional
from astra.pre_admission.types import AgentOutput, IndicatorScore
from astra.blockchain.backend import TxRecord
from astra.network.mempool import MempoolLog, MempoolSighting
from astra.network.propagation import BlockPropagationLog


class FinneyAgent:
    """Specialized agent detecting Finney double-spending and withheld block releases."""

    def __init__(self, name: str = "Finney Agent"):
        self.name = name

    def evaluate(
        self,
        candidate_address: str,
        on_chain_txs: List[TxRecord],
        mempool_log: MempoolLog,
        propagation_log: Optional[BlockPropagationLog] = None,
        candidate_mined_blocks: Optional[List[int]] = None
    ) -> AgentOutput:
        c_addr = candidate_address.lower()
        mined_blocks = set(candidate_mined_blocks or [])

        # Filter candidate's on-chain transactions
        cand_on_chain = [tx for tx in on_chain_txs if tx.sender.lower() == c_addr]
        
        # ------------------------------------------------------------------
        # 1. Match Mempool Sightings against On-Chain Txs by (sender, nonce)
        # ------------------------------------------------------------------
        has_double_spend_conflict = False
        is_benign_fee_bump = False
        conflict_details = []

        for on_chain_tx in cand_on_chain:
            sightings = mempool_log.get_by_sender_nonce(c_addr, on_chain_tx.nonce)
            for s in sightings:
                # If transaction hash differs:
                if s.tx_hash.lower() != on_chain_tx.tx_hash.lower():
                    # Check recipient
                    if s.to.lower() != on_chain_tx.to.lower():
                        # DIFFERENT RECIPIENT -> Malicious Double Spend!
                        has_double_spend_conflict = True
                        conflict_details.append(
                            f"Conflicting nonce {on_chain_tx.nonce}: Mempool payment to {s.to[:10]}... "
                            f"vs on-chain spend to {on_chain_tx.to[:10]}..."
                        )
                    else:
                        # SAME RECIPIENT -> Check if it is a fee bump
                        if s.fee_eth < on_chain_tx.fee_eth or on_chain_tx.fee_eth < s.fee_eth:
                            is_benign_fee_bump = True

        s_conflict = 0.95 if has_double_spend_conflict else (0.10 if is_benign_fee_bump else 0.05)

        # ------------------------------------------------------------------
        # 2. Hidden-Block Withholding Indicator
        # Candidate mined the block holding the conflicting tx,
        # block timestamp is earlier than the merchant-payment sighting,
        # but first_seen is later (withheld then published).
        # ------------------------------------------------------------------
        hidden_block_detected = False
        max_withholding_delay = 0.0

        if has_double_spend_conflict and propagation_log:
            for on_chain_tx in cand_on_chain:
                if on_chain_tx.block_number in mined_blocks or on_chain_tx.block_number is not None:
                    prop_rec = propagation_log.get(on_chain_tx.block_number)
                    if prop_rec:
                        sightings = mempool_log.get_by_sender_nonce(c_addr, on_chain_tx.nonce)
                        for s in sightings:
                            if s.tx_hash.lower() != on_chain_tx.tx_hash.lower():
                                # Withholding signature: block timestamp <= sighting time, but first_seen > sighting time + 5s
                                if prop_rec.block_timestamp <= (s.seen_at + 2.0) and prop_rec.first_seen > s.seen_at:
                                    delay = prop_rec.first_seen - prop_rec.block_timestamp
                                    if delay > 5.0:
                                        hidden_block_detected = True
                                        max_withholding_delay = max(max_withholding_delay, delay)

        s_hidden = 0.95 if hidden_block_detected else (0.50 if has_double_spend_conflict else 0.05)

        # ------------------------------------------------------------------
        # 3. Abnormal Publication Delay against Baseline
        # ------------------------------------------------------------------
        baseline_delay = propagation_log.median_delay() if propagation_log else 0.8
        delay_ratio = (max_withholding_delay / baseline_delay) if baseline_delay > 0 else 1.0
        if delay_ratio > 10.0:
            s_delay = 0.90
        elif delay_ratio > 4.0:
            s_delay = 0.60
        else:
            s_delay = 0.05

        # ------------------------------------------------------------------
        # 4. Noisy-OR Combination
        # ------------------------------------------------------------------
        indicators = [
            IndicatorScore(
                name="Mempool Conflict Status",
                raw_value="DOUBLE-SPEND" if has_double_spend_conflict else ("FEE-BUMP" if is_benign_fee_bump else "CLEAN"),
                score=s_conflict,
                weight=0.45,
                description="Presence of conflicting mempool transactions with different destination addresses"
            ),
            IndicatorScore(
                name="Hidden Block Withholding",
                raw_value=f"{max_withholding_delay:.1f}s withheld" if hidden_block_detected else "NONE",
                score=s_hidden,
                weight=0.35,
                description="Block containing self-transfer was withheld prior to merchant payment release"
            ),
            IndicatorScore(
                name="Propagation Delay Anomaly",
                raw_value=f"{delay_ratio:.1f}x baseline",
                score=s_delay,
                weight=0.20,
                description="Block delivery arrival lag relative to network propagation median"
            )
        ]

        prod = 1.0
        for ind in indicators:
            prod *= (1.0 - ind.weight * ind.score)
        risk = max(0.0, min(1.0, 1.0 - prod))

        max_possible_prod = 1.0
        for ind in indicators:
            max_possible_prod *= (1.0 - ind.weight * 1.0)
        norm_factor = 1.0 - max_possible_prod
        if norm_factor > 0:
            risk = min(1.0, risk / norm_factor)

        risk = round(risk, 3)

        # ------------------------------------------------------------------
        # 5. Evidence Generation
        # ------------------------------------------------------------------
        evidence = []
        critical = False

        if has_double_spend_conflict:
            critical = True
            evidence.extend(conflict_details)
            evidence.append("CRITICAL: Conflicting transaction detected with divergent destination address.")

        if hidden_block_detected:
            critical = True
            evidence.append(
                f"Secret mining pattern: Block mined by candidate held private for {max_withholding_delay:.1f}s "
                f"before broadcast, matching Finney attack profile."
            )

        if is_benign_fee_bump and not has_double_spend_conflict:
            evidence.append("Observed benign Replace-By-Fee (RBF) fee escalation to identical counterparty.")

        if not evidence:
            evidence.append("No conflicting mempool sightings or withheld block propagation anomalies.")

        summary = f"Finney Risk: {risk:.2f}. " + (
            "CRITICAL Finney double-spend and block withholding signature detected!" if critical
            else "Clean transaction settlement record."
        )

        return AgentOutput(
            agent_name=self.name,
            risk=risk,
            indicators=indicators,
            evidence=evidence,
            summary=summary,
            critical=critical
        )
