"""
Scenario Generator for ASTRA.
Builds realistic background blockchain traffic and synthesizes candidate nodes
with ground truth labels (hidden from agents) across honest, hard-negative, and attack classes.
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from astra.blockchain.backend import ChainBackend
from astra.network.peer_registry import PeerRegistry, PeerProfile, PeerNode
from astra.network.mempool import MempoolLog
from astra.network.propagation import BlockPropagationLog


@dataclass
class ScenarioCandidate:
    candidate_id: str
    wallet_address: str
    candidate_type: str            # e.g., 'honest', 'sybil', 'malicious_wallet', 'finney', 'eclipse', 'sleeper'
    label: str                     # 'HONEST' or 'ATTACK'
    peer_profile: PeerProfile
    mined_blocks: List[int] = field(default_factory=list)
    related_cluster: List[str] = field(default_factory=list)
    is_attacker: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScenarioGenerator:
    """Generates reproducible multi-agent evaluation environments."""

    def __init__(self, seed: int = 42, exchange_balance_eth: float = 400.0):
        self.seed = seed
        self.rng = random.Random(seed)
        # Each exchange hub must be able to fund every candidate it is asked to fund;
        # a 120-candidate benchmark draws roughly 130 ETH in total across the two hubs.
        self.exchange_balance_eth = exchange_balance_eth
        self.exchanges: List[str] = []
        self.organic_users: List[str] = []

    def populate_background(
        self,
        chain: ChainBackend,
        peer_registry: PeerRegistry,
        mempool_log: MempoolLog,
        propagation_log: BlockPropagationLog
    ) -> None:
        """Sets up organic background exchange activity and normal user transfers."""
        # 1. Create 2 designated exchange funding hubs
        self.exchanges = [
            chain.create_account(initial_balance_eth=self.exchange_balance_eth),
            chain.create_account(initial_balance_eth=self.exchange_balance_eth)
        ]

        # 2. Fund 10 organic users at varied times
        self.organic_users = []
        for i in range(10):
            u_addr = chain.create_account(initial_balance_eth=0.0)
            self.organic_users.append(u_addr)
            
            ex = self.rng.choice(self.exchanges)
            val = round(self.rng.uniform(0.3, 0.8), 3)
            # Advance time organically
            chain.advance_time(self.rng.uniform(600.0, 7200.0))  # 10 min to 2 hours
            chain.send(sender=ex, to=u_addr, value_eth=val)

        # 3. Organic transfers between users
        for _ in range(15):
            s = self.rng.choice(self.organic_users)
            r = self.rng.choice([u for u in self.organic_users if u != s])
            amt = round(self.rng.uniform(0.01, 0.04), 3)
            chain.advance_time(self.rng.uniform(30.0, 300.0))
            chain.send(sender=s, to=r, value_eth=amt)

    def create_candidate(
        self,
        candidate_type: str,
        candidate_id: str,
        chain: ChainBackend,
        peer_registry: PeerRegistry,
        mempool_log: MempoolLog,
        propagation_log: BlockPropagationLog
    ) -> ScenarioCandidate:
        c_type = candidate_type.lower()
        now = chain.now()
        tip = chain.block_number()

        # ==================================================================
        # 1. HONEST
        # ==================================================================
        if c_type == "honest":
            c_addr = chain.create_account(initial_balance_eth=0.0)
            ex = self.rng.choice(self.exchanges) if self.exchanges else chain.create_account(initial_balance_eth=10.0)
            # Funded 45 days ago
            chain.advance_time(45.0 * 86400.0)
            chain.send(sender=ex, to=c_addr, value_eth=1.5)
            # Clean organic history
            for _ in range(5):
                chain.advance_time(self.rng.uniform(3600.0, 86400.0))
                other = self.rng.choice(self.organic_users) if self.organic_users else chain.create_account()
                chain.send(sender=c_addr, to=other, value_eth=round(self.rng.uniform(0.02, 0.08), 3))

            profile = peer_registry.create_honest_peer_profile(candidate_id, peer_count=8, current_tip=tip)
            return ScenarioCandidate(
                candidate_id=candidate_id,
                wallet_address=c_addr,
                candidate_type="honest",
                label="HONEST",
                peer_profile=profile,
                is_attacker=False
            )

        # ==================================================================
        # 2. HARD NEGATIVE: HONEST POWER USER
        # Busy user, high volume, varied counterparties, legitimate transactions
        # ==================================================================
        elif c_type == "honest_power_user":
            c_addr = chain.create_account(initial_balance_eth=0.0)
            ex = self.rng.choice(self.exchanges) if self.exchanges else chain.create_account(initial_balance_eth=15.0)
            chain.advance_time(90.0 * 86400.0)
            chain.send(sender=ex, to=c_addr, value_eth=3.0)
            # 15 varied transfers
            for _ in range(15):
                chain.advance_time(self.rng.uniform(60.0, 900.0))
                other = self.rng.choice(self.organic_users) if self.organic_users else chain.create_account()
                chain.send(sender=c_addr, to=other, value_eth=round(self.rng.uniform(0.02, 0.08), 3))

            profile = peer_registry.create_honest_peer_profile(candidate_id, peer_count=12, current_tip=tip)
            return ScenarioCandidate(
                candidate_id=candidate_id,
                wallet_address=c_addr,
                candidate_type="honest_power_user",
                label="HONEST",
                peer_profile=profile,
                is_attacker=False
            )

        # ==================================================================
        # 3. HARD NEGATIVE: HONEST SINGLE CLOUD ASN
        # Legitimate node hosted in single datacenter (e.g. AWS), connected to backbone
        # ==================================================================
        elif c_type == "honest_single_cloud":
            c_addr = chain.create_account(initial_balance_eth=0.0)
            ex = self.rng.choice(self.exchanges) if self.exchanges else chain.create_account(initial_balance_eth=10.0)
            chain.advance_time(35.0 * 86400.0)
            chain.send(sender=ex, to=c_addr, value_eth=1.5)

            peers = []
            for i in range(6):
                peers.append(PeerNode(
                    node_id=f"AWS_BACKBONE_PEER_{i}",
                    ip=f"54.210.10.{i + 5}",
                    subnet="54.210.0.0/16",
                    asn="AS16509",  # Single AWS ASN
                    connection_age_days=self.rng.uniform(30.0, 100.0),
                    reported_height=tip,
                    is_backbone=True
                ))
            profile = PeerProfile(candidate_id=candidate_id, peers=peers, sampled_at_tip=tip)
            return ScenarioCandidate(
                candidate_id=candidate_id,
                wallet_address=c_addr,
                candidate_type="honest_single_cloud",
                label="HONEST",
                peer_profile=profile,
                is_attacker=False
            )

        # ==================================================================
        # 4. HARD NEGATIVE: HONEST FEE BUMPER
        # User who replaces unconfirmed transaction with higher fee to SAME recipient
        # ==================================================================
        elif c_type == "honest_fee_bumper":
            c_addr = chain.create_account(initial_balance_eth=0.0)
            ex = self.rng.choice(self.exchanges) if self.exchanges else chain.create_account(initial_balance_eth=10.0)
            chain.advance_time(40.0 * 86400.0)
            chain.send(sender=ex, to=c_addr, value_eth=1.5)

            merchant = self.rng.choice(self.organic_users) if self.organic_users else chain.create_account()
            # 1. Unconfirmed mempool tx with low fee
            nonce = chain.tx_count(c_addr)
            tx_low = chain.sign_only(sender=c_addr, to=merchant, value_eth=0.1, nonce=nonce)
            mempool_log.record(
                tx_hash=tx_low.tx_hash,
                sender=c_addr,
                nonce=nonce,
                to=merchant,
                value_eth=0.1,
                fee_eth=0.0001,
                seen_at=chain.now()
            )
            # 2. Replaced with higher fee to SAME recipient on chain
            chain.advance_time(15.0)
            tx_high = chain.send(sender=c_addr, to=merchant, value_eth=0.1, nonce=nonce)
            mempool_log.mark_mined(tx_high.tx_hash)

            profile = peer_registry.create_honest_peer_profile(candidate_id, peer_count=8, current_tip=tip)
            return ScenarioCandidate(
                candidate_id=candidate_id,
                wallet_address=c_addr,
                candidate_type="honest_fee_bumper",
                label="HONEST",
                peer_profile=profile,
                is_attacker=False
            )

        # ==================================================================
        # 5. SYBIL ATTACK
        # Burst-funded cluster with circular transfers, identical amounts
        # ==================================================================
        elif c_type == "sybil":
            funder = chain.create_account(initial_balance_eth=2.0)
            c_addr = chain.create_account(initial_balance_eth=0.0)
            siblings = [chain.create_account(initial_balance_eth=0.0) for _ in range(3)]
            cluster = [c_addr] + siblings

            # Burst funding within 60 seconds with identical 0.2 ETH
            chain.send(sender=funder, to=c_addr, value_eth=0.2)
            for s in siblings:
                chain.advance_time(self.rng.uniform(5.0, 25.0))
                chain.send(sender=funder, to=s, value_eth=0.2)

            # Circular transfers among cluster
            for i in range(len(cluster)):
                src = cluster[i]
                dst = cluster[(i + 1) % len(cluster)]
                chain.advance_time(self.rng.uniform(10.0, 30.0))
                chain.send(sender=src, to=dst, value_eth=0.01)

            profile = peer_registry.create_honest_peer_profile(candidate_id, peer_count=4, current_tip=tip)
            return ScenarioCandidate(
                candidate_id=candidate_id,
                wallet_address=c_addr,
                candidate_type="sybil",
                label="ATTACK",
                peer_profile=profile,
                related_cluster=cluster,
                is_attacker=True
            )

        # ==================================================================
        # 6. STEALTHY SYBIL
        # Funding routed through intermediate hop, spread over hours
        # ==================================================================
        elif c_type == "stealthy_sybil":
            origin = chain.create_account(initial_balance_eth=2.0)
            hop = chain.create_account(initial_balance_eth=0.0)
            c_addr = chain.create_account(initial_balance_eth=0.0)
            sib = chain.create_account(initial_balance_eth=0.0)

            chain.send(sender=origin, to=hop, value_eth=1.5)
            chain.advance_time(1200.0)
            chain.send(sender=hop, to=c_addr, value_eth=0.35)
            chain.advance_time(2400.0)
            chain.send(sender=hop, to=sib, value_eth=0.40)

            profile = peer_registry.create_honest_peer_profile(candidate_id, peer_count=6, current_tip=tip)
            return ScenarioCandidate(
                candidate_id=candidate_id,
                wallet_address=c_addr,
                candidate_type="stealthy_sybil",
                label="ATTACK",
                peer_profile=profile,
                related_cluster=[hop, sib],
                is_attacker=True
            )

        # ==================================================================
        # 7. MALICIOUS WALLET
        # Bot bursts (<10s inter-arrival), dusting, repeated transfers, failing txs
        # ==================================================================
        elif c_type == "malicious_wallet":
            funder = chain.create_account(initial_balance_eth=1.5)
            c_addr = chain.create_account(initial_balance_eth=0.0)
            chain.send(sender=funder, to=c_addr, value_eth=1.0)

            # Rapid bot burst: 8 transactions < 5s apart, dusting and failing
            fresh_recipients = [chain.create_account() for _ in range(5)]
            for i in range(8):
                chain.advance_time(self.rng.uniform(1.0, 4.0))  # Burst < 10s
                dst = self.rng.choice(fresh_recipients)
                is_fail = (i % 2 == 1)  # 50% failure rate
                chain.send(sender=c_addr, to=dst, value_eth=0.0001, fail=is_fail)

            profile = peer_registry.create_honest_peer_profile(candidate_id, peer_count=6, current_tip=tip)
            return ScenarioCandidate(
                candidate_id=candidate_id,
                wallet_address=c_addr,
                candidate_type="malicious_wallet",
                label="ATTACK",
                peer_profile=profile,
                is_attacker=True
            )

        # ==================================================================
        # 8. FINNEY ATTACK
        # Secret block self-transfer mined, merchant payment at same nonce, block withheld
        # ==================================================================
        elif c_type == "finney":
            funder = chain.create_account(initial_balance_eth=2.0)
            c_addr = chain.create_account(initial_balance_eth=0.0)
            attacker_stash = chain.create_account(initial_balance_eth=0.0)
            merchant = chain.create_account(initial_balance_eth=0.0)

            chain.advance_time(30.0 * 86400.0)
            chain.send(sender=funder, to=c_addr, value_eth=1.5)

            nonce = chain.tx_count(c_addr)

            # Step 1: Pre-mine block K privately transferring coins to attacker_stash
            secret_time = chain.now()
            tx_secret = chain.send(sender=c_addr, to=attacker_stash, value_eth=0.4, nonce=nonce)
            mined_block = tx_secret.block_number

            # Step 2: Merchant payment broadcast to mempool at SAME nonce
            chain.advance_time(10.0)
            sighting_time = chain.now()
            tx_merchant = chain.sign_only(sender=c_addr, to=merchant, value_eth=0.4, nonce=nonce)
            mempool_log.record(
                tx_hash=tx_merchant.tx_hash,
                sender=c_addr,
                nonce=nonce,
                to=merchant,
                value_eth=0.4,
                fee_eth=0.0002,
                seen_at=sighting_time
            )

            # Step 3: Secret block published with 25s withholding delay
            if mined_block is not None:
                first_seen = sighting_time + 15.0
                propagation_log.record(mined_block, c_addr, secret_time, first_seen)

            profile = peer_registry.create_honest_peer_profile(candidate_id, peer_count=7, current_tip=tip)
            return ScenarioCandidate(
                candidate_id=candidate_id,
                wallet_address=c_addr,
                candidate_type="finney",
                label="ATTACK",
                peer_profile=profile,
                mined_blocks=[mined_block] if mined_block else [],
                is_attacker=True
            )

        # ==================================================================
        # 9. ECLIPSE ATTACK
        # Peers concentrated in 1-2 attacker ASNs, fresh connections, lagging tip
        # ==================================================================
        elif c_type == "eclipse":
            c_addr = chain.create_account(initial_balance_eth=0.0)
            ex = self.rng.choice(self.exchanges) if self.exchanges else chain.create_account(initial_balance_eth=10.0)
            chain.advance_time(30.0 * 86400.0)
            chain.send(sender=ex, to=c_addr, value_eth=1.0)

            # Eclipsed peer table: 8 peers in AS99999_BOTNET, lag 12 blocks
            profile = peer_registry.create_eclipse_peer_profile(
                candidate_id=candidate_id,
                attacker_asn="AS99999_BOTNET",
                peer_count=8,
                lag_blocks=12,
                current_tip=tip
            )
            return ScenarioCandidate(
                candidate_id=candidate_id,
                wallet_address=c_addr,
                candidate_type="eclipse",
                label="ATTACK",
                peer_profile=profile,
                is_attacker=True
            )

        # ==================================================================
        # 10. PARTIAL ECLIPSE
        # 5 out of 7 peers in attacker ASN
        # ==================================================================
        elif c_type == "partial_eclipse":
            c_addr = chain.create_account(initial_balance_eth=0.0)
            ex = self.rng.choice(self.exchanges) if self.exchanges else chain.create_account(initial_balance_eth=10.0)
            chain.advance_time(30.0 * 86400.0)
            chain.send(sender=ex, to=c_addr, value_eth=1.0)

            base = peer_registry.create_honest_peer_profile(candidate_id, peer_count=2, current_tip=tip)
            ecl = peer_registry.create_eclipse_peer_profile(candidate_id, attacker_asn="AS88888_COLLUDING", peer_count=5, lag_blocks=4, current_tip=tip)
            profile = PeerProfile(candidate_id=candidate_id, peers=base.peers + ecl.peers, sampled_at_tip=tip)

            return ScenarioCandidate(
                candidate_id=candidate_id,
                wallet_address=c_addr,
                candidate_type="partial_eclipse",
                label="ATTACK",
                peer_profile=profile,
                is_attacker=True
            )

        # ==================================================================
        # 11. SLEEPER NODE
        # Completely clean at admission, but goes rogue after 4 transactions
        # ==================================================================
        elif c_type == "sleeper":
            c_addr = chain.create_account(initial_balance_eth=0.0)
            ex = self.rng.choice(self.exchanges) if self.exchanges else chain.create_account(initial_balance_eth=10.0)
            chain.advance_time(50.0 * 86400.0)
            chain.send(sender=ex, to=c_addr, value_eth=2.5)

            # Related cluster that will be activated post-admission
            sleeper_sybil_ally = chain.create_account(initial_balance_eth=0.0)

            profile = peer_registry.create_honest_peer_profile(candidate_id, peer_count=8, current_tip=tip)
            return ScenarioCandidate(
                candidate_id=candidate_id,
                wallet_address=c_addr,
                candidate_type="sleeper",
                label="ATTACK",  # Ground truth attacker (sleeper)
                peer_profile=profile,
                related_cluster=[sleeper_sybil_ally],
                is_attacker=True
            )

        else:
            raise ValueError(f"Unknown candidate type: {candidate_type}")
