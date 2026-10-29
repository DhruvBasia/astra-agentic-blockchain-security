"""
Continuous Monitor: Post-Admission Surveillance Engine.
Executes the four continuous monitoring agents (51%, Double-Spend, Selfish Mining, Block Withholding)
across a sliding window of blocks, deduplicates alerts, and tracks attack detection delays.
"""

from typing import List, Dict, Any, Optional, Set
from astra.post_admission.types import PostAdmissionAlert, BlockRecord
from astra.post_admission.attack_51_agent import Attack51Agent
from astra.post_admission.double_spend_agent import DoubleSpendAgent
from astra.post_admission.selfish_mining_agent import SelfishMiningAgent
from astra.post_admission.block_withholding_agent import BlockWithholdingAgent
from astra.network.propagation import BlockPropagationLog
from astra.network.mempool import MempoolLog


class ContinuousMonitor:
    """Orchestrates network-wide post-admission threat detection."""

    def __init__(self, window_blocks: int = 30):
        self.window_blocks = window_blocks
        self.agent_51 = Attack51Agent()
        self.agent_ds = DoubleSpendAgent()
        self.agent_selfish = SelfishMiningAgent()
        self.agent_withholding = BlockWithholdingAgent()

        self._emitted_alerts: List[PostAdmissionAlert] = []
        self._seen_alert_keys: Set[str] = set()
        self._attack_start_time: Optional[float] = None
        self._first_detection_delay: Optional[float] = None

    def set_attack_start(self, timestamp: float) -> None:
        """Records the ground-truth inception time of an attack scenario."""
        self._attack_start_time = timestamp
        self._first_detection_delay = None

    @property
    def detection_delay(self) -> Optional[float]:
        return self._first_detection_delay

    @property
    def alerts(self) -> List[PostAdmissionAlert]:
        return list(self._emitted_alerts)

    def process_new_block(
        self,
        new_block: BlockRecord,
        main_chain: List[BlockRecord],
        orphaned_blocks: List[BlockRecord],
        reorg_history: List[Dict[str, Any]],
        propagation_log: BlockPropagationLog,
        mempool_log: MempoolLog,
        miner_pool_stats: Optional[Dict[str, Dict[str, Any]]] = None,
        linked_sybil_clusters: Optional[Dict[str, Set[str]]] = None,
        censored_addresses: Optional[List[str]] = None,
        pending_mempool_txs: Optional[List[Dict[str, Any]]] = None
    ) -> List[PostAdmissionAlert]:
        """Runs the four agents on sliding window and yields newly discovered alerts."""
        recent_blocks = main_chain[-self.window_blocks:]
        recent_orphans = [
            b for b in orphaned_blocks
            if b.block_number >= (main_chain[-1].block_number - self.window_blocks)
        ]

        # 1. 51% Attack Agent
        alerts_51 = self.agent_51.evaluate(
            recent_blocks=recent_blocks,
            reorg_history=reorg_history,
            linked_sybil_clusters=linked_sybil_clusters,
            censored_addresses=censored_addresses,
            pending_mempool_txs=pending_mempool_txs
        )

        # 2. Double-Spending Agent
        alerts_ds = self.agent_ds.evaluate(
            main_chain=main_chain,
            orphaned_blocks=orphaned_blocks,
            mempool_log=mempool_log
        )

        # 3. Selfish Mining Agent
        alerts_selfish = self.agent_selfish.evaluate(
            recent_main_blocks=recent_blocks,
            recent_orphaned_blocks=recent_orphans
        )

        # 4. Block Withholding Agent
        alerts_bwh = self.agent_withholding.evaluate(
            recent_blocks=recent_blocks,
            propagation_log=propagation_log,
            miner_pool_stats=miner_pool_stats
        )

        all_candidates = alerts_51 + alerts_ds + alerts_selfish + alerts_bwh
        new_alerts: List[PostAdmissionAlert] = []

        for alert in all_candidates:
            key = alert.deduplication_key()
            if key not in self._seen_alert_keys:
                self._seen_alert_keys.add(key)
                self._emitted_alerts.append(alert)
                new_alerts.append(alert)

                # Track detection delay from attack start
                if self._attack_start_time is not None and self._first_detection_delay is None:
                    self._first_detection_delay = max(0.0, alert.timestamp - self._attack_start_time)

        return new_alerts
