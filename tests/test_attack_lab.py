"""
Unit tests for the Attack Lab:
- the live LangGraph admission graph agrees with MonitorAgent.evaluate_candidate
- each attack is launched on-chain, analysed, refused admission, and saved to disk
"""

import json
import os
import pytest
from astra.blockchain.sim_chain import SimChain
from astra.pre_admission.monitor_agent import MonitorAgent
from astra.pre_admission.types import AdminAction
from astra.attack_lab import ATTACK_PLAYBOOK, launch_attack, analyse_with_agents, save_attack_run


@pytest.mark.parametrize("attack_type", list(ATTACK_PLAYBOOK))
def test_attack_is_launched_analysed_and_saved(attack_type, tmp_path):
    attack = launch_attack(attack_type, SimChain(seed=42))
    assert attack.footprint, "attack must leave transactions on the chain"
    assert any(tx.sender == attack.candidate.wallet_address or tx.to == attack.candidate.wallet_address
               for tx in attack.footprint)

    run = analyse_with_agents(attack)
    assert run.node_trace[0] == "collect"
    assert set(run.node_trace[1:5]) == {"sybil_agent", "wallet_agent", "finney_agent", "eclipse_agent"}
    assert run.node_trace[5:] == ["aggregate", "human_review"]
    assert run.decision.action != AdminAction.ACCEPT
    assert not run.admitted

    json_path, md_path = save_attack_run(run, str(tmp_path))
    assert os.path.isfile(json_path) and os.path.isfile(md_path)
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["run"]["attack_type"] == attack_type
    assert len(data["attack"]["on_chain_transactions"]) == len(attack.footprint)
    assert set(data["agentic_analysis"]["agents"]) == {"Sybil", "Wallet", "Finney", "Eclipse"}
    assert data["admin_decision"]["action"] == run.decision.action.value


def test_live_graph_matches_monitor_agent():
    attack = launch_attack("finney", SimChain(seed=7), seed=7)
    cand = attack.candidate
    expected = MonitorAgent().evaluate_candidate(
        candidate_id=cand.candidate_id,
        wallet_address=cand.wallet_address,
        chain=attack.chain,
        peer_profile=cand.peer_profile,
        peer_registry=attack.peer_registry,
        mempool_log=attack.mempool_log,
        propagation_log=attack.propagation_log,
        candidate_mined_blocks=cand.mined_blocks,
        known_exchanges=attack.known_exchanges,
    )

    run = analyse_with_agents(attack)
    assert run.evaluation.ar == expected.ar
    assert run.evaluation.pt == expected.pt
    assert run.evaluation.tf == expected.tf
    assert run.evaluation.recommendation == expected.recommendation
    assert run.evaluation.escalation_reasons == expected.escalation_reasons
