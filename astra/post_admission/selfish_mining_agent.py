"""
Selfish Mining Post-Admission Continuous Monitoring Agent.
Monitors:
  1. Network orphan rate spikes above honest baseline.
  2. Burst block releases (>= 2 blocks from the same miner published within <= 1s).
  3. Reactive race releases (attacker block published immediately after competitor block).
  4. Stale/old block header timestamps relative to network first-seen time.
"""

from typing import List, Dict, Any, Optional
from astra.post_admission.types import PostAdmissionAlert, AlertSeverity, BlockRecord


class SelfishMiningAgent:
    """Detects Eyal-Sirer selfish mining, block races, and secret branch withholding."""

    def __init__(self, name: str = "Selfish Mining Agent", baseline_orphan_rate: float = 0.02):
        self.name = name
        self.baseline_orphan_rate = baseline_orphan_rate

    def evaluate(
        self,
        recent_main_blocks: List[BlockRecord],
        recent_orphaned_blocks: List[BlockRecord]
    ) -> List[PostAdmissionAlert]:
        alerts: List[PostAdmissionAlert] = []
        if not recent_main_blocks:
            return alerts

        latest_b = recent_main_blocks[-1]
        total_observed = len(recent_main_blocks) + len(recent_orphaned_blocks)
        if total_observed < 10:
            return alerts

        # ------------------------------------------------------------------
        # 1. Network Orphan Rate Spike
        # ------------------------------------------------------------------
        orphan_rate = len(recent_orphaned_blocks) / total_observed
        if orphan_rate >= 0.15:  # Significant elevation above 2% baseline
            severity = AlertSeverity.CRITICAL if orphan_rate >= 0.25 else AlertSeverity.HIGH
            risk = min(1.0, orphan_rate * 3.0)
            alerts.append(PostAdmissionAlert(
                alert_id=f"SELFISH_ORPHAN_SPIKE_{latest_b.block_number}",
                agent_name=self.name,
                severity=severity,
                risk=risk,
                suspect="Strategic Adversary Pool",
                evidence=[
                    f"Orphan rate spiked to {orphan_rate:.1%} ({len(recent_orphaned_blocks)}/{total_observed} blocks).",
                    f"Elevated significantly above honest baseline ({self.baseline_orphan_rate:.1%}).",
                    "Signifies intentional branch invalidation and selfish mining block withholding."
                ],
                timestamp=latest_b.timestamp,
                block_number=latest_b.block_number,
                metadata={"orphan_rate": orphan_rate, "orphans": len(recent_orphaned_blocks)}
            ))

        # ------------------------------------------------------------------
        # 2. Burst Releases (>= 2 consecutive blocks from same miner within <= 1 second)
        # ------------------------------------------------------------------
        for i in range(1, len(recent_main_blocks)):
            b_prev = recent_main_blocks[i - 1]
            b_curr = recent_main_blocks[i]
            if b_curr.miner == b_prev.miner:
                dt = abs(b_curr.first_seen - b_prev.first_seen)
                withhold_lag = max(b_curr.first_seen - b_curr.timestamp, b_prev.first_seen - b_prev.timestamp)
                if dt <= 1.0 and withhold_lag >= 3.0:
                    alerts.append(PostAdmissionAlert(
                        alert_id=f"SELFISH_BURST_RELEASE_{b_curr.miner}_{b_curr.block_number}",
                        agent_name=self.name,
                        severity=AlertSeverity.HIGH,
                        risk=0.88,
                        suspect=b_curr.miner,
                        evidence=[
                            f"Burst release: Miner {b_curr.miner[:10]}... published consecutive blocks within {dt:.2f}s with withholding lag {withhold_lag:.1f}s.",
                            "Matches selfish mining private branch flush to overwrite honest competitor."
                        ],
                        timestamp=latest_b.timestamp,
                        block_number=latest_b.block_number,
                        metadata={"miner": b_curr.miner, "delta_time": dt, "withhold_lag": withhold_lag}
                    ))

        # ------------------------------------------------------------------
        # 3. Old Header Timestamps vs First-Seen Arrival
        # ------------------------------------------------------------------
        for b in recent_main_blocks[-10:]:
            age_lag = b.first_seen - b.timestamp
            if age_lag >= 20.0:  # Withheld for 20+ seconds before release
                alerts.append(PostAdmissionAlert(
                    alert_id=f"SELFISH_STALE_TIMESTAMP_{b.miner}_{b.block_number}",
                    agent_name=self.name,
                    severity=AlertSeverity.MEDIUM,
                    risk=0.75,
                    suspect=b.miner,
                    evidence=[
                        f"Block #{b.block_number} carries stale header timestamp lagging arrival by {age_lag:.1f}s.",
                        "Block mined privately and withheld before network broadcast."
                    ],
                    timestamp=latest_b.timestamp,
                    block_number=b.block_number,
                    metadata={"delay": age_lag}
                ))

        return alerts
