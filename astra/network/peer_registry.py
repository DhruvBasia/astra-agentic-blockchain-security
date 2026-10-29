"""
Simulated Network Layer: PeerRegistry, PeerProfile, and NetworkX P2P overlay graph.
Maintains a diverse honest backbone and evaluates network topology and isolation.
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import networkx as nx


@dataclass
class PeerNode:
    """Represents a peer in the blockchain network."""
    node_id: str
    ip: str
    subnet: str
    asn: str
    connection_age_days: float
    reported_height: int
    is_backbone: bool = False


@dataclass
class PeerProfile:
    """The peer connection table of a candidate joining node."""
    candidate_id: str
    peers: List[PeerNode] = field(default_factory=list)
    # Chain tip at the moment the peer table was sampled. Reported heights are
    # compared against this, not against the live tip, so a table sampled long
    # before evaluation does not make every peer look stale.
    sampled_at_tip: Optional[int] = None

    @property
    def peer_count(self) -> int:
        return len(self.peers)

    @property
    def asns(self) -> List[str]:
        return [p.asn for p in self.peers]

    @property
    def subnets(self) -> List[str]:
        return [p.subnet for p in self.peers]


class PeerRegistry:
    """
    Simulated P2P network registry with an honest backbone and NetworkX topology graph.
    """

    HONEST_ASNS = [
        "AS15169",  # Google
        "AS16509",  # Amazon AWS
        "AS13335",  # Cloudflare
        "AS8075",   # Microsoft
        "AS701",    # Verizon
        "AS3356",   # Level 3
        "AS1299",   # Telia
        "AS6939",   # Hurricane Electric
        "AS32934",  # Fastly
        "AS209"     # CenturyLink
    ]

    def __init__(self, backbone_size: int = 50, seed: int = 42):
        self.rng = random.Random(seed)
        self.backbone_nodes: Dict[str, PeerNode] = {}
        self.graph: nx.Graph = nx.Graph()
        self._build_backbone(backbone_size)

    def _build_backbone(self, size: int) -> None:
        """Constructs an interconnected honest backbone with high ASN and subnet diversity."""
        for i in range(size):
            nid = f"BACKBONE_{i:03d}"
            asn = self.HONEST_ASNS[i % len(self.HONEST_ASNS)]
            oct1 = 100 + (i % 50)
            oct2 = (i * 7) % 250
            subnet = f"{oct1}.{oct2}.0.0/16"
            ip = f"{oct1}.{oct2}.{self.rng.randint(1, 254)}.{self.rng.randint(1, 254)}"
            age = self.rng.uniform(60.0, 365.0)  # Established nodes
            height = 1000

            node = PeerNode(
                node_id=nid,
                ip=ip,
                subnet=subnet,
                asn=asn,
                connection_age_days=age,
                reported_height=height,
                is_backbone=True
            )
            self.backbone_nodes[nid] = node
            self.graph.add_node(nid, asn=asn, subnet=subnet, is_backbone=True)

        # Connect backbone using a connected small-world graph
        node_ids = list(self.backbone_nodes.keys())
        for i, u in enumerate(node_ids):
            # Connect to adjacent 4 peers to ensure ring connectivity
            for j in range(1, 4):
                v = node_ids[(i + j) % len(node_ids)]
                self.graph.add_edge(u, v)
            # Add random cross-links
            if self.rng.random() < 0.3:
                rand_peer = self.rng.choice(node_ids)
                if rand_peer != u:
                    self.graph.add_edge(u, rand_peer)

    def create_honest_peer_profile(self, candidate_id: str, peer_count: int = 8, current_tip: int = 1000) -> PeerProfile:
        """Generates a healthy, well-diversified peer profile connected to backbone."""
        selected_backbone = self.rng.sample(list(self.backbone_nodes.values()), k=min(peer_count, len(self.backbone_nodes)))
        peers = []
        for p in selected_backbone:
            # Slight jitter in connection age
            peers.append(PeerNode(
                node_id=p.node_id,
                ip=p.ip,
                subnet=p.subnet,
                asn=p.asn,
                connection_age_days=self.rng.uniform(15.0, 180.0),
                reported_height=current_tip - self.rng.choice([0, 0, 0, 1]),
                is_backbone=True
            ))
        return PeerProfile(candidate_id=candidate_id, peers=peers, sampled_at_tip=current_tip)

    def create_eclipse_peer_profile(
        self,
        candidate_id: str,
        attacker_asn: str = "AS99999_MALICIOUS",
        attacker_subnet: str = "198.51.100.0/24",
        peer_count: int = 8,
        lag_blocks: int = 15,
        current_tip: int = 1000
    ) -> PeerProfile:
        """Generates an eclipsed peer profile with concentrated attacker nodes."""
        peers = []
        for i in range(peer_count):
            nid = f"ATTACKER_PEER_{i:02d}"
            ip = f"198.51.100.{i + 10}"
            peers.append(PeerNode(
                node_id=nid,
                ip=ip,
                subnet=attacker_subnet,
                asn=attacker_asn,
                connection_age_days=self.rng.uniform(0.01, 1.5),  # Brand new connections
                reported_height=current_tip - lag_blocks,          # Lagging tip
                is_backbone=False
            ))
        return PeerProfile(candidate_id=candidate_id, peers=peers, sampled_at_tip=current_tip)

    def evaluate_node_disjoint_paths_to_core(self, candidate_profile: PeerProfile, sample_size: int = 5) -> int:
        """
        Calculates the number of node-disjoint paths from the candidate to the honest core
        using NetworkX, ensuring resistance against routing table eclipse.
        """
        temp_g = self.graph.copy()
        c_id = candidate_profile.candidate_id
        temp_g.add_node(c_id, is_backbone=False)

        # Attach candidate peers to graph
        for p in candidate_profile.peers:
            if not temp_g.has_node(p.node_id):
                temp_g.add_node(p.node_id, asn=p.asn, subnet=p.subnet, is_backbone=p.is_backbone)
                if p.is_backbone:
                    # A verified backbone member outside the sampled registry still belongs to
                    # the honest core: wire it to registry nodes of its own ASN (or any three).
                    same_asn = [n for n, b in self.backbone_nodes.items() if b.asn == p.asn]
                    for core_peer in (same_asn or list(self.backbone_nodes.keys()))[:3]:
                        temp_g.add_edge(p.node_id, core_peer)
            temp_g.add_edge(c_id, p.node_id)

        # Select a sample of core backbone nodes
        core_sample = list(self.backbone_nodes.keys())[:sample_size]
        disjoint_path_counts = []
        for core in core_sample:
            try:
                paths = list(nx.node_disjoint_paths(temp_g, c_id, core))
                disjoint_path_counts.append(len(paths))
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                disjoint_path_counts.append(0)

        return max(disjoint_path_counts) if disjoint_path_counts else 0
