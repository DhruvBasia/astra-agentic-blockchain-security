"""
STEP 7: Eclipse Agent
Role: Analyzes P2P graph topology using NetworkX to identify network isolation,
peer monopolization, and eclipse vulnerability.
Output: Eclipse Risk Score (0.0 to 1.0) and explainable reasoning.
"""

from typing import Dict, Any, Optional
import networkx as nx


class EclipseAgent:
    """
    Evaluates Eclipse attack risk using NetworkX graph topology metrics,
    peer diversity index, and suspicious peer concentration.
    """
    def __init__(self, name: str = "Eclipse Risk Agent"):
        self.name = name

    def evaluate(self, eclipse_evidence: Dict[str, Any], p2p_graph: Optional[nx.Graph] = None) -> Dict[str, Any]:
        """
        Calculates Eclipse Risk (0.0 to 1.0).
        Higher = More dangerous.
        """
        peer_count = int(eclipse_evidence.get("peer_count", 0))
        diversity_score = float(eclipse_evidence.get("peer_diversity_score", 0.5))
        suspicious_ratio = float(eclipse_evidence.get("suspicious_peer_ratio", 0.0))

        # 1. Peer Diversity Risk (Low diversity = high risk of colluding cluster)
        diversity_risk = max(0.0, 1.0 - diversity_score)

        # 2. Suspicious Peer Concentration Risk
        concentration_risk = suspicious_ratio

        # 3. NetworkX Graph Topologic Density & Degree Analysis
        if p2p_graph is not None and len(p2p_graph) > 0:
            # Analyze using graph measures if full topology available
            avg_clustering = nx.average_clustering(p2p_graph)
            graph_factor = min(1.0, avg_clustering)
        else:
            # If sub-graph not provided, evaluate based on peer count threshold
            if peer_count < 3:
                graph_factor = 0.70  # Starvation risk
            elif peer_count < 8:
                graph_factor = 0.30
            else:
                graph_factor = 0.10

        # High concentration of suspicious peers is the definitive hallmark of an Eclipse attack
        if suspicious_ratio >= 0.70 or (peer_count < 4 and diversity_score < 0.25):
            eclipse_risk = min(1.0, 0.85 + (suspicious_ratio * 0.12))
            eclipse_flag = "CRITICAL_ECLIPSE_ISOLATION_RISK"
        elif suspicious_ratio >= 0.40 or diversity_score < 0.40:
            eclipse_risk = 0.55
            eclipse_flag = "ELEVATED_TOPOLOGY_MONOPOLIZATION"
        else:
            eclipse_risk = max(0.05, (0.45 * diversity_risk) + (0.40 * concentration_risk) + (0.15 * graph_factor))
            eclipse_flag = "BALANCED_HEALTHY_TOPOLOGY"

        eclipse_risk = round(min(1.0, max(0.0, eclipse_risk)), 3)

        explanation = (
            f"Eclipse evaluation: Peer count={peer_count}, diversity_score={diversity_score} (diversity_risk={round(diversity_risk, 2)}), "
            f"suspicious_peer_ratio={round(suspicious_ratio * 100, 1)}% (concentration_risk={round(concentration_risk, 2)}). "
            f"Classification: {eclipse_flag}. Overall Eclipse Risk: {eclipse_risk}."
        )

        return {
            "agent_name": self.name,
            "eclipse_risk": eclipse_risk,
            "indicators": {
                "peer_count": peer_count,
                "diversity_score": diversity_score,
                "suspicious_peer_ratio": suspicious_ratio,
                "eclipse_flag": eclipse_flag,
                "diversity_risk": round(diversity_risk, 3),
                "concentration_risk": round(concentration_risk, 3)
            },
            "explanation": explanation
        }
