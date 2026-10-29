"""
Optional LangGraph Orchestration Flow.
Builds a LangGraph StateGraph implementing:
  collect -> fan-out (Sybil, Wallet, Finney, Eclipse) -> aggregate -> human_review (via interrupt)
  Resumes execution with Command(resume=decision).

Two builders share that topology:
  build_live_admission_graph: nodes run the real agents on live chain evidence.
  build_astra_langgraph:      nodes pass through pre-supplied risk values (flow/interrupt testing).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from astra.pre_admission.monitor_agent import MonitorAgent
from astra.pre_admission.types import AgentOutput, TrustEvaluation, AdminAction, Recommendation
from astra.blockchain.backend import ChainBackend, TxRecord
from astra.network.peer_registry import PeerProfile, PeerRegistry
from astra.network.mempool import MempoolLog
from astra.network.propagation import BlockPropagationLog
from astra.config import ASTRAConfig, DEFAULT_CONFIG


class AgenticState(TypedDict, total=False):
    candidate_id: str
    wallet_address: str
    chain_data: Dict[str, Any]
    peer_data: Dict[str, Any]
    sybil_risk: float
    wallet_risk: float
    finney_risk: float
    eclipse_risk: float
    sybil_evidence: List[str]
    wallet_evidence: List[str]
    finney_evidence: List[str]
    eclipse_evidence: List[str]
    ar: float
    pt: float
    tf: float
    tv: float
    recommendation: str
    escalation_flag: bool
    escalation_reasons: List[str]
    admin_decision: str
    admin_reason: str


def human_review_node(state: AgenticState) -> Dict[str, Any]:
    """Human Review Node: pauses the graph with interrupt() until the administrator decides."""
    review_request = {
        "message": "Human administrator review required for blockchain admission",
        "candidate_id": state["candidate_id"],
        "wallet_address": state["wallet_address"],
        "tf": state["tf"],
        "ar": state["ar"],
        "pt": state["pt"],
        "recommendation": state["recommendation"],
        "escalation_flag": state["escalation_flag"]
    }
    human_response = interrupt(review_request)
    action = human_response.get("action", state["recommendation"])
    reason = human_response.get("reason", "Decision confirmed by administrator.")
    return {
        "admin_decision": action,
        "admin_reason": reason
    }


@dataclass
class AdmissionContext:
    """
    Live evidence the graph nodes work on for one candidate.
    Kept outside the checkpointed graph state because chain connections and
    agent output objects are not serializable; the state only carries plain values.
    """
    candidate_id: str
    wallet_address: str
    chain: ChainBackend
    peer_profile: PeerProfile
    peer_registry: PeerRegistry
    mempool_log: MempoolLog
    propagation_log: Optional[BlockPropagationLog] = None
    candidate_mined_blocks: Optional[List[int]] = None
    known_exchanges: Optional[List[str]] = None

    # Filled in by the graph nodes as they execute
    all_transactions: List[TxRecord] = field(default_factory=list)
    current_time: float = 0.0
    current_tip: int = 0
    agent_outputs: Dict[str, AgentOutput] = field(default_factory=dict)
    evaluation: Optional[TrustEvaluation] = None


def build_live_admission_graph(
    ctx: AdmissionContext,
    monitor_agent: Optional[MonitorAgent] = None,
    checkpointer: Optional[MemorySaver] = None
):
    """
    Constructs the ASTRA StateGraph in which every node does real work on live evidence:
      collect (read chain) -> Sybil | Wallet | Finney | Eclipse agents in parallel
      -> aggregate (AR, PT, TF) -> human_review (interrupt) -> END
    """
    monitor = monitor_agent or MonitorAgent()
    checkpointer = checkpointer or MemorySaver()
    c_addr = ctx.wallet_address.lower()

    # 1. Evidence Collection Node: reads the ledger once for all agents
    def collect_node(state: AgenticState) -> Dict[str, Any]:
        ctx.all_transactions = ctx.chain.all_transactions()
        ctx.current_time = ctx.chain.now()
        ctx.current_tip = ctx.chain.block_number()
        return {
            "candidate_id": ctx.candidate_id,
            "wallet_address": c_addr,
            "chain_data": {
                "transactions_scanned": len(ctx.all_transactions),
                "block_height": ctx.current_tip
            },
            "peer_data": {
                "peer_count": ctx.peer_profile.peer_count,
                "distinct_asns": len(set(ctx.peer_profile.asns))
            }
        }

    # 2. Fan-out Agent Nodes
    def sybil_node(state: AgenticState) -> Dict[str, Any]:
        out = monitor.sybil_agent.evaluate(
            candidate_address=c_addr,
            all_transactions=ctx.all_transactions,
            current_time=ctx.current_time,
            known_exchange_addresses=ctx.known_exchanges
        )
        ctx.agent_outputs["Sybil"] = out
        return {"sybil_risk": out.risk, "sybil_evidence": out.evidence}

    def wallet_node(state: AgenticState) -> Dict[str, Any]:
        out = monitor.wallet_agent.evaluate(
            candidate_address=c_addr,
            all_transactions=ctx.all_transactions,
            current_time=ctx.current_time
        )
        ctx.agent_outputs["Wallet"] = out
        return {"wallet_risk": out.risk, "wallet_evidence": out.evidence}

    def finney_node(state: AgenticState) -> Dict[str, Any]:
        out = monitor.finney_agent.evaluate(
            candidate_address=c_addr,
            on_chain_txs=ctx.all_transactions,
            mempool_log=ctx.mempool_log,
            propagation_log=ctx.propagation_log,
            candidate_mined_blocks=ctx.candidate_mined_blocks
        )
        ctx.agent_outputs["Finney"] = out
        return {"finney_risk": out.risk, "finney_evidence": out.evidence}

    def eclipse_node(state: AgenticState) -> Dict[str, Any]:
        out = monitor.eclipse_agent.evaluate(
            peer_profile=ctx.peer_profile,
            peer_registry=ctx.peer_registry,
            current_tip=ctx.current_tip
        )
        ctx.agent_outputs["Eclipse"] = out
        return {"eclipse_risk": out.risk, "eclipse_evidence": out.evidence}

    # 3. Aggregation Node: same AR / PT / TF computation as MonitorAgent.evaluate_candidate
    def aggregate_node(state: AgenticState) -> Dict[str, Any]:
        ev = monitor.aggregate(
            candidate_id=ctx.candidate_id,
            wallet_address=c_addr,
            agent_outputs={name: ctx.agent_outputs[name] for name in ("Sybil", "Wallet", "Finney", "Eclipse")},
            all_transactions=ctx.all_transactions,
            current_time=ctx.current_time,
            peer_profile=ctx.peer_profile,
            peer_registry=ctx.peer_registry,
            chain_info=ctx.chain.info(),
            known_exchanges=ctx.known_exchanges
        )
        ctx.evaluation = ev
        return {
            "ar": ev.ar,
            "pt": ev.pt,
            "tf": ev.tf,
            "tv": ev.tv,
            "recommendation": ev.recommendation.value,
            "escalation_flag": ev.escalation_flag,
            "escalation_reasons": ev.escalation_reasons
        }

    builder = StateGraph(AgenticState)
    builder.add_node("collect", collect_node)
    builder.add_node("sybil_agent", sybil_node)
    builder.add_node("wallet_agent", wallet_node)
    builder.add_node("finney_agent", finney_node)
    builder.add_node("eclipse_agent", eclipse_node)
    builder.add_node("aggregate", aggregate_node)
    builder.add_node("human_review", human_review_node)

    builder.add_edge(START, "collect")
    for agent_node in ("sybil_agent", "wallet_agent", "finney_agent", "eclipse_agent"):
        builder.add_edge("collect", agent_node)
        builder.add_edge(agent_node, "aggregate")
    builder.add_edge("aggregate", "human_review")
    builder.add_edge("human_review", END)

    return builder.compile(checkpointer=checkpointer)


def build_astra_langgraph(monitor_agent: Optional[MonitorAgent] = None, checkpointer: Optional[MemorySaver] = None):
    """Constructs the ASTRA multi-agent StateGraph."""
    monitor = monitor_agent or MonitorAgent()
    checkpointer = checkpointer or MemorySaver()

    builder = StateGraph(AgenticState)

    # 1. Evidence Collection Node
    def collect_node(state: AgenticState) -> Dict[str, Any]:
        return {
            "candidate_id": state.get("candidate_id", "CAND_01"),
            "wallet_address": state.get("wallet_address", "0x0")
        }

    # 2. Fan-out Agent Nodes
    def sybil_node(state: AgenticState) -> Dict[str, Any]:
        risk = state.get("sybil_risk", 0.08)
        evidence = state.get("sybil_evidence", ["No Sybil cluster detected."])
        return {"sybil_risk": risk, "sybil_evidence": evidence}

    def wallet_node(state: AgenticState) -> Dict[str, Any]:
        risk = state.get("wallet_risk", 0.05)
        evidence = state.get("wallet_evidence", ["Transaction rate normal."])
        return {"wallet_risk": risk, "wallet_evidence": evidence}

    def finney_node(state: AgenticState) -> Dict[str, Any]:
        risk = state.get("finney_risk", 0.05)
        evidence = state.get("finney_evidence", ["No conflicting mempool sightings."])
        return {"finney_risk": risk, "finney_evidence": evidence}

    def eclipse_node(state: AgenticState) -> Dict[str, Any]:
        risk = state.get("eclipse_risk", 0.08)
        evidence = state.get("eclipse_evidence", ["Diversified peer topology."])
        return {"eclipse_risk": risk, "eclipse_evidence": evidence}

    # 3. Aggregation Node
    def aggregate_node(state: AgenticState) -> Dict[str, Any]:
        cfg = monitor.config
        s = state.get("sybil_risk", 0.0)
        w = state.get("wallet_risk", 0.0)
        f = state.get("finney_risk", 0.0)
        e = state.get("eclipse_risk", 0.0)

        ar = round(cfg.weight_sybil * s + cfg.weight_wallet * w + cfg.weight_finney * f + cfg.weight_eclipse * e, 3)
        pt = round(state.get("pt", 0.80), 3)
        tf = round(cfg.weight_tf_pt * pt + cfg.weight_tf_ar * (1.0 - ar), 3)
        rec = "ACCEPT" if tf >= cfg.threshold_tv else "REJECT"

        escalation_reasons = []
        if max(s, w, f, e) >= cfg.escalation_risk_threshold:
            escalation_reasons.append(f"Individual risk >= {cfg.escalation_risk_threshold}")

        return {
            "ar": ar,
            "pt": pt,
            "tf": tf,
            "tv": cfg.threshold_tv,
            "recommendation": rec,
            "escalation_flag": len(escalation_reasons) > 0,
            "escalation_reasons": escalation_reasons
        }

    # Register nodes
    builder.add_node("collect", collect_node)
    builder.add_node("sybil_agent", sybil_node)
    builder.add_node("wallet_agent", wallet_node)
    builder.add_node("finney_agent", finney_node)
    builder.add_node("eclipse_agent", eclipse_node)
    builder.add_node("aggregate", aggregate_node)
    builder.add_node("human_review", human_review_node)

    # Connect edges
    builder.add_edge(START, "collect")
    builder.add_edge("collect", "sybil_agent")
    builder.add_edge("collect", "wallet_agent")
    builder.add_edge("collect", "finney_agent")
    builder.add_edge("collect", "eclipse_agent")
    builder.add_edge("sybil_agent", "aggregate")
    builder.add_edge("wallet_agent", "aggregate")
    builder.add_edge("finney_agent", "aggregate")
    builder.add_edge("eclipse_agent", "aggregate")
    builder.add_edge("aggregate", "human_review")
    builder.add_edge("human_review", END)

    return builder.compile(checkpointer=checkpointer)
