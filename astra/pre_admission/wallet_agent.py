"""
Malicious Wallet Pre-Admission Agent.
Analyzes transaction burstiness (inter-arrival < 10s), dusting attacks,
repeated identical transfers, fan-out to fresh addresses, failed transaction ratios,
and robust z-scores (median/MAD) against network baseline.
Uses Noisy-OR combination of indicator scores.
"""

import math
import statistics
from typing import List, Dict, Any, Optional
from astra.pre_admission.types import AgentOutput, IndicatorScore
from astra.blockchain.backend import TxRecord


class WalletAgent:
    """Specialized agent detecting abnormal, DoS-style, and automated bot wallet behaviour."""

    def __init__(self, name: str = "Wallet Agent"):
        self.name = name

    def _robust_z_score(self, value: float, population: List[float]) -> float:
        """Calculates robust z-score using median and Median Absolute Deviation (MAD)."""
        if not population or len(population) < 3:
            return 0.0
        med = statistics.median(population)
        abs_devs = [abs(x - med) for x in population]
        mad = statistics.median(abs_devs)
        if mad < 1e-6:
            return 0.0
        # Normal consistency constant 1.4826
        return (value - med) / (1.4826 * mad)

    @staticmethod
    def _ledger_tx_frequencies(all_transactions: List[TxRecord], exclude: str) -> List[float]:
        """Outgoing transactions per minute for every sender except `exclude`."""
        by_sender: Dict[str, List[float]] = {}
        for tx in all_transactions:
            s = tx.sender.lower()
            if s != exclude:
                by_sender.setdefault(s, []).append(tx.timestamp)
        freqs = []
        for stamps in by_sender.values():
            if len(stamps) >= 2:
                span = max(1.0, max(stamps) - min(stamps))
                freqs.append(len(stamps) / span * 60.0)
        return freqs

    def evaluate(
        self,
        candidate_address: str,
        all_transactions: List[TxRecord],
        current_time: float,
        network_tx_frequencies: Optional[List[float]] = None
    ) -> AgentOutput:
        c_addr = candidate_address.lower()

        # Extract candidate's outgoing transactions
        out_txs = [tx for tx in all_transactions if tx.sender.lower() == c_addr]
        out_txs.sort(key=lambda x: x.timestamp)
        n_out = len(out_txs)

        if n_out == 0:
            # Clean / fresh node with no prior outgoing spam
            return AgentOutput(
                agent_name=self.name,
                risk=0.04,
                indicators=[
                    IndicatorScore(
                        name="Transaction History",
                        raw_value="0 outgoing txs",
                        score=0.04,
                        weight=1.0,
                        description="Account has clean outgoing transaction record"
                    )
                ],
                evidence=["Account has no abnormal transaction history."],
                summary="Wallet Risk: 0.04. Clean, unflagged transaction history.",
                critical=False
            )

        # ------------------------------------------------------------------
        # 1. Burstiness (Inter-arrival time < 10 seconds)
        # ------------------------------------------------------------------
        short_intervals = 0
        intervals = []
        for i in range(1, n_out):
            dt = max(0.0, out_txs[i].timestamp - out_txs[i - 1].timestamp)
            intervals.append(dt)
            if dt < 10.0:
                short_intervals += 1

        burst_ratio = (short_intervals / max(1, n_out - 1)) if n_out > 1 else 0.0
        s_burst = min(1.0, burst_ratio * 1.5)

        # ------------------------------------------------------------------
        # 2. Dust Transaction Ratio (< 0.001 ETH)
        # ------------------------------------------------------------------
        dust_txs = [tx for tx in out_txs if tx.value_eth < 0.001]
        dust_ratio = len(dust_txs) / n_out
        s_dust = min(1.0, dust_ratio * 1.3)

        # ------------------------------------------------------------------
        # 3. Repeated Identical Transfers
        # ------------------------------------------------------------------
        value_counts = {}
        for tx in out_txs:
            val = round(tx.value_eth, 4)
            value_counts[val] = value_counts.get(val, 0) + 1
        max_repeated = max(value_counts.values()) if value_counts else 0
        repeated_ratio = (max_repeated / n_out) if n_out >= 3 else 0.0
        s_repeat = 0.85 if repeated_ratio > 0.60 and n_out >= 4 else (repeated_ratio * 0.5)

        # ------------------------------------------------------------------
        # 4. Fan-Out to Fresh Addresses
        # A destination is fresh when the candidate's transfer is the first time the
        # address appears on the ledger. Paying established counterparties is normal.
        # ------------------------------------------------------------------
        first_seen: Dict[str, float] = {}
        for tx in all_transactions:
            for addr in (tx.sender.lower(), tx.to.lower()):
                if addr and (addr not in first_seen or tx.timestamp < first_seen[addr]):
                    first_seen[addr] = tx.timestamp
        destinations = set(tx.to.lower() for tx in out_txs if tx.to)
        fresh_destinations = {
            d for d in destinations
            if first_seen.get(d, 0.0) >= min(tx.timestamp for tx in out_txs if tx.to.lower() == d)
        }
        fan_out_ratio = len(fresh_destinations) / n_out if n_out > 0 else 0.0
        s_fanout = 0.80 if (fan_out_ratio > 0.50 and n_out >= 5) else (fan_out_ratio * 0.6)

        # ------------------------------------------------------------------
        # 5. Failed Transaction Ratio
        # ------------------------------------------------------------------
        failed_txs = [tx for tx in out_txs if tx.status == 0]
        failed_ratio = len(failed_txs) / n_out
        if failed_ratio >= 0.40:
            s_fail = 0.95
        elif failed_ratio >= 0.20:
            s_fail = 0.60
        else:
            s_fail = failed_ratio * 1.5

        # ------------------------------------------------------------------
        # 6. Robust Z-score (Tx Frequency against Population)
        # ------------------------------------------------------------------
        time_span = max(1.0, out_txs[-1].timestamp - out_txs[0].timestamp) if n_out > 1 else 60.0
        tx_freq = (n_out / time_span) * 60.0  # tx/min

        # Population baseline: per-sender rate of every other account on the ledger
        # with at least two outgoing transfers (median/MAD keeps other bots from
        # dragging the baseline up). Falls back to a fixed baseline on a tiny ledger.
        pop = network_tx_frequencies or self._ledger_tx_frequencies(all_transactions, exclude=c_addr)
        if len(pop) < 3:
            pop = [0.5, 1.0, 1.2, 0.8, 1.5, 2.0, 0.4, 0.9, 1.1]
        z_score = self._robust_z_score(tx_freq, pop)
        s_z = min(1.0, max(0.0, z_score / 4.0))

        # ------------------------------------------------------------------
        # 7. Noisy-OR Combination
        # ------------------------------------------------------------------
        indicators = [
            IndicatorScore(
                name="Burst Inter-Arrival Ratio",
                raw_value=f"{burst_ratio:.1%} (<10s)",
                score=s_burst,
                weight=0.25,
                description="Fraction of outgoing transactions executed under 10 seconds apart"
            ),
            IndicatorScore(
                name="Dust Ratio",
                raw_value=f"{dust_ratio:.1%} (<0.001 ETH)",
                score=s_dust,
                weight=0.15,
                description="High volume micro-transactions below dusting threshold"
            ),
            IndicatorScore(
                name="Repeated Transfers",
                raw_value=f"{max_repeated}x identical amount",
                score=s_repeat,
                weight=0.15,
                description="Repetitive identical transfer values indicating automated scripts"
            ),
            IndicatorScore(
                name="Fan-Out Fresh Ratio",
                raw_value=f"{fan_out_ratio:.1%} ({len(fresh_destinations)} fresh of {len(destinations)} distinct)",
                score=s_fanout,
                weight=0.15,
                description="Rapid dispersal to numerous fresh unestablished addresses"
            ),
            IndicatorScore(
                name="Failed Transaction Ratio",
                raw_value=f"{failed_ratio:.1%} ({len(failed_txs)} failed)",
                score=s_fail,
                weight=0.20,
                description="Proportion of reverted/invalid transactions consuming state without completion"
            ),
            IndicatorScore(
                name="Robust Frequency Z-Score",
                raw_value=f"Z={z_score:.2f} ({tx_freq:.1f} tx/min)",
                score=s_z,
                weight=0.10,
                description="Median/MAD standardized frequency deviation from network baseline"
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
        # 8. Evidence Generation
        # ------------------------------------------------------------------
        evidence = []
        critical = False

        if burst_ratio > 0.50:
            evidence.append(f"Abnormal burst execution: {burst_ratio:.1%} of transactions sent <10s apart.")
        if dust_ratio > 0.50:
            evidence.append(f"Dusting pattern detected: {dust_ratio:.1%} of transactions <0.001 ETH.")
        if failed_ratio > 0.30:
            evidence.append(f"High failure rate: {failed_ratio:.1%} of transactions reverted on-chain.")
            if failed_ratio > 0.60 and n_out >= 5:
                critical = True
        if repeated_ratio > 0.60 and n_out >= 5:
            evidence.append(f"Automated pattern: {max_repeated} transactions with exact identical values.")
        if fan_out_ratio > 0.50 and n_out >= 5:
            evidence.append(f"Fan-out to fresh addresses: {len(fresh_destinations)} destinations had no prior ledger history.")
        if z_score > 3.0:
            evidence.append(
                f"Velocity anomaly: {tx_freq:.1f} tx/min is {z_score:.1f} robust standard deviations above the network median."
            )

        if not evidence:
            evidence.append("Transaction patterns fall within normal behavioral baselines.")

        summary = f"Wallet Risk: {risk:.2f}. " + (
            "Detected bot burst and dusting activity." if risk > 0.50 else "Normal transaction behavior."
        )

        return AgentOutput(
            agent_name=self.name,
            risk=risk,
            indicators=indicators,
            evidence=evidence,
            summary=summary,
            critical=critical
        )
