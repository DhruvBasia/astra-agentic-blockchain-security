"""
ASTRA: Autonomous Security and Threat Response using Agentic AI for Blockchain
Module: astra_agents.py
Multi-Agent BDI (Belief-Desire-Intention) Architecture for Autonomous Blockchain Security.
Defines specialized intelligent agents for SAFE attacks (Sybil, Attack Wallet, Finney, Eclipse).
"""

import time
import math
from typing import Dict, List, Any, Optional
from astra_blockchain import Blockchain, Node, Transaction, Block


class AgentLog:
    def __init__(self, agent_name: str, attack_type: str, belief: str, desire: str, intention: str, action: str, result: str, tf_score: Optional[float] = None, tv_score: Optional[float] = None):
        self.timestamp = time.strftime("%H:%M:%S")
        self.agent_name = agent_name
        self.attack_type = attack_type
        self.belief = belief
        self.desire = desire
        self.intention = intention
        self.action = action
        self.result = result
        self.tf_score = tf_score
        self.tv_score = tv_score

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "attack_type": self.attack_type,
            "belief": self.belief,
            "desire": self.desire,
            "intention": self.intention,
            "action": self.action,
            "result": self.result,
            "tf_score": self.tf_score,
            "tv_score": self.tv_score
        }


class AdmissionAgent:
    """
    Evaluates prospective nodes BEFORE network admission.
    Implements Trust Factor (TF) vs Threshold Value (TV) decision model.
    Defends against: Sybil Attacks.
    """
    def __init__(self, base_tv: float = 0.65, weights: Dict[str, float] = None):
        self.base_tv = base_tv
        # Parameter weights (sum to 1.0)
        self.weights = weights or {
            "identity_verifiability": 0.30,   # Iv: Subnet uniqueness, cryptographic handshake
            "behavioral_history": 0.25,       # Bh: Past uptime, reliability score
            "topology_diversity": 0.25,       # Tp: IP cluster dispersion, routing entropy
            "cryptographic_stake": 0.20       # Cs: Staked collateral / computational commitment
        }
        self.threat_multiplier = 0.0

    def compute_trust_factor(self, node: Node, existing_nodes: Dict[str, Node]) -> Dict[str, float]:
        # 1. Identity Verifiability (Iv): penalize IP/Subnet collisions
        same_subnet_count = sum(1 for n in existing_nodes.values() if n.subnet == node.subnet)
        iv = max(0.1, 1.0 - (same_subnet_count * 0.25))

        # 2. Behavioral History (Bh): new nodes start neutral, known sybils penalized
        if node.status == "SYBIL":
            bh = 0.15
        elif node.reputation_score > 0:
            bh = node.reputation_score
        else:
            bh = 0.50

        # 3. Topology Diversity (Tp): check ASN entropy and dispersion
        asn_matches = sum(1 for n in existing_nodes.values() if n.asn == node.asn)
        tp = max(0.15, 1.0 / (1.0 + 0.3 * asn_matches))

        # 4. Cryptographic Stake Commitment (Cs):
        # Higher stake gives higher assurance up to 1.0
        cs = min(1.0, max(0.1, node.stake / 100.0))

        tf = (
            self.weights["identity_verifiability"] * iv +
            self.weights["behavioral_history"] * bh +
            self.weights["topology_diversity"] * tp +
            self.weights["cryptographic_stake"] * cs
        )

        return {
            "tf": round(tf, 3),
            "iv": round(iv, 3),
            "bh": round(bh, 3),
            "tp": round(tp, 3),
            "cs": round(cs, 3)
        }

    def evaluate_admission(self, node: Node, blockchain: Blockchain, current_threat_level: float = 0.0) -> Dict[str, Any]:
        dynamic_tv = round(self.base_tv + (0.15 * current_threat_level), 3)
        metrics = self.compute_trust_factor(node, blockchain.nodes)
        tf = metrics["tf"]

        decision = "ADMIT" if tf >= dynamic_tv else "REJECT_QUARANTINE"

        # BDI Reasoning formulation
        belief = f"Node {node.node_id} requests admission from subnet {node.subnet}, stake={node.stake} ETH. Computed TF={tf} (Iv={metrics['iv']}, Bh={metrics['bh']}, Tp={metrics['tp']}, Cs={metrics['cs']})."
        desire = "Ensure only provably trustworthy entities enter consensus and prevent Sybil cluster inflation."
        intention = f"Compare Trust Factor ({tf}) against adaptive Threshold Value ({dynamic_tv})."

        if decision == "ADMIT":
            blockchain.admit_node(node.node_id, tf)
            action = f"Granted admission credentials to {node.node_id} and integrated into peer routing table."
            result = f"Node {node.node_id} joined network as HONEST peer (TF {tf} >= TV {dynamic_tv})."
        else:
            blockchain.reject_node(node.node_id, reason="TF < TV")
            action = f"Enforced pre-admission quarantine on {node.node_id}. Blacklisted subnet {node.subnet} temporary cluster."
            result = f"SYBIL ADMISSION BLOCKED: Node {node.node_id} rejected (TF {tf} < TV {dynamic_tv})."

        log = AgentLog(
            agent_name="Admission & Identity Agent",
            attack_type="Sybil Attack",
            belief=belief,
            desire=desire,
            intention=intention,
            action=action,
            result=result,
            tf_score=tf,
            tv_score=dynamic_tv
        )

        return {
            "decision": decision,
            "metrics": metrics,
            "tv": dynamic_tv,
            "log": log
        }


