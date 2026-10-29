"""
Monitor Agent: Pre-Admission Orchestrator and Trust Aggregator.
Dispatches specialized agents (Sybil, Wallet, Finney, Eclipse),
calculates Positive Trust (PT) and Attack Risk (AR),
computes overall Trust Factor (TF), and attaches escalation flags for human review.
"""

from typing import List, Dict, Any, Optional
from astra.pre_admission.types import (
    AgentOutput,
    TrustEvaluation,
    Recommendation,
    PositiveTrustScore
)
from astra.pre_admission.sybil_agent import SybilAgent
from astra.pre_admission.wallet_agent import WalletAgent
from astra.pre_admission.finney_agent import FinneyAgent
from astra.pre_admission.eclipse_agent import EclipseAgent
from astra.pre_admission.positive_trust import PositiveTrustEngine
from astra.blockchain.backend import ChainBackend, TxRecord
from astra.network.peer_registry import PeerProfile, PeerRegistry
from astra.network.mempool import MempoolLog
from astra.network.propagation import BlockPropagationLog
from astra.config import ASTRAConfig, DEFAULT_CONFIG


class MonitorAgent:
    """Orchestrates evidence collection, multi-agent dispatch, and trust computation."""

    def __init__(self, config: ASTRAConfig = DEFAULT_CONFIG):
        self.config = config
        self.sybil_agent = SybilAgent()
        self.wallet_agent = WalletAgent()
        self.finney_agent = FinneyAgent()
        self.eclipse_agent = EclipseAgent()
        self.pt_engine = PositiveTrustEngine(config)

    def evaluate_candidate(
        self,
        candidate_id: str,
        wallet_address: str,
        chain: ChainBackend,
        peer_profile: PeerProfile,
        peer_registry: PeerRegistry,
        mempool_log: MempoolLog,
        propagation_log: Optional[BlockPropagationLog] = None,
        candidate_mined_blocks: Optional[List[int]] = None,
        known_exchanges: Optional[List[str]] = None,
        network_tx_frequencies: Optional[List[float]] = None,
        prior_alerts_count: int = 0
    ) -> TrustEvaluation:
        c_addr = wallet_address.lower()
        all_txs = chain.all_transactions()
        current_time = chain.now()

        # ------------------------------------------------------------------
        # 1. Dispatch Specialized Pre-Admission Agents
        # ------------------------------------------------------------------
        sybil_out: AgentOutput = self.sybil_agent.evaluate(
            candidate_address=c_addr,
            all_transactions=all_txs,
            current_time=current_time,
            known_exchange_addresses=known_exchanges
        )

        wallet_out: AgentOutput = self.wallet_agent.evaluate(
            candidate_address=c_addr,
            all_transactions=all_txs,
            current_time=current_time,
            network_tx_frequencies=network_tx_frequencies
        )

        finney_out: AgentOutput = self.finney_agent.evaluate(
            candidate_address=c_addr,
            on_chain_txs=all_txs,
            mempool_log=mempool_log,
            propagation_log=propagation_log,
            candidate_mined_blocks=candidate_mined_blocks
        )

        eclipse_out: AgentOutput = self.eclipse_agent.evaluate(
            peer_profile=peer_profile,
            peer_registry=peer_registry,
            current_tip=chain.block_number()
        )

        return self.aggregate(
            candidate_id=candidate_id,
            wallet_address=c_addr,
            agent_outputs={
                "Sybil": sybil_out,
                "Wallet": wallet_out,
                "Finney": finney_out,
                "Eclipse": eclipse_out
            },
            all_transactions=all_txs,
            current_time=current_time,
            peer_profile=peer_profile,
            peer_registry=peer_registry,
            chain_info=chain.info(),
            known_exchanges=known_exchanges,
            prior_alerts_count=prior_alerts_count
        )

    def aggregate(
        self,
        candidate_id: str,
        wallet_address: str,
        agent_outputs: Dict[str, AgentOutput],
        all_transactions: List[TxRecord],
        current_time: float,
        peer_profile: PeerProfile,
        peer_registry: PeerRegistry,
        chain_info: Optional[Dict[str, Any]] = None,
        known_exchanges: Optional[List[str]] = None,
        prior_alerts_count: int = 0
    ) -> TrustEvaluation:
        """Combines the four agent outputs into AR, PT, TF, the recommendation and the escalation flag."""
        c_addr = wallet_address.lower()
        all_txs = all_transactions
        sybil_out = agent_outputs["Sybil"]
        wallet_out = agent_outputs["Wallet"]
        finney_out = agent_outputs["Finney"]
        eclipse_out = agent_outputs["Eclipse"]

        # ------------------------------------------------------------------
        # 2. Compute Attack Risk (AR)
        # AR = 0.30*S + 0.20*W + 0.20*F + 0.30*E
        # ------------------------------------------------------------------
        s_risk = sybil_out.risk
        w_risk = wallet_out.risk
        f_risk = finney_out.risk
        e_risk = eclipse_out.risk

        ar = (
            self.config.weight_sybil * s_risk
            + self.config.weight_wallet * w_risk
            + self.config.weight_finney * f_risk
            + self.config.weight_eclipse * e_risk
        )
        ar = round(max(0.0, min(1.0, ar)), 3)

        # ------------------------------------------------------------------
        # 3. Compute Positive Trust (PT)
        # ------------------------------------------------------------------
        has_conflicts = finney_out.critical or finney_out.risk > 0.50
        pt_score: PositiveTrustScore = self.pt_engine.evaluate(
            candidate_address=c_addr,
            all_transactions=all_txs,
            peer_profile=peer_profile,
            peer_registry=peer_registry,
            current_time=current_time,
            has_conflicts=has_conflicts,
            prior_alerts_count=prior_alerts_count,
            known_exchanges=known_exchanges
        )
        pt = pt_score.pt_total

        # ------------------------------------------------------------------
        # 4. Compute Final Trust Factor (TF)
        # TF = 0.60*PT + 0.40*(1 - AR)
        # ------------------------------------------------------------------
        tf = (self.config.weight_tf_pt * pt) + (self.config.weight_tf_ar * (1.0 - ar))
        tf = round(max(0.0, min(1.0, tf)), 3)

        # Recommendation: Strictly TF-based comparison with TV (0.70)
        recommendation = Recommendation.ACCEPT if tf >= self.config.threshold_tv else Recommendation.REJECT

        # ------------------------------------------------------------------
        # 5. Escalation Flag (Documented Extension)
        # Triggers when any single agent risk >= 0.75 or critical evidence is found
        # Advises the human administrator to investigate.
        # ------------------------------------------------------------------
        escalation_reasons = []
        max_agent_risk = max(s_risk, w_risk, f_risk, e_risk)

        if s_risk >= self.config.escalation_risk_threshold:
            escalation_reasons.append(f"Sybil risk {s_risk:.2f} exceeds escalation threshold ({self.config.escalation_risk_threshold})")
        if w_risk >= self.config.escalation_risk_threshold:
            escalation_reasons.append(f"Wallet risk {w_risk:.2f} exceeds escalation threshold ({self.config.escalation_risk_threshold})")
        if f_risk >= self.config.escalation_risk_threshold:
            escalation_reasons.append(f"Finney risk {f_risk:.2f} exceeds escalation threshold ({self.config.escalation_risk_threshold})")
        if e_risk >= self.config.escalation_risk_threshold:
            escalation_reasons.append(f"Eclipse risk {e_risk:.2f} exceeds escalation threshold ({self.config.escalation_risk_threshold})")

        if sybil_out.critical:
            escalation_reasons.append("Sybil agent flagged critical cluster creation")
        if wallet_out.critical:
            escalation_reasons.append("Wallet agent flagged critical DoS/failure rate")
        if finney_out.critical:
            escalation_reasons.append("Finney agent flagged critical double-spend / withholding")
        if eclipse_out.critical:
            escalation_reasons.append("Eclipse agent flagged critical routing table monopoly")

        escalation_flag = len(escalation_reasons) > 0

        return TrustEvaluation(
            candidate_id=candidate_id,
            wallet_address=c_addr,
            ar=ar,
            pt=pt,
            tf=tf,
            tv=self.config.threshold_tv,
            recommendation=recommendation,
            escalation_flag=escalation_flag,
            escalation_reasons=escalation_reasons,
            agent_outputs=agent_outputs,
            pt_score=pt_score,
            timestamp=current_time,
            metadata={
                "max_agent_risk": max_agent_risk,
                "chain_info": chain_info or {}
            }
        )
