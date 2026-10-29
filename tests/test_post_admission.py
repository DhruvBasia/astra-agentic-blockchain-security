"""
tests/test_post_admission.py
Unit tests for post-admission consensus simulation and threat detection agents.
Tests all 5 miner scenarios:
1. Honest baseline (zero false positive alerts)
2. Selfish mining (Eyal-Sirer fork / orphan rate anomaly)
3. 51% coalition (Wilson lower bound > 0.45, private fork reorg)
4. Block withholding (delayed publication & binomial pool share discrepancy)
5. Race double-spend (conflicting on-chain / mempool sightings)
"""

import pytest
from astra.consensus_sim.miner_strategies import MinerType
from astra.consensus_sim.simulator import ConsensusSimulator
from astra.post_admission.continuous_monitor import ContinuousMonitor


def test_post_admission_honest_baseline():
    """Verify that an honest network generates steady blocks without triggering attack alerts."""
    sim = ConsensusSimulator(seed=42)
    sim.setup_miners(MinerType.HONEST)
    monitor = ContinuousMonitor(window_blocks=25)

    for _ in range(25):
        blocks = sim.step()
        for b in blocks:
            pool_stats = {
                m.miner_id: {"shares_submitted": m.pool_shares_submitted, "blocks_found": m.full_blocks_found}
                for m in sim.miners.values()
            }
            monitor.process_new_block(
                new_block=b,
                main_chain=sim.main_chain,
                orphaned_blocks=sim.orphaned_blocks,
                reorg_history=sim.reorg_history,
                propagation_log=sim.propagation_log,
                mempool_log=sim.mempool_log,
                miner_pool_stats=pool_stats,
            )

    # In honest conditions with uniform miners, no attack alerts should be emitted
    assert len(monitor.alerts) == 0


def test_post_admission_selfish_mining():
    """Verify that selfish miner withholding private blocks triggers SelfishMiningAgent alerts."""
    sim = ConsensusSimulator(seed=101)
    sim.setup_miners(MinerType.SELFISH)
    monitor = ContinuousMonitor(window_blocks=25)

    for step in range(35):
        if step == 3:
            monitor.set_attack_start(sim.current_time)
        blocks = sim.step()
        for b in blocks:
            pool_stats = {
                m.miner_id: {"shares_submitted": m.pool_shares_submitted, "blocks_found": m.full_blocks_found}
                for m in sim.miners.values()
            }
            monitor.process_new_block(
                new_block=b,
                main_chain=sim.main_chain,
                orphaned_blocks=sim.orphaned_blocks,
                reorg_history=sim.reorg_history,
                propagation_log=sim.propagation_log,
                mempool_log=sim.mempool_log,
                miner_pool_stats=pool_stats,
            )

    selfish_alerts = [a for a in monitor.alerts if "Selfish Mining" in a.agent_name]
    assert len(selfish_alerts) > 0


def test_post_admission_51_percent_coalition():
    """Verify that a 51% coalition mining private forks triggers Attack51Agent alerts."""
    sim = ConsensusSimulator(seed=202)
    sim.setup_miners(MinerType.COALITION_51)
    monitor = ContinuousMonitor(window_blocks=25)

    for step in range(35):
        if step == 3:
            monitor.set_attack_start(sim.current_time)
        blocks = sim.step()
        for b in blocks:
            pool_stats = {
                m.miner_id: {"shares_submitted": m.pool_shares_submitted, "blocks_found": m.full_blocks_found}
                for m in sim.miners.values()
            }
            monitor.process_new_block(
                new_block=b,
                main_chain=sim.main_chain,
                orphaned_blocks=sim.orphaned_blocks,
                reorg_history=sim.reorg_history,
                propagation_log=sim.propagation_log,
                mempool_log=sim.mempool_log,
                miner_pool_stats=pool_stats,
            )

    coalition_alerts = [a for a in monitor.alerts if "51% Attack" in a.agent_name]
    assert len(coalition_alerts) > 0


def test_post_admission_block_withholding():
    """Verify that block withholding miner triggers BlockWithholdingAgent alerts."""
    sim = ConsensusSimulator(seed=303)
    sim.setup_miners(MinerType.BLOCK_WITHHOLDING)
    monitor = ContinuousMonitor(window_blocks=25)

    for step in range(35):
        if step == 3:
            monitor.set_attack_start(sim.current_time)
        blocks = sim.step()
        for b in blocks:
            pool_stats = {
                m.miner_id: {"shares_submitted": m.pool_shares_submitted, "blocks_found": m.full_blocks_found}
                for m in sim.miners.values()
            }
            monitor.process_new_block(
                new_block=b,
                main_chain=sim.main_chain,
                orphaned_blocks=sim.orphaned_blocks,
                reorg_history=sim.reorg_history,
                propagation_log=sim.propagation_log,
                mempool_log=sim.mempool_log,
                miner_pool_stats=pool_stats,
            )

    bwh_alerts = [a for a in monitor.alerts if "Block Withholding" in a.agent_name]
    assert len(bwh_alerts) > 0


def test_post_admission_race_double_spend():
    """Verify that race double-spending transactions trigger DoubleSpendAgent alerts."""
    sim = ConsensusSimulator(seed=404)
    sim.setup_miners(MinerType.RACE_DOUBLE_SPEND)
    monitor = ContinuousMonitor(window_blocks=25)

    for step in range(35):
        if step == 3:
            monitor.set_attack_start(sim.current_time)
        blocks = sim.step()
        for b in blocks:
            pool_stats = {
                m.miner_id: {"shares_submitted": m.pool_shares_submitted, "blocks_found": m.full_blocks_found}
                for m in sim.miners.values()
            }
            monitor.process_new_block(
                new_block=b,
                main_chain=sim.main_chain,
                orphaned_blocks=sim.orphaned_blocks,
                reorg_history=sim.reorg_history,
                propagation_log=sim.propagation_log,
                mempool_log=sim.mempool_log,
                miner_pool_stats=pool_stats,
            )

    ds_alerts = [a for a in monitor.alerts if "Double" in a.agent_name]
    assert len(ds_alerts) > 0
