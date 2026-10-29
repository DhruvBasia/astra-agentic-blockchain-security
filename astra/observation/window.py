"""
Observation Window: Sliding observation tracking admitted nodes for their first 8–10 transactions.
Recomputes H, B, and TF after each transaction, raising alerts upon behavioral degradation.
Graduates clean nodes to the continuous monitoring layer.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from astra.blockchain.backend import ChainBackend, TxRecord
from astra.pre_admission.monitor_agent import MonitorAgent
from astra.pre_admission.types import TrustEvaluation, AdminAction
from astra.network.peer_registry import PeerProfile, PeerRegistry
from astra.network.mempool import MempoolLog
from astra.config import ASTRAConfig, DEFAULT_CONFIG


@dataclass
class ObservationStepResult:
    tx_index: int
    tx_hash: str
    ar: float
    pt: float
    tf: float
    tv: float
    h_score: float
    b_score: float
    alert_raised: bool
    alert_reasons: List[str]
    suggested_action: AdminAction
    timestamp: float


@dataclass
class ObservationSession:
    candidate_id: str
    wallet_address: str
    window_size: int = 10
    step_results: List[ObservationStepResult] = field(default_factory=list)
    is_graduated: bool = False
    is_removed: bool = False
    active_alerts: List[str] = field(default_factory=list)

    @property
    def completed_count(self) -> int:
        return len(self.step_results)


class ObservationWindowManager:
    """Manages transaction-by-transaction probation for newly admitted blockchain participants."""

    def __init__(self, monitor_agent: Optional[MonitorAgent] = None, config: ASTRAConfig = DEFAULT_CONFIG):
        self.config = config
        self.monitor = monitor_agent or MonitorAgent(config)

    def start_session(self, candidate_id: str, wallet_address: str, window_size: Optional[int] = None) -> ObservationSession:
        w_size = window_size or self.config.observation_window_size
        return ObservationSession(
            candidate_id=candidate_id,
            wallet_address=wallet_address.lower(),
            window_size=w_size
        )

    def process_transaction(
        self,
        session: ObservationSession,
        tx: TxRecord,
        chain: ChainBackend,
        peer_profile: PeerProfile,
        peer_registry: PeerRegistry,
        mempool_log: MempoolLog,
        known_related_cluster: Optional[List[str]] = None
    ) -> ObservationStepResult:
        if session.is_removed or session.is_graduated:
            raise ValueError("Observation session already finalized.")

        step_idx = len(session.step_results) + 1
        c_addr = session.wallet_address.lower()
        related = set(a.lower() for a in (known_related_cluster or []))

        # Re-evaluate candidate with updated on-chain history
        eval_result: TrustEvaluation = self.monitor.evaluate_candidate(
            candidate_id=session.candidate_id,
            wallet_address=c_addr,
            chain=chain,
            peer_profile=peer_profile,
            peer_registry=peer_registry,
            mempool_log=mempool_log
        )

        alert_reasons = []
        alert_raised = False
        suggested_action = AdminAction.CONTINUE

        # 1. Condition: TF dropped below TV
        if eval_result.tf < self.config.threshold_tv:
            alert_raised = True
            alert_reasons.append(f"Trust Factor degraded: TF ({eval_result.tf:.2f}) dropped below TV ({self.config.threshold_tv:.2f})")
            suggested_action = AdminAction.INVESTIGATE

        # 2. Condition: Specific evidence of conflicting double-spend
        if eval_result.agent_outputs["Finney"].critical:
            alert_raised = True
            alert_reasons.append("Critical: Conflicting double-spend transaction detected during observation window")
            suggested_action = AdminAction.REMOVE

        # 3. Condition: Repeated circular transfers to related cluster accounts
        if tx.to.lower() in related:
            # Check cluster frequency in recent txs
            recent_related = sum(
                1 for prev in session.step_results[-4:]
                if prev.alert_reasons and any("cluster" in r for r in prev.alert_reasons)
            )
            if recent_related >= 1 or tx.value_eth > 0.0:
                alert_raised = True
                alert_reasons.append(f"Suspicious activity: Transaction directed to identified sibling cluster account ({tx.to[:10]}...)")
                suggested_action = AdminAction.INVESTIGATE

        # 4. Condition: Rapid failed transactions
        if tx.status == 0:
            alert_raised = True
            alert_reasons.append("Reverted transaction: Outgoing transfer failed / reverted on-chain")
            if suggested_action == AdminAction.CONTINUE:
                suggested_action = AdminAction.INVESTIGATE

        if eval_result.ar > 0.60:
            suggested_action = AdminAction.REMOVE

        step_res = ObservationStepResult(
            tx_index=step_idx,
            tx_hash=tx.tx_hash,
            ar=eval_result.ar,
            pt=eval_result.pt,
            tf=eval_result.tf,
            tv=self.config.threshold_tv,
            h_score=eval_result.pt_score.h_score,
            b_score=eval_result.pt_score.b_score,
            alert_raised=alert_raised,
            alert_reasons=alert_reasons,
            suggested_action=suggested_action,
            timestamp=chain.now()
        )

        session.step_results.append(step_res)
        if alert_raised:
            session.active_alerts.extend(alert_reasons)

        # Check graduation: node only graduates if window completes cleanly without any alerts
        if len(session.step_results) >= session.window_size:
            if any(r.suggested_action == AdminAction.REMOVE for r in session.step_results):
                session.is_removed = True
                session.is_graduated = False
            elif not session.active_alerts:
                session.is_graduated = True
            else:
                session.is_graduated = False

        return step_res
