"""
Block Withholding Post-Admission Continuous Monitoring Agent.
Evaluates:
  1. Per-miner publication delay against network median.
  2. Fraction of abnormally delayed blocks.
  3. Binomial statistical test for mining pool share withholding (submitting shares without full solutions).
"""

import math
import statistics
from typing import List, Dict, Any, Optional
from astra.post_admission.types import PostAdmissionAlert, AlertSeverity, BlockRecord
from astra.network.propagation import BlockPropagationLog


class BlockWithholdingAgent:
    """Detects delayed block propagation and pool block withholding attacks."""

    def __init__(self, name: str = "Block Withholding Agent"):
        self.name = name

    def _binomial_cdf(self, k: int, n: int, p: float) -> float:
        """Computes cumulative probability P(X <= k) for Binomial(n, p)."""
        if k < 0:
            return 0.0
        if k >= n:
            return 1.0
        cdf = 0.0
        for i in range(k + 1):
            comb = math.comb(n, i)
            cdf += comb * (p ** i) * ((1.0 - p) ** (n - i))
        return min(1.0, max(0.0, cdf))

    def evaluate(
        self,
        recent_blocks: List[BlockRecord],
        propagation_log: BlockPropagationLog,
        miner_pool_stats: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[PostAdmissionAlert]:
        alerts: List[PostAdmissionAlert] = []
        if not recent_blocks:
            return alerts

        latest_b = recent_blocks[-1]
        median_delay = propagation_log.median_delay()

        # ------------------------------------------------------------------
        # 1. Per-Miner Publication Delay vs Network Median
        # ------------------------------------------------------------------
        miner_delays: Dict[str, List[float]] = {}
        for b in recent_blocks:
            prop_rec = propagation_log.get(b.block_number)
            delay = prop_rec.delay if prop_rec else (b.first_seen - b.timestamp)
            miner_delays.setdefault(b.miner, []).append(delay)

        for miner, delays in miner_delays.items():
            if len(delays) >= 2:
                avg_delay = statistics.mean(delays)
                delayed_count = sum(1 for d in delays if d > (median_delay * 4.0) and d > 10.0)
                delayed_fraction = delayed_count / len(delays)

                if delayed_fraction >= 0.40 and avg_delay > 15.0:
                    alerts.append(PostAdmissionAlert(
                        alert_id=f"BWH_DELAY_{miner}",
                        agent_name=self.name,
                        severity=AlertSeverity.HIGH,
                        risk=0.85,
                        suspect=miner,
                        evidence=[
                            f"Miner {miner[:10]}... average publication delay is {avg_delay:.1f}s "
                            f"({avg_delay / max(0.1, median_delay):.1f}x network median of {median_delay:.2f}s).",
                            f"{delayed_fraction:.1%} ({delayed_count}/{len(delays)}) of mined blocks were withheld.",
                            "Systematic latency indicates block withholding strategy."
                        ],
                        timestamp=latest_b.timestamp,
                        block_number=latest_b.block_number,
                        metadata={"avg_delay": avg_delay, "delayed_fraction": delayed_fraction}
                    ))

        # ------------------------------------------------------------------
        # 2. Pool Share vs Found Blocks (Binomial Test)
        # ------------------------------------------------------------------
        if miner_pool_stats:
            for miner, stats in miner_pool_stats.items():
                shares = stats.get("shares_submitted", 0)
                blocks_found = stats.get("blocks_found", 0)
                # If miner submits > 40 shares (expected 4 full blocks), but found <= 0
                share_to_block_ratio = 10.0  # 1 block per 10 shares
                expected_blocks = shares / share_to_block_ratio
                if expected_blocks >= 4.0:
                    p = 1.0 / share_to_block_ratio
                    # Binomial p-value of finding <= blocks_found
                    p_val = self._binomial_cdf(blocks_found, shares, p)
                    if p_val < 0.02:
                        alerts.append(PostAdmissionAlert(
                            alert_id=f"BWH_POOL_SABOTAGE_{miner}",
                            agent_name=self.name,
                            severity=AlertSeverity.CRITICAL,
                            risk=0.92,
                            suspect=miner,
                            evidence=[
                                f"Mining pool sabotage detected: Miner {miner[:10]}... submitted {shares} valid shares.",
                                f"Expected ~{expected_blocks:.1f} full blocks, but reported only {blocks_found} (p-value={p_val:.4f}).",
                                "Statistically significant block discarding (pool withholding attack)."
                            ],
                            timestamp=latest_b.timestamp,
                            block_number=latest_b.block_number,
                            metadata={"shares": shares, "blocks_found": blocks_found, "p_value": p_val}
                        ))

        return alerts