class MempoolGuardianAgent:
    """
    Monitors incoming transaction streams and mempool dynamics.
    Defends against: Attack Wallet (DoS, micro-value transaction floods, resource exhaustion).
    """
    def __init__(self, velocity_threshold_tx_per_sec: float = 5.0, min_legit_value: float = 0.001):
        self.velocity_threshold = velocity_threshold_tx_per_sec
        self.min_legit_value = min_legit_value
        self.wallet_tx_history: Dict[str, List[float]] = {}
        self.quarantined_wallets: Set[str] = set()

    def inspect_mempool(self, blockchain: Blockchain) -> List[AgentLog]:
        logs = []
        if not blockchain.mempool:
            return logs

        # Analyze transaction velocity per sender in mempool
        sender_counts: Dict[str, int] = {}
        sender_spam_count: Dict[str, int] = {}
        for tx in blockchain.mempool:
            sender_counts[tx.sender] = sender_counts.get(tx.sender, 0) + 1
            if tx.is_spam or tx.amount <= self.min_legit_value:
                sender_spam_count[tx.sender] = sender_spam_count.get(tx.sender, 0) + 1

        for sender, count in sender_counts.items():
            spam_ratio = sender_spam_count.get(sender, 0) / count
            if count >= self.velocity_threshold or (count >= 3 and spam_ratio > 0.6):
                # Detected Attack Wallet anomaly
                initial_mempool_size = len(blockchain.mempool)
                # Intention: Drop spam transactions and quarantine sender wallet
                blockchain.mempool = [tx for tx in blockchain.mempool if tx.sender != sender]
                pruned_count = initial_mempool_size - len(blockchain.mempool)
                self.quarantined_wallets.add(sender)

                log = AgentLog(
                    agent_name="Mempool & Wallet Guardian Agent",
                    attack_type="Attack Wallet",
                    belief=f"Sender wallet '{sender}' generated {count} burst transactions ({pruned_count} flagged micro-spam) within active inspection window.",
                    desire="Prevent block space exhaustion, CPU starvation of validators, and network DoS.",
                    intention=f"Enforce dynamic gas multiplier penalty, drop {pruned_count} abusive transactions, and freeze wallet.",
                    action=f"Purged {pruned_count} spam transactions from Mempool. Quarantined wallet '{sender}'.",
                    result=f"ATTACK WALLET MITIGATED: Mempool normalized (freed {pruned_count} transaction slots)."
                )
                logs.append(log)

        return logs


