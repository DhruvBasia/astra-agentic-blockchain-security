"""
Discrete-event multi-miner PoW consensus simulator.
Simulates Poisson block discovery, network propagation delays, longest-chain rule,
tie-breaker parameter gamma, chain reorganizations, orphan tracking, and adversarial miner strategies.
"""

import math
import random
import hashlib
from typing import List, Dict, Any, Optional, Callable
from astra.post_admission.types import BlockRecord
from astra.consensus_sim.miner_strategies import MinerType, MinerAgentState
from astra.network.propagation import BlockPropagationLog
from astra.network.mempool import MempoolLog


class ConsensusSimulator:
    """Discrete-event multi-miner PoW simulator."""

    def __init__(
        self,
        block_time_mean: float = 30.0,
        propagation_mean: float = 0.8,
        gamma_tie: float = 0.5,
        seed: int = 42
    ):
        self.block_time_mean = block_time_mean
        self.propagation_mean = propagation_mean
        self.gamma_tie = gamma_tie
        self.rng = random.Random(seed)

        self.current_time: float = 1700000000.0
        self.main_chain: List[BlockRecord] = []
        self.orphaned_blocks: List[BlockRecord] = []
        self.reorg_history: List[Dict[str, Any]] = []
        self.propagation_log = BlockPropagationLog()
        self.mempool_log = MempoolLog()

        self.miners: Dict[str, MinerAgentState] = {}
        self._init_genesis()

    def _init_genesis(self) -> None:
        genesis = BlockRecord(
            block_number=0,
            block_hash="0xgenesis" + "0" * 56,
            parent_hash="0x" + "0" * 64,
            miner="0xgenesis_miner",
            timestamp=self.current_time,
            first_seen=self.current_time,
            transactions=[],
            is_orphan=False,
            is_main_chain=True,
            height=0
        )
        self.main_chain.append(genesis)
        self.propagation_log.record(0, genesis.miner, genesis.timestamp, genesis.first_seen)

    def setup_miners(self, scenario: MinerType, attacker_hashrate: float = 0.33) -> None:
        """Sets up miner network with given adversary strategy."""
        self.miners.clear()

        if scenario == MinerType.HONEST:
            # 4 honest miners splitting 100% hashpower
            for i in range(4):
                mid = f"0xminer_honest_{i}"
                self.miners[mid] = MinerAgentState(
                    miner_id=mid,
                    strategy=MinerType.HONEST,
                    hashrate_share=0.25
                )

        elif scenario == MinerType.SELFISH:
            # 1 selfish miner (alpha ~ 0.33) + honest miners (0.67)
            self.miners["0xminer_selfish_adv"] = MinerAgentState(
                miner_id="0xminer_selfish_adv",
                strategy=MinerType.SELFISH,
                hashrate_share=attacker_hashrate,
                attack_active=True
            )
            honest_share = (1.0 - attacker_hashrate) / 3.0
            for i in range(3):
                mid = f"0xminer_honest_{i}"
                self.miners[mid] = MinerAgentState(
                    miner_id=mid,
                    strategy=MinerType.HONEST,
                    hashrate_share=honest_share
                )

        elif scenario == MinerType.COALITION_51:
            # Sybil-linked coalition with ~55% hashpower
            self.miners["0xcoalition_leader"] = MinerAgentState(
                miner_id="0xcoalition_leader",
                strategy=MinerType.COALITION_51,
                hashrate_share=0.35,
                attack_active=True,
                censored_addresses=["0xvictim_merchant"]
            )
            self.miners["0xcoalition_sybil_ally"] = MinerAgentState(
                miner_id="0xcoalition_sybil_ally",
                strategy=MinerType.COALITION_51,
                hashrate_share=0.20,
                attack_active=True
            )
            # Honest remainder: 45%
            for i in range(3):
                mid = f"0xminer_honest_{i}"
                self.miners[mid] = MinerAgentState(
                    miner_id=mid,
                    strategy=MinerType.HONEST,
                    hashrate_share=0.15
                )

        elif scenario == MinerType.BLOCK_WITHHOLDING:
            self.miners["0xwithholding_miner"] = MinerAgentState(
                miner_id="0xwithholding_miner",
                strategy=MinerType.BLOCK_WITHHOLDING,
                hashrate_share=0.35,
                attack_active=True
            )
            honest_share = (1.0 - 0.35) / 3.0
            for i in range(3):
                mid = f"0xminer_honest_{i}"
                self.miners[mid] = MinerAgentState(
                    miner_id=mid,
                    strategy=MinerType.HONEST,
                    hashrate_share=honest_share
                )

        elif scenario == MinerType.RACE_DOUBLE_SPEND:
            self.miners["0xrace_attacker"] = MinerAgentState(
                miner_id="0xrace_attacker",
                strategy=MinerType.RACE_DOUBLE_SPEND,
                hashrate_share=0.35,
                attack_active=True
            )
            honest_share = (1.0 - 0.35) / 3.0
            for i in range(3):
                mid = f"0xminer_honest_{i}"
                self.miners[mid] = MinerAgentState(
                    miner_id=mid,
                    strategy=MinerType.HONEST,
                    hashrate_share=honest_share
                )
            # Record victim merchant payment in mempool
            self.mempool_log.record(
                tx_hash="0xmerchant_victim_payment_tx",
                sender="0xrace_attacker",
                nonce=1,
                to="0xmerchant_victim_store",
                value_eth=15.0,
                fee_eth=0.001,
                seen_at=self.current_time,
                is_mined=False
            )

    def _generate_block_hash(self, number: int, parent: str, miner: str) -> str:
        content = f"{number}:{parent}:{miner}:{self.rng.random()}"
        return "0x" + hashlib.sha256(content.encode()).hexdigest()

    def step(self, on_block_mined: Optional[Callable[[BlockRecord, List[BlockRecord]], None]] = None) -> List[BlockRecord]:
        """
        Advances discrete-event simulation by 1 mining discovery event.
        Returns newly published blocks.
        """
        # Exponential inter-arrival time
        dt = self.rng.expovariate(1.0 / self.block_time_mean)
        self.current_time += dt

        # Random miner discovery weighted by hashrate
        r = self.rng.random()
        cumulative = 0.0
        winning_miner: Optional[MinerAgentState] = None
        for m in self.miners.values():
            cumulative += m.hashrate_share
            if r <= cumulative:
                winning_miner = m
                break
        if not winning_miner:
            winning_miner = list(self.miners.values())[0]

        if winning_miner.strategy != MinerType.BLOCK_WITHHOLDING:
            winning_miner.full_blocks_found += 1
        winning_miner.pool_shares_submitted += int(winning_miner.hashrate_share * 12) + self.rng.randint(2, 6)

        published_blocks: List[BlockRecord] = []
        tip = self.main_chain[-1]

        # ------------------------------------------------------------------
        # Miner Strategy Execution
        # ------------------------------------------------------------------
        if winning_miner.strategy == MinerType.HONEST:
            # Honest block publication
            b_hash = self._generate_block_hash(tip.height + 1, tip.block_hash, winning_miner.miner_id)
            prop_delay = max(0.2, self.rng.normalvariate(self.propagation_mean, 0.2))
            
            block = BlockRecord(
                block_number=len(self.main_chain) + len(self.orphaned_blocks),
                block_hash=b_hash,
                parent_hash=tip.block_hash,
                miner=winning_miner.miner_id,
                timestamp=self.current_time,
                first_seen=self.current_time + prop_delay,
                transactions=[{"tx_hash": f"0xtx_{self.rng.randint(1000, 9999)}", "miner": winning_miner.miner_id}],
                is_orphan=False,
                is_main_chain=True,
                height=tip.height + 1
            )

            # Check if selfish miner is in lead
            selfish_miner = next((m for m in self.miners.values() if m.strategy == MinerType.SELFISH), None)
            if selfish_miner and selfish_miner.lead > 0:
                if selfish_miner.lead == 1:
                    # Race condition: selfish miner publishes private block immediately
                    self.current_time += 0.05
                    private_b = selfish_miner.private_chain.pop(0)
                    private_b.first_seen = self.current_time + 0.05
                    selfish_miner.lead = 0
                    
                    if self.rng.random() < self.gamma_tie:
                        # Selfish miner wins race
                        block.is_orphan = True
                        block.is_main_chain = False
                        self.orphaned_blocks.append(block)
                        self.main_chain.append(private_b)
                        published_blocks.extend([block, private_b])
                    else:
                        # Honest miner wins race
                        private_b.is_orphan = True
                        private_b.is_main_chain = False
                        self.orphaned_blocks.append(private_b)
                        self.main_chain.append(block)
                        published_blocks.extend([block, private_b])
                elif selfish_miner.lead == 2:
                    # Selfish miner publishes all private blocks, causing reorg
                    self.current_time += 0.1
                    released = list(selfish_miner.private_chain)
                    selfish_miner.private_chain.clear()
                    selfish_miner.lead = 0
                    
                    block.is_orphan = True
                    block.is_main_chain = False
                    self.orphaned_blocks.append(block)
                    for rb in released:
                        rb.first_seen = self.current_time
                        self.main_chain.append(rb)
                    self.reorg_history.append({"depth": 2, "at_block": block.block_number, "timestamp": self.current_time})
                    published_blocks.extend([block] + released)
                else:
                    # lead > 2: publish 1 block to preserve lead
                    released_b = selfish_miner.private_chain.pop(0)
                    released_b.first_seen = self.current_time + 0.05
                    selfish_miner.lead -= 1
                    self.main_chain.append(released_b)
                    block.is_orphan = True
                    block.is_main_chain = False
                    self.orphaned_blocks.append(block)
                    published_blocks.extend([block, released_b])
            else:
                self.main_chain.append(block)
                published_blocks.append(block)

        elif winning_miner.strategy == MinerType.SELFISH:
            # Selfish mining: mine privately on top of private chain
            parent = winning_miner.private_chain[-1].block_hash if winning_miner.private_chain else tip.block_hash
            parent_height = winning_miner.private_chain[-1].height if winning_miner.private_chain else tip.height
            
            b_hash = self._generate_block_hash(parent_height + 1, parent, winning_miner.miner_id)
            private_block = BlockRecord(
                block_number=len(self.main_chain) + len(self.orphaned_blocks) + len(winning_miner.private_chain) + 1,
                block_hash=b_hash,
                parent_hash=parent,
                miner=winning_miner.miner_id,
                timestamp=self.current_time,
                first_seen=self.current_time,  # Will be updated on broadcast
                transactions=[{"tx_hash": f"0xselfish_{self.rng.randint(1000, 9999)}"}],
                is_orphan=False,
                is_main_chain=True,
                height=parent_height + 1
            )
            winning_miner.private_chain.append(private_block)
            winning_miner.lead += 1

        elif winning_miner.strategy == MinerType.BLOCK_WITHHOLDING:
            # Block withholding: intentional delay of 25-45 seconds
            withhold_delay = self.rng.uniform(20.0, 45.0)
            winning_miner.withheld_count += 1
            
            b_hash = self._generate_block_hash(tip.height + 1, tip.block_hash, winning_miner.miner_id)
            block = BlockRecord(
                block_number=len(self.main_chain) + len(self.orphaned_blocks),
                block_hash=b_hash,
                parent_hash=tip.block_hash,
                miner=winning_miner.miner_id,
                timestamp=self.current_time,
                first_seen=self.current_time + withhold_delay,  # Delayed arrival
                transactions=[{"tx_hash": f"0xdelayed_{self.rng.randint(1000, 9999)}"}],
                is_orphan=False,
                is_main_chain=True,
                height=tip.height + 1
            )
            self.main_chain.append(block)
            published_blocks.append(block)

        elif winning_miner.strategy == MinerType.COALITION_51:
            # 51% Coalition: build private fork of depth >= 4 with a double-spend
            leader = self.miners["0xcoalition_leader"]
            parent = leader.private_chain[-1].block_hash if leader.private_chain else tip.block_hash
            parent_height = leader.private_chain[-1].height if leader.private_chain else tip.height
            
            b_hash = self._generate_block_hash(parent_height + 1, parent, winning_miner.miner_id)
            block = BlockRecord(
                block_number=len(self.main_chain) + len(self.orphaned_blocks) + len(leader.private_chain) + 1,
                block_hash=b_hash,
                parent_hash=parent,
                miner=winning_miner.miner_id,
                timestamp=self.current_time,
                first_seen=self.current_time,
                transactions=[
                    # Replaced double-spend transaction sending funds back to attacker
                    {"tx_hash": "0xreorg_doublespend_tx", "sender": "0xcoalition_leader", "nonce": 5, "to": "0xcoalition_secret_stash", "value": 50.0}
                ],
                is_orphan=False,
                is_main_chain=True,
                height=parent_height + 1
            )
            leader.private_chain.append(block)
            leader.lead += 1

            # When private branch reaches depth >= 4, release all blocks to reorg public chain!
            if leader.lead >= 4:
                reorg_depth = leader.lead
                self.reorg_history.append({"depth": reorg_depth, "at_block": block.block_number, "timestamp": self.current_time})
                
                # Orphan the public chain blocks
                for _ in range(reorg_depth - 1):
                    if len(self.main_chain) > 1:
                        orphaned = self.main_chain.pop()
                        orphaned.is_orphan = True
                        orphaned.is_main_chain = False
                        self.orphaned_blocks.append(orphaned)
                        published_blocks.append(orphaned)
                
                for b in leader.private_chain:
                    b.first_seen = self.current_time
                    self.main_chain.append(b)
                    published_blocks.append(b)
                
                leader.private_chain.clear()
                leader.lead = 0

        elif winning_miner.strategy == MinerType.RACE_DOUBLE_SPEND:
            # Honest mining, but records conflicting mempool sightings
            b_hash = self._generate_block_hash(tip.height + 1, tip.block_hash, winning_miner.miner_id)
            block = BlockRecord(
                block_number=len(self.main_chain) + len(self.orphaned_blocks),
                block_hash=b_hash,
                parent_hash=tip.block_hash,
                miner=winning_miner.miner_id,
                timestamp=self.current_time,
                first_seen=self.current_time + self.propagation_mean,
                transactions=[{"tx_hash": "0xrace_confirmed_spend", "sender": "0xrace_attacker", "nonce": 1, "to": "0xrace_attacker_vault"}],
                is_orphan=False,
                is_main_chain=True,
                height=tip.height + 1
            )
            self.main_chain.append(block)
            published_blocks.append(block)

        # Record propagation timing
        for pb in published_blocks:
            self.propagation_log.record(pb.block_number, pb.miner, pb.timestamp, pb.first_seen)

        # Notify callback
        if on_block_mined:
            for pb in published_blocks:
                on_block_mined(pb, self.main_chain)

        return published_blocks

    def run_simulation(
        self,
        scenario: MinerType,
        total_blocks: int = 30,
        on_block_mined: Optional[Callable[[BlockRecord, List[BlockRecord]], None]] = None
    ) -> List[BlockRecord]:
        """Runs the simulation until total_blocks are mined."""
        self.setup_miners(scenario)
        while len(self.main_chain) < total_blocks:
            self.step(on_block_mined=on_block_mined)
        return list(self.main_chain)
