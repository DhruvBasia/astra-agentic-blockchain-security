"""
tests/test_e2e.py
End-to-end integration tests for ASTRA:
- Plain-Python orchestrator candidate admission flow
- Evaluation benchmark suite execution (pre-admission, sleeper observation, consensus)
- Report and JSON persistence verification
- LangGraph human-in-the-loop interruption and resumption
"""

import os
import json
import pytest
from astra.blockchain.sim_chain import SimChain
from astra.network.peer_registry import PeerRegistry
from astra.network.mempool import MempoolLog
from astra.network.propagation import BlockPropagationLog
from astra.scenarios.generator import ScenarioGenerator
from astra.orchestration.plain_orchestrator import PlainOrchestrator
from astra.admin.policies import AutoAdmin, AdminPolicy
from astra.pre_admission.types import AdminAction, AdminDecisionRecord, Recommendation
from astra.evaluation.runner import EvaluationRunner
from astra.orchestration.langgraph_flow import build_astra_langgraph, AgenticState
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver


def test_e2e_plain_orchestrator_admission():
    chain = SimChain(seed=123)
    peer_reg = PeerRegistry(seed=123)
    mempool = MempoolLog()
    prop_log = BlockPropagationLog()
    gen = ScenarioGenerator(seed=123)
    gen.populate_background(chain, peer_reg, mempool, prop_log)

    cand_honest = gen.create_candidate("honest", "E2E_HONEST", chain, peer_reg, mempool, prop_log)
    cand_sybil = gen.create_candidate("sybil", "E2E_SYBIL", chain, peer_reg, mempool, prop_log)

    orch = PlainOrchestrator(admin_policy=AutoAdmin())

    # Evaluate honest candidate
    res_honest = orch.run_admission(
        candidate_id=cand_honest.candidate_id,
        wallet_address=cand_honest.wallet_address,
        chain=chain,
        peer_profile=cand_honest.peer_profile,
        peer_registry=peer_reg,
        mempool_log=mempool,
        propagation_log=prop_log,
        known_exchanges=gen.exchanges,
    )
    assert res_honest["evaluation"].recommendation == Recommendation.ACCEPT
    assert res_honest["decision"].action == AdminAction.ACCEPT

    # Evaluate Sybil attacker
    res_sybil = orch.run_admission(
        candidate_id=cand_sybil.candidate_id,
        wallet_address=cand_sybil.wallet_address,
        chain=chain,
        peer_profile=cand_sybil.peer_profile,
        peer_registry=peer_reg,
        mempool_log=mempool,
        propagation_log=prop_log,
        known_exchanges=gen.exchanges,
    )
    assert res_sybil["evaluation"].recommendation == Recommendation.REJECT
    assert res_sybil["decision"].action == AdminAction.REJECT


def test_e2e_evaluation_runner_pipeline(tmp_path):
    output_dir = str(tmp_path / "results")
    runner = EvaluationRunner(seed=42)

    eval_out = runner.generate_full_evaluation(backend_name="sim", n_candidates=15, output_dir=output_dir)

    assert eval_out["metadata"]["backend"] in ("sim", "SimChain")
    assert "pre_admission" in eval_out
    assert "observation_window" in eval_out
    assert "post_admission" in eval_out

    # Verify JSON and Markdown files were generated on disk
    json_path = os.path.join(output_dir, "eval_results.json")
    md_path = os.path.join(output_dir, "eval_report.md")
    assert os.path.isfile(json_path)
    assert os.path.isfile(md_path)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["pre_admission"]["total_evaluated"] == 15
    assert data["observation_window"]["detected"] is True

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    assert "ASTRA" in md_text and "REPORT" in md_text
    assert "Confusion Matrix" in md_text


def test_e2e_langgraph_flow_with_interruption():
    checkpointer = MemorySaver()
    graph = build_astra_langgraph(checkpointer=checkpointer)

    thread_config = {"configurable": {"thread_id": "test_e2e_thread_1"}}
    initial_state = {
        "candidate_id": "LG_CANDIDATE_01",
        "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
        "sybil_risk": 0.1,
        "wallet_risk": 0.05,
        "finney_risk": 0.05,
        "eclipse_risk": 0.05,
        "ar": 0.065,
        "pt": 0.85,
        "tf": 0.884,
        "tv": 0.70,
        "recommendation": "ACCEPT",
        "escalation_flag": False,
        "escalation_reasons": [],
    }

    # Step 1: Run graph up to human review interrupt
    interrupt_state = graph.invoke(initial_state, config=thread_config)
    assert "__interrupt__" in interrupt_state

    # Step 2: Resume with administrator decision
    decision_payload = {
        "action": "ACCEPT",
        "reason": "Verified clean node with high trust factor.",
        "admin_id": "human_admin_01",
    }
    final_state = graph.invoke(Command(resume=decision_payload), config=thread_config)

    assert final_state["admin_decision"] == "ACCEPT"
    assert "Verified clean" in final_state["admin_reason"]