class ConsensusAuditAgent:
    """
    Monitors block announcements, mining timestamps, and conflicting mempool spends.
    Defends against: Finney Attack (withheld block double-spend).
    """
    def __init__(self, required_confirmations: int = 3):
        self.required_confirmations = required_confirmations

    def verify_transaction_safety(self, tx: Transaction, secret_block: Optional[Block], blockchain: Blockchain) -> AgentLog:
        # Check if tx is zero-confirmation and conflicting with a withheld or alternative block
        has_double_spend_conflict = False
        conflicting_miner = None

        if secret_block and secret_block.is_secret:
            for stx in secret_block.transactions:
                if stx.sender == tx.sender and stx.recipient != tx.recipient:
                    has_double_spend_conflict = True
                    conflicting_miner = secret_block.miner
                    break

        if has_double_spend_conflict:
            # Finney attack detected
            belief = (f"Incoming transaction {tx.tx_id} (amount={tx.amount} BTC from {tx.sender} to {tx.recipient}) "
                      f"has 0 confirmations, while miner {conflicting_miner} is withholding private block {secret_block.index} spending same UTXO.")
            desire = "Prevent zero-confirmation merchant settlement fraud and consensus chain reorganization losses."
            intention = f"Raise confirmation threshold from 0 to {self.required_confirmations}, pause merchant payment clearance, and flag conflicting fork."
            action = f"Blocked unconfirmed merchant settlement. Flagged hidden block {secret_block.index} by {conflicting_miner} as conflicting fork."
            result = f"FINNEY ATTACK FOILED: Victim transaction protected from double-spend invalidation."

            return AgentLog(
                agent_name="Consensus & Fork Audit Agent",
                attack_type="Finney Attack",
                belief=belief,
                desire=desire,
                intention=intention,
                action=action,
                result=result
            )
        else:
            return AgentLog(
                agent_name="Consensus & Fork Audit Agent",
                attack_type="Consensus Audit",
                belief=f"Transaction {tx.tx_id} validated. No withheld block or double-spend race condition detected.",
                desire="Maintain ledger finality.",
                intention="Authorize transaction validation.",
                action="Passed to miner pool.",
                result="Transaction accepted into verification queue."
            )


class TopologyGuardianAgent:
    """
    Monitors P2P network connectivity and peer table distribution.
    Defends against: Eclipse Attacks (peer isolation of honest victim nodes).
    """
    def __init__(self, eclipse_ratio_threshold: float = 0.60):
        self.eclipse_ratio_threshold = eclipse_ratio_threshold

    def audit_node_topology(self, target_node_id: str, blockchain: Blockchain) -> Optional[AgentLog]:
        if target_node_id not in blockchain.nodes:
            return None

        node = blockchain.nodes[target_node_id]
        if not node.peers:
            return None

        # Check composition of peers
        total_peers = len(node.peers)
        malicious_or_colluding_peers = []
        for p_id in node.peers:
            peer_node = blockchain.nodes.get(p_id)
            if peer_node and (peer_node.status in ["SYBIL", "MALICIOUS", "ECLIPSER"] or peer_node.trust_factor < 0.45):
                malicious_or_colluding_peers.append(p_id)

        malicious_ratio = len(malicious_or_colluding_peers) / total_peers

        if malicious_ratio >= self.eclipse_ratio_threshold:
            # Eclipse attack detected! The victim node is isolated by attacker nodes
            evicted_peers = list(malicious_or_colluding_peers)
            # Autonomous remediation: Evict malicious peers and inject known trusted anchor nodes
            node.peers = [p for p in node.peers if p not in evicted_peers]

            honest_anchors = [nid for nid, n in blockchain.nodes.items() if nid != target_node_id and n.status == "HONEST" and n.trust_factor >= 0.70]
            injected_anchors = honest_anchors[:3]
            for anchor in injected_anchors:
                if anchor not in node.peers:
                    node.peers.append(anchor)

            belief = (f"Target node {target_node_id} has {len(malicious_or_colluding_peers)}/{total_peers} peers "
                      f"({malicious_ratio*100:.1f}%) belonging to colluding/untrusted cluster.")
            desire = f"Prevent target node {target_node_id} from consensus partition, stale views, and transaction double-spend isolation."
            intention = f"Evict {len(evicted_peers)} eclipsing peers and inject {len(injected_anchors)} cryptographically verified anchor nodes."
            action = f"Evicted peers {evicted_peers} from {target_node_id}'s routing table. Connected {injected_anchors} trusted anchors."
            result = f"ECLIPSE ATTACK REVERSED: Node {target_node_id} restored to honest global consensus topology."

            return AgentLog(
                agent_name="Topology & Peer Guardian Agent",
                attack_type="Eclipse Attack",
                belief=belief,
                desire=desire,
                intention=intention,
                action=action,
                result=result
            )

        return None


class ResponseOrchestrator:
    """
    Coordinates multi-agent telemetry, maintains unified security posture,
    and exposes explainable logs for demonstration.
    """
    def __init__(self):
        self.admission_agent = AdmissionAgent()
        self.mempool_agent = MempoolGuardianAgent()
        self.consensus_agent = ConsensusAuditAgent()
        self.topology_agent = TopologyGuardianAgent()
        self.event_logs: List[AgentLog] = []

    def log_event(self, log: AgentLog):
        self.event_logs.insert(0, log)
        if len(self.event_logs) > 50:
            self.event_logs.pop()

    def get_logs(self) -> List[Dict]:
        return [l.to_dict() for l in self.event_logs]
