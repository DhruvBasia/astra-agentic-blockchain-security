"""
Unit tests for the 8–10 transaction Observation Window.
Tests honest graduation and sleeper node interception.
"""

import pytest
from astra.blockchain.sim_chain import SimChain
from astra.network.peer_registry import PeerRegistry
from astra.network.mempool import MempoolLog
from astra.network.propagation import BlockPropagationLog
from astra.scenarios.generator import ScenarioGenerator
from astra.observation.window import ObservationWindowManager
from astra.pre_admission.types import AdminAction


def test_observation_window_honest_graduation():
    chain = SimChain(seed=202)
    peer_reg = PeerRegistry(seed=202)
    mempool = MempoolLog()
    prop_log = BlockPropagationLog()
    gen = ScenarioGenerator(seed=202)
    gen.populate_background(chain, peer_reg, mempool, prop_log)

    cand = gen.create_candidate("honest", "HONEST_OBS_TEST", chain, peer_reg, mempool, prop_log)
    obs = ObservationWindowManager()
    session = obs.start_session(cand.candidate_id, cand.wallet_address, window_size=10)

    for _ in range(10):
        chain.advance_time(60.0)
        recipient = chain.create_account()
        tx = chain.send(sender=cand.wallet_address, to=recipient, value_eth=0.1)
        res = obs.process_transaction(session, tx, chain, cand.peer_profile, peer_reg, mempool)
        assert res.suggested_action == AdminAction.CONTINUE

    assert session.is_graduated
    assert len(session.step_results) == 10


def test_observation_window_sleeper_interception():
    chain = SimChain(seed=303)
    peer_reg = PeerRegistry(seed=303)
    mempool = MempoolLog()
    prop_log = BlockPropagationLog()
    gen = ScenarioGenerator(seed=303)
    gen.populate_background(chain, peer_reg, mempool, prop_log)

    sleeper = gen.create_candidate("sleeper", "SLEEPER_OBS_TEST", chain, peer_reg, mempool, prop_log)
    obs = ObservationWindowManager()
    session = obs.start_session(sleeper.candidate_id, sleeper.wallet_address, window_size=10)
    ally = sleeper.related_cluster[0]

    alert_triggered = False
    for step in range(1, 11):
        chain.advance_time(30.0)
        if step >= 5:
            # Malicious cluster transfers
            tx = chain.send(sender=sleeper.wallet_address, to=ally, value_eth=0.2)
            res = obs.process_transaction(
                session, tx, chain, sleeper.peer_profile, peer_reg, mempool,
                known_related_cluster=sleeper.related_cluster
            )
        else:
            other = chain.create_account()
            tx = chain.send(sender=sleeper.wallet_address, to=other, value_eth=0.1)
            res = obs.process_transaction(session, tx, chain, sleeper.peer_profile, peer_reg, mempool)

        if res.alert_raised:
            alert_triggered = True

    assert alert_triggered
    assert not session.is_graduated
