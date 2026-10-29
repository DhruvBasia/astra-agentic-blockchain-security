"""
Double-Spending Post-Admission Continuous Monitoring Agent.
Monitors:
  1. (sender, nonce) conflicts across mempool, main chain, and orphaned blocks.
  2. Confirmed-then-reversed transactions caused by chain reorganizations.
  3. Divergent recipient replacements.
"""

from typing import List, Dict, Any, Optional
from astra.post_admission.types import PostAdmissionAlert, AlertSeverity, BlockRecord
from astra.network.mempool import MempoolLog


class DoubleSpendAgent:
    """Detects multi-layer double-spending across forks and mempools."""

    def __init__(self, name: str = "Double-Spending Agent"):
        self.name = name

    def evaluate(
        self,
        main_chain: List[BlockRecord],
        orphaned_blocks: List[BlockRecord],
        mempool_log: MempoolLog
    ) -> List[PostAdmissionAlert]:
        alerts: List[PostAdmissionAlert] = []
        if not main_chain:
            return alerts

        latest_b = main_chain[-1]

        # ------------------------------------------------------------------
        # 1. Confirmed-then-Reversed Transactions
        # Transactions in orphaned blocks whose inputs or nonces conflict with main chain
        # ------------------------------------------------------------------
        main_txs_by_sn = {}
        for b in main_chain:
            for tx in b.transactions:
                sender = tx.get("sender", "").lower()
                nonce = tx.get("nonce")
                if sender and nonce is not None:
                    main_txs_by_sn[(sender, nonce)] = (tx, b)

        for orb in orphaned_blocks:
            for otx in orb.transactions:
                s = otx.get("sender", "").lower()
                n = otx.get("nonce")
                if s and n is not None:
                    key = (s, n)
                    if key in main_txs_by_sn:
                        mtx, mb = main_txs_by_sn[key]
                        if otx.get("tx_hash") != mtx.get("tx_hash"):
                            # Conflicting transaction successfully replaced via reorg!
                            alerts.append(PostAdmissionAlert(
                                alert_id=f"DS_REORG_REVERSED_{s}_{n}",
                                agent_name=self.name,
                                severity=AlertSeverity.CRITICAL,
                                risk=0.99,
                                suspect=s,
                                evidence=[
                                    f"CRITICAL DOUBLE-SPEND REVERSAL: Sender {s[:10]}... nonce {n}.",
                                    f"Original tx {otx.get('tx_hash')} in orphaned block #{orb.block_number} paying {otx.get('to', '')[:10]}...",
                                    f"Conflicting tx {mtx.get('tx_hash')} mined in main chain block #{mb.block_number} redirecting funds to {mtx.get('to', '')[:10]}...",
                                    "Merchant transaction confirmed then revoked via chain reorganization."
                                ],
                                timestamp=latest_b.timestamp,
                                block_number=latest_b.block_number,
                                metadata={"sender": s, "nonce": n, "orphan_block": orb.block_number}
                            ))

        # ------------------------------------------------------------------
        # 2. Cross-Layer Mempool vs Main Chain Conflicting Replacements
        # ------------------------------------------------------------------
        for (sender, nonce), (mtx, mb) in main_txs_by_sn.items():
            sightings = mempool_log.get_by_sender_nonce(sender, nonce)
            for s in sightings:
                if s.tx_hash.lower() != mtx.get("tx_hash", "").lower():
                    if s.to.lower() != mtx.get("to", "").lower():
                        alerts.append(PostAdmissionAlert(
                            alert_id=f"DS_MEMPOOL_CONFLICT_{sender}_{nonce}",
                            agent_name=self.name,
                            severity=AlertSeverity.HIGH,
                            risk=0.90,
                            suspect=sender,
                            evidence=[
                                f"Mempool conflict: broadcast tx {s.tx_hash[:10]}... to {s.to[:10]}...",
                                f"Conflicting on-chain tx {mtx.get('tx_hash')[:10]}... to {mtx.get('to', '')[:10]}... on block #{mb.block_number}.",
                                "Divergent recipient double-spend replacement detected."
                            ],
                            timestamp=latest_b.timestamp,
                            block_number=latest_b.block_number,
                            metadata={"sender": sender, "nonce": nonce}
                        ))

        return alerts
