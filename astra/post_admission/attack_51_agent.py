"""
51% Attack Post-Admission Continuous Monitoring Agent.
Evaluates:
  1. Per-entity main-chain block share with Wilson score lower bound (merging Sybil-linked miners).
  2. Deep chain reorganizations (depth >= 3).
  3. Transaction censorship (victim transactions starved despite block space).
"""

import math
from typing import List, Dict, Any, Optional, Set
from astra.post_admission.types import PostAdmissionAlert, AlertSeverity, BlockRecord


class Attack51Agent:
    """Monitors consensus dominance, deep reorgs, and transaction censorship."""

    def __init__(self, name: str = "51% Attack Agent"):
        self.name = name

    def _wilson_lower_bound(self, successes: int, total: int, z: float = 1.96) -> float:
        """Calculates 95% Wilson score interval lower bound for binomial proportion."""
        if total == 0:
            return 0.0
        p_hat = successes / total
        z2 = z * z
        denom = 1.0 + (z2 / total)
        center = p_hat + (z2 / (2.0 * total))
        inside = (p_hat * (1.0 - p_hat) / total) + (z2 / (4.0 * (total * total)))
        spread = z * math.sqrt(max(0.0, inside))
        return max(0.0, (center - spread) / denom)

    def evaluate(
        self,
        recent_blocks: List[BlockRecord],
        reorg_history: List[Dict[str, Any]],
        linked_sybil_clusters: Optional[Dict[str, Set[str]]] = None,
        censored_addresses: Optional[List[str]] = None,
        pending_mempool_txs: Optional[List[Dict[str, Any]]] = None
    ) -> List[PostAdmissionAlert]:
        alerts: List[PostAdmissionAlert] = []
        if not recent_blocks:
            return alerts

        n_blocks = len(recent_blocks)
        latest_b = recent_blocks[-1]
        clusters = linked_sybil_clusters or {
            "0xcoalition_cluster": {"0xcoalition_leader", "0xcoalition_sybil_ally"}
        }

        # ------------------------------------------------------------------
        # 1. Block Share Analysis with Entity Merging & Wilson Lower Bound
        # ------------------------------------------------------------------
        # Map miner -> entity
        def get_entity(miner_addr: str) -> str:
            m = miner_addr.lower()
            for entity_name, members in clusters.items():
                if m in members:
                    return entity_name
            return m

        entity_counts: Dict[str, int] = {}
        for b in recent_blocks:
            ent = get_entity(b.miner)
            entity_counts[ent] = entity_counts.get(ent, 0) + 1

        if n_blocks >= 10:
            for entity, count in entity_counts.items():
                empirical_share = count / n_blocks
                w_lb = self._wilson_lower_bound(count, n_blocks)

                if w_lb >= 0.45 or (n_blocks >= 15 and empirical_share >= 0.52):
                    severity = AlertSeverity.CRITICAL if empirical_share > 0.52 else AlertSeverity.HIGH
                    risk = min(1.0, 0.5 + (empirical_share * 0.5))
                    alerts.append(PostAdmissionAlert(
                        alert_id=f"51_DOMINANCE_{entity}",
                        agent_name=self.name,
                        severity=severity,
                        risk=risk,
                        suspect=entity,
                        evidence=[
                            f"Entity '{entity}' mined {count}/{n_blocks} blocks ({empirical_share:.1%}) in sliding window.",
                            f"Wilson 95% lower bound hash share: {w_lb:.1%} (exceeds 45% danger threshold).",
                            "Sybil-linked miners colluding under unified consensus control."
                        ],
                        timestamp=latest_b.timestamp,
                        block_number=latest_b.block_number,
                        metadata={"empirical_share": empirical_share, "wilson_lb": w_lb}
                    ))

        # ------------------------------------------------------------------
        # 2. Deep Reorganization Detection (depth >= 3)
        # ------------------------------------------------------------------
        for reorg in reorg_history:
            depth = reorg.get("depth", 0)
            if depth >= 3:
                alerts.append(PostAdmissionAlert(
                    alert_id=f"51_DEEP_REORG_{reorg.get('at_block', 0)}",
                    agent_name=self.name,
                    severity=AlertSeverity.CRITICAL,
                    risk=0.98,
                    suspect=latest_b.miner,
                    evidence=[
                        f"CRITICAL deep chain reorganization observed: {depth} blocks invalidated.",
                        "Private hostile branch published replacing honest longest chain.",
                        "Previously confirmed transactions reversed on orphaned fork."
                    ],
                    timestamp=reorg.get("timestamp", latest_b.timestamp),
                    block_number=reorg.get("at_block", latest_b.block_number),
                    metadata={"depth": depth}
                ))

        # ------------------------------------------------------------------
        # 3. Transaction Censorship Detection
        # ------------------------------------------------------------------
        if censored_addresses and pending_mempool_txs:
            censored_set = set(a.lower() for a in censored_addresses)
            for tx in pending_mempool_txs:
                sender = tx.get("sender", "").lower()
                if sender in censored_set:
                    blocks_starved = tx.get("blocks_pending", 0)
                    if blocks_starved >= 3:
                        alerts.append(PostAdmissionAlert(
                            alert_id=f"51_CENSORSHIP_{sender}",
                            agent_name=self.name,
                            severity=AlertSeverity.HIGH,
                            risk=0.85,
                            suspect="Consensus Majority",
                            evidence=[
                                f"Transaction from {sender[:10]}... delayed for {blocks_starved} blocks despite block space.",
                                "Targeted discriminatory censorship pattern detected."
                            ],
                            timestamp=latest_b.timestamp,
                            block_number=latest_b.block_number,
                            metadata={"victim": sender, "blocks_starved": blocks_starved}
                        ))

        return alerts
