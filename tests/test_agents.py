"""
Unit tests for the 4 specialized Pre-Admission Agents:
Sybil, Wallet, Finney, Eclipse.
Evaluates both clean and attack cases for each agent.
"""

import pytest
from astra.blockchain.sim_chain import SimChain
from astra.network.peer_registry import PeerRegistry
from astra.network.mempool import MempoolLog
from astra.network.propagation import BlockPropagationLog
from astra.scenarios.generator import ScenarioGenerator
from astra.pre_admission.sybil_agent import SybilAgent
from astra.pre_admission.wallet_agent import WalletAgent
from astra.pre_admission.finney_agent import FinneyAgent
from astra.pre_admission.eclipse_agent import EclipseAgent


@pytest.fixture
def sim_env():
    chain = SimChain(seed=101)
    peer_reg = PeerRegistry(seed=101)
    mempool = MempoolLog()
    prop_log = BlockPropagationLog()
    gen = ScenarioGenerator(seed=101)
    gen.populate_background(chain, peer_reg, mempool, prop_log)
    return chain, peer_reg, mempool, prop_log, gen


def test_sybil_agent_clean_vs_attack(sim_env):
    chain, peer_reg, mempool, prop_log, gen = sim_env
    agent = SybilAgent()

    # Clean Honest Node
    c_honest = gen.create_candidate("honest", "HONEST_SYBIL_TEST", chain, peer_reg, mempool, prop_log)
    out_honest = agent.evaluate(c_honest.wallet_address, chain.all_transactions(), chain.now())
    assert out_honest.risk < 0.35
    assert not out_honest.critical

    # Sybil Cluster Attack
    c_sybil = gen.create_candidate("sybil", "ATTACK_SYBIL_TEST", chain, peer_reg, mempool, prop_log)
    out_sybil = agent.evaluate(c_sybil.wallet_address, chain.all_transactions(), chain.now())
    assert out_sybil.risk >= 0.70


def test_wallet_agent_clean_vs_attack(sim_env):
    chain, peer_reg, mempool, prop_log, gen = sim_env
    agent = WalletAgent()

    # Clean Honest Node
    c_honest = gen.create_candidate("honest", "HONEST_WALLET_TEST", chain, peer_reg, mempool, prop_log)
    out_honest = agent.evaluate(c_honest.wallet_address, chain.all_transactions(), chain.now())
    assert out_honest.risk < 0.30

    # Malicious Bot Wallet
    c_wallet = gen.create_candidate("malicious_wallet", "ATTACK_WALLET_TEST", chain, peer_reg, mempool, prop_log)
    out_wallet = agent.evaluate(c_wallet.wallet_address, chain.all_transactions(), chain.now())
    assert out_wallet.risk >= 0.65


def test_finney_agent_clean_vs_attack(sim_env):
    chain, peer_reg, mempool, prop_log, gen = sim_env
    agent = FinneyAgent()

    # Clean / Benign Fee Bumper
    c_bumper = gen.create_candidate("honest_fee_bumper", "FEE_BUMPER_TEST", chain, peer_reg, mempool, prop_log)
    out_bumper = agent.evaluate(c_bumper.wallet_address, chain.all_transactions(), mempool, prop_log)
    assert out_bumper.risk < 0.30
    assert not out_bumper.critical

    # Finney Attack Double Spend
    c_finney = gen.create_candidate("finney", "ATTACK_FINNEY_TEST", chain, peer_reg, mempool, prop_log)
    out_finney = agent.evaluate(
        c_finney.wallet_address,
        chain.all_transactions(),
        mempool,
        prop_log,
        candidate_mined_blocks=c_finney.mined_blocks
    )
    assert out_finney.risk >= 0.85
    assert out_finney.critical


def test_eclipse_agent_clean_vs_attack(sim_env):
    chain, peer_reg, mempool, prop_log, gen = sim_env
    agent = EclipseAgent()

    # Clean Honest Node
    c_honest = gen.create_candidate("honest", "HONEST_ECLIPSE_TEST", chain, peer_reg, mempool, prop_log)
    out_honest = agent.evaluate(c_honest.peer_profile, peer_reg, current_tip=chain.block_number())
    assert out_honest.risk < 0.30
    assert not out_honest.critical

    # Eclipsed Node
    c_eclipse = gen.create_candidate("eclipse", "ATTACK_ECLIPSE_TEST", chain, peer_reg, mempool, prop_log)
    out_eclipse = agent.evaluate(c_eclipse.peer_profile, peer_reg, current_tip=chain.block_number())
    assert out_eclipse.risk >= 0.75
