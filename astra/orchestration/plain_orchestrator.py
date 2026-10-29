"""
Plain-Python Multi-Agent Admission Orchestrator.
Coordinates candidate evaluation, evidence logging, and administrator policy dispatch.
"""

from typing import Dict, Any, Optional
from astra.pre_admission.monitor_agent import MonitorAgent
from astra.pre_admission.types import TrustEvaluation, AdminDecisionRecord
from astra.admin.policies import AdminPolicy, AutoAdmin
from astra.blockchain.backend import ChainBackend
from astra.network.peer_registry import PeerProfile, PeerRegistry
from astra.network.mempool import MempoolLog
from astra.network.propagation import BlockPropagationLog
from astra.config import ASTRAConfig, DEFAULT_CONFIG


class PlainOrchestrator:
    """Standard robust orchestrator managing the pre-admission workflow."""

    def __init__(self, admin_policy: Optional[AdminPolicy] = None, config: ASTRAConfig = DEFAULT_CONFIG):
        self.config = config
        self.monitor = MonitorAgent(config)
        self.admin = admin_policy or AutoAdmin()

    def run_admission(
        self,
        candidate_id: str,
        wallet_address: str,
        chain: ChainBackend,
        peer_profile: PeerProfile,
        peer_registry: PeerRegistry,
        mempool_log: MempoolLog,
        propagation_log: Optional[BlockPropagationLog] = None,
        candidate_mined_blocks: Optional[list] = None,
        known_exchanges: Optional[list] = None
    ) -> Dict[str, Any]:
        """Executes full pre-admission evaluation and records administrator action."""
        evaluation: TrustEvaluation = self.monitor.evaluate_candidate(
            candidate_id=candidate_id,
            wallet_address=wallet_address,
            chain=chain,
            peer_profile=peer_profile,
            peer_registry=peer_registry,
            mempool_log=mempool_log,
            propagation_log=propagation_log,
            candidate_mined_blocks=candidate_mined_blocks,
            known_exchanges=known_exchanges
        )

        decision: AdminDecisionRecord = self.admin.decide(evaluation)

        return {
            "evaluation": evaluation,
            "decision": decision
        }
