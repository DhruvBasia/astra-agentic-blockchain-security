"""
STEP 11: Multi-Agent Orchestration Workflow Graph
Orchestrates the node admission pipeline from Monitor Agent through
Attack Agents, Trust Scoring, Policy Validation, and Memory Update.
"""

from typing import Dict, Any, List
from agents.monitor_agent import MonitorAgent
from agents.sybil_agent import SybilAgent
from agents.wallet_agent import WalletAgent
from agents.finney_agent import FinneyAgent
from agents.eclipse_agent import EclipseAgent
from scoring.trust_calculator import TrustCalculator
from memory.trust_memory import TrustMemory


class AdmissionState:
    """Represents the shared working context across the agent graph"""
    def __init__(self, raw_request: Dict[str, Any]):
        self.raw_request = raw_request
        self.evidence = None
        self.risk_scores = {}
        self.agent_explanations = []
        self.positive_parameters = {}
        self.evaluation_result = {}
        self.final_decision = None
        self.llm_summary = ""


class AdmissionWorkflowGraph:
    """
    Executes the multi-agent graph:
    START -> Monitor -> Attack Agents -> Positive Trust -> Policy Engine -> Memory -> END
    """
    def __init__(self, memory: TrustMemory = None, tv_threshold: float = 0.70):
        self.monitor_agent = MonitorAgent()
        self.sybil_agent = SybilAgent()
        self.wallet_agent = WalletAgent()
        self.finney_agent = FinneyAgent()
        self.eclipse_agent = EclipseAgent()
        self.calculator = TrustCalculator(tv_threshold=tv_threshold)
        self.memory = memory or TrustMemory()

    def run(self, raw_node_dict: Dict[str, Any]) -> Dict[str, Any]:
        state = AdmissionState(raw_node_dict)

        # Node 1: Monitor Agent
        state.evidence = self.monitor_agent.process_join_request(raw_node_dict)

        # Node 2: Specialized Attack Agents
        sybil_res = self.sybil_agent.evaluate(state.evidence.sybil_evidence)
        wallet_res = self.wallet_agent.evaluate(state.evidence.wallet_evidence)
        finney_res = self.finney_agent.evaluate(state.evidence.finney_evidence)
        eclipse_res = self.eclipse_agent.evaluate(state.evidence.eclipse_evidence)

        sr = sybil_res["sybil_risk"]
        wr = wallet_res["wallet_risk"]
        fr = finney_res["finney_risk"]
        er = eclipse_res["eclipse_risk"]

        state.risk_scores = {"SR": sr, "WR": wr, "FR": fr, "ER": er}
        state.agent_explanations = [
            sybil_res["explanation"],
            wallet_res["explanation"],
            finney_res["explanation"],
            eclipse_res["explanation"]
        ]

        # Node 3: Positive Trust Parameters (I, T, N, H, B)
        # Check historical memory for H
        hist = self.memory.get_node_history(state.evidence.node_id)
        if not hist:
            h_score = 0.50  # Unknown/neutral for new node
        else:
            good_records = sum(1 for r in hist if r["decision"] == "ACCEPT")
            h_score = round(good_records / len(hist), 2)

        pos = state.evidence.positive_indicators
        state.positive_parameters = {
            "I": pos["identity_maturity_score"],
            "T": pos["transaction_stability_score"],
            "N": pos["network_connectivity_score"],
            "H": h_score,
            "B": pos["consistency_factor"]
        }

        # Node 4: Trust Calculator & Deterministic Policy Layer
        state.evaluation_result = self.calculator.evaluate_admission(
            sr=sr,
            wr=wr,
            fr=fr,
            er=er,
            i=state.positive_parameters["I"],
            t=state.positive_parameters["T"],
            n=state.positive_parameters["N"],
            h=state.positive_parameters["H"],
            b=state.positive_parameters["B"]
        )

        state.final_decision = state.evaluation_result["decision"]

        # Node 5: Memory Update
        self.memory.record_decision(
            node_id=state.evidence.node_id,
            wallet_address=state.evidence.wallet_address,
            tf=state.evaluation_result["tf"],
            al=state.evaluation_result["al"],
            decision=state.final_decision,
            risk_scores=state.risk_scores,
            positive_parameters=state.positive_parameters,
            reason=state.evaluation_result["reason"]
        )

        # Node 6: Explainable Reasoning Summary
        if state.final_decision == "ACCEPT":
            state.llm_summary = (
                f"Node {state.evidence.node_id} accepted with high Trust Factor ({state.evaluation_result['tf']:.2f} > {state.evaluation_result['tv']:.2f}). "
                f"Attack Level is low ({state.evaluation_result['al']:.2f}). Node meets all admission invariants."
            )
        else:
            state.llm_summary = (
                f"Node {state.evidence.node_id} admission REJECTED. "
                f"Reason: {state.evaluation_result['reason']}. "
                f"Computed Trust Factor is {state.evaluation_result['tf']:.2f} with Attack Level {state.evaluation_result['al']:.2f}."
            )

        return {
            "node_id": state.evidence.node_id,
            "wallet_address": state.evidence.wallet_address,
            "decision": state.final_decision,
            "tf": state.evaluation_result["tf"],
            "tv": state.evaluation_result["tv"],
            "al": state.evaluation_result["al"],
            "pt": state.evaluation_result["pt"],
            "risk_scores": state.risk_scores,
            "positive_parameters": state.positive_parameters,
            "critical_override": state.evaluation_result["critical_override"],
            "reason": state.evaluation_result["reason"],
            "agent_explanations": state.agent_explanations,
            "summary": state.llm_summary
        }
