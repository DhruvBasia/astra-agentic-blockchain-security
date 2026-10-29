"""
ASTRA: Autonomous Security and Threat Response using Agentic AI for Blockchain
Module: astra_blockchain.py
Core Blockchain Simulation Engine with P2P Topology, Mempool, Cryptographic Ledger, and Node Management.
"""

import hashlib
import time
import json
import random
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Set, Optional


@dataclass
class Transaction:
    tx_id: str
    sender: str
    recipient: str
    amount: float
    fee: float
    timestamp: float
    signature: str
    is_spam: bool = False
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def create(cls, sender: str, recipient: str, amount: float, fee: float = 0.001, is_spam: bool = False, metadata: Dict = None):
        ts = time.time()
        tx_data = f"{sender}:{recipient}:{amount}:{fee}:{ts}:{random.random()}"
        tx_id = hashlib.sha256(tx_data.encode()).hexdigest()[:16]
        sig = hashlib.sha256(f"sig:{tx_id}:{sender}".encode()).hexdigest()[:24]
        return cls(
            tx_id=tx_id,
            sender=sender,
            recipient=recipient,
            amount=amount,
            fee=fee,
            timestamp=ts,
            signature=sig,
            is_spam=is_spam,
            metadata=metadata or {}
        )

    def to_dict(self):
        return asdict(self)


@dataclass
class Block:
    index: int
    previous_hash: str
    timestamp: float
    transactions: List[Transaction]
    nonce: int
    hash: str
    miner: str
    is_secret: bool = False  # Used in Finney attack withholding

    @classmethod
    def create(cls, index: int, previous_hash: str, transactions: List[Transaction], miner: str, is_secret: bool = False):
        ts = time.time()
        nonce = 0
        raw_payload = f"{index}:{previous_hash}:{ts}:{miner}:{[t.tx_id for t in transactions]}"
        while True:
            candidate_hash = hashlib.sha256(f"{raw_payload}:{nonce}".encode()).hexdigest()
            # Proof of Work difficulty: starts with 2 zeros for fast simulation demo
            if candidate_hash.startswith("00"):
                break
            nonce += 1
            if nonce > 5000:  # Bound iteration for real-time responsiveness
                break
        return cls(
            index=index,
            previous_hash=previous_hash,
            timestamp=ts,
            transactions=transactions,
            nonce=nonce,
            hash=candidate_hash,
            miner=miner,
            is_secret=is_secret
        )

    def to_dict(self):
        d = asdict(self)
        d['transactions'] = [t.to_dict() for t in self.transactions]
        return d


@dataclass
class Node:
    node_id: str
    ip_address: str
    asn: str
    stake: float
    status: str  # "HONEST", "SYBIL", "MALICIOUS_MINER", "ATTACK_WALLET", "ECLIPSED_TARGET", "QUARANTINED"
    peers: List[str] = field(default_factory=list)
    trust_factor: float = 0.5
    is_admitted: bool = False
    joined_at: float = field(default_factory=time.time)
    reputation_score: float = 0.5
    subnet: str = ""

    def __post_init__(self):
        if not self.subnet and self.ip_address:
            parts = self.ip_address.split(".")
            if len(parts) >= 3:
                self.subnet = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
            else:
                self.subnet = "192.168.1.0/24"

    def to_dict(self):
        return asdict(self)


class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.mempool: List[Transaction] = []
        self.nodes: Dict[str, Node] = {}
        self.pending_admissions: List[Node] = []
        self.balances: Dict[str, float] = {}
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_tx = Transaction.create(
            sender="GENESIS_SYSTEM",
            recipient="NODE_01",
            amount=1000.0,
            fee=0.0
        )
        genesis_block = Block(
            index=0,
            previous_hash="0" * 64,
            timestamp=time.time(),
            transactions=[genesis_tx],
            nonce=0,
            hash="0000genesis_hash_" + "0" * 48,
            miner="GENESIS_MINER"
        )
        self.chain.append(genesis_block)
        self.balances["GENESIS_SYSTEM"] = 10000.0
        self.balances["NODE_01"] = 1000.0

    @property
    def latest_block(self) -> Block:
        return self.chain[-1]

    def register_node(self, node: Node, direct_admit: bool = False) -> bool:
        if direct_admit:
            node.is_admitted = True
            self.nodes[node.node_id] = node
            return True
        else:
            self.pending_admissions.append(node)
            return False

    def admit_node(self, node_id: str, trust_factor: float):
        for idx, node in enumerate(self.pending_admissions):
            if node.node_id == node_id:
                node.is_admitted = True
                node.trust_factor = trust_factor
                self.nodes[node_id] = node
                self.pending_admissions.pop(idx)
                # Form initial honest peer connections
                self.connect_to_peers(node_id, min_peers=3)
                return node
        return None

    def reject_node(self, node_id: str, reason: str = "TF < TV"):
        for idx, node in enumerate(self.pending_admissions):
            if node.node_id == node_id:
                node.is_admitted = False
                node.status = "QUARANTINED"
                rejected = self.pending_admissions.pop(idx)
                return rejected
        return None

    def connect_to_peers(self, node_id: str, min_peers: int = 3):
        if node_id not in self.nodes:
            return
        available = [nid for nid in self.nodes if nid != node_id and self.nodes[nid].status == "HONEST"]
        chosen = random.sample(available, min(len(available), min_peers))
        for p in chosen:
            if p not in self.nodes[node_id].peers:
                self.nodes[node_id].peers.append(p)
            if node_id not in self.nodes[p].peers:
                self.nodes[p].peers.append(node_id)

    def submit_transaction(self, tx: Transaction) -> bool:
        self.mempool.append(tx)
        return True

    def mine_pending_block(self, miner_id: str, is_secret: bool = False) -> Optional[Block]:
        if not self.mempool and not is_secret:
            return None
        
        # Take up to 10 transactions from mempool
        txs_to_mine = self.mempool[:10]
        self.mempool = self.mempool[10:]
        
        block = Block.create(
            index=len(self.chain),
            previous_hash=self.latest_block.hash,
            transactions=txs_to_mine,
            miner=miner_id,
            is_secret=is_secret
        )
        
        if not is_secret:
            self.chain.append(block)
            # Update balances
            for tx in txs_to_mine:
                self.balances[tx.sender] = self.balances.get(tx.sender, 100.0) - (tx.amount + tx.fee)
                self.balances[tx.recipient] = self.balances.get(tx.recipient, 0.0) + tx.amount
        return block

    def get_network_graph(self) -> Dict:
        """Returns nodes and edges suitable for graph visualization"""
        nodes_data = []
        edges_data = []
        for nid, node in self.nodes.items():
            nodes_data.append({
                "id": nid,
                "status": node.status,
                "trust_factor": round(node.trust_factor, 3),
                "ip": node.ip_address,
                "peers_count": len(node.peers)
            })
            for peer in node.peers:
                if nid < peer:  # Avoid duplicate undirected edges
                    edges_data.append({"source": nid, "target": peer})
        return {"nodes": nodes_data, "edges": edges_data}
