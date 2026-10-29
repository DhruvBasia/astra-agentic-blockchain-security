"""
Eclipse Attack Pre-Admission Agent.
Evaluates peer topology, ASN diversity, Herfindahl-Hirschman concentration (HHI),
backbone connectivity, peer connection freshness, tip lag, and NetworkX node-disjoint paths.
Uses Noisy-OR combination of indicator scores.
"""

from typing import List, Dict, Any, Optional
import collections
from astra.pre_admission.types import AgentOutput, IndicatorScore
from astra.network.peer_registry import PeerRegistry, PeerProfile


class EclipseAgent:
    """Specialized agent detecting network-level routing table isolation and Eclipse attacks."""

    # Well-known providers and carriers; concentration inside one of these is
    # treated as hosting, not as attacker infrastructure.
    REPUTABLE_ASNS = frozenset(PeerRegistry.HONEST_ASNS)

    def __init__(self, name: str = "Eclipse Agent"):
        self.name = name

    def evaluate(
        self,
        peer_profile: PeerProfile,
        peer_registry: PeerRegistry,
        current_tip: int = 1000
    ) -> AgentOutput:
        peers = peer_profile.peers
        n_peers = len(peers)

        # ------------------------------------------------------------------
        # 1. Peer Count
        # ------------------------------------------------------------------
        if n_peers == 0:
            s_count = 1.0
        elif n_peers < 4:
            s_count = 0.85
        elif n_peers < 8:
            s_count = 0.35
        else:
            s_count = 0.05

        # ------------------------------------------------------------------
        # 2. ASN Diversity & Herfindahl Concentration Index (HHI)
        # ------------------------------------------------------------------
        asn_counts = collections.Counter(p.asn for p in peers)
        unique_asns = len(asn_counts)

        if n_peers > 0:
            hhi = sum((count / n_peers) ** 2 for count in asn_counts.values())
        else:
            hhi = 1.0

        dominant_asn, dominant_count = asn_counts.most_common(1)[0] if asn_counts else ("", 0)
        dominant_share = (dominant_count / n_peers) if n_peers > 0 else 0.0
        dominant_is_reputable = dominant_asn in self.REPUTABLE_ASNS

        # High HHI (>0.60) means peers are monopolized by 1 or 2 ASNs
        if hhi >= 0.80:
            s_hhi = 0.95
        elif hhi >= 0.50:
            s_hhi = 0.65
        elif hhi >= 0.30:
            s_hhi = 0.30
        else:
            s_hhi = 0.05

        # ------------------------------------------------------------------
        # 3. Backbone Overlap
        # Fraction of peers that are verified backbone members
        # ------------------------------------------------------------------
        backbone_peers = [p for p in peers if p.is_backbone or p.node_id in peer_registry.backbone_nodes]
        backbone_ratio = (len(backbone_peers) / n_peers) if n_peers > 0 else 0.0
        # If backbone ratio is 0, high isolation risk
        s_backbone = max(0.0, 1.0 - (backbone_ratio * 1.2))

        # ------------------------------------------------------------------
        # 4. Peer Freshness
        # Share of connections younger than 2 days. A ratio (not the mean age)
        # so that a few long-lived honest peers cannot mask a fresh majority.
        # ------------------------------------------------------------------
        fresh_peers = [p for p in peers if p.connection_age_days < 2.0]
        fresh_ratio = (len(fresh_peers) / n_peers) if n_peers > 0 else 0.0
        avg_age = (sum(p.connection_age_days for p in peers) / n_peers) if n_peers > 0 else 0.0

        if fresh_ratio >= 0.75:
            s_fresh = 0.90
        elif fresh_ratio >= 0.50:
            s_fresh = 0.65
        elif fresh_ratio >= 0.25:
            s_fresh = 0.30
        else:
            s_fresh = 0.05

        # Concentration inside one well-known provider, with established verified
        # backbone peers, is how a legitimately cloud-hosted node looks. Discount it;
        # the attack signatures below (isolation, churn, takeover) are unaffected.
        provider_hosted = (
            hhi >= 0.50 and dominant_is_reputable and backbone_ratio >= 0.80 and fresh_ratio < 0.25
        )
        if provider_hosted:
            s_hhi = min(s_hhi, 0.40)

        # ------------------------------------------------------------------
        # 5. Reported Tip Lag
        # Heights are compared against the tip at the time the table was sampled.
        # ------------------------------------------------------------------
        reference_tip = peer_profile.sampled_at_tip if peer_profile.sampled_at_tip is not None else current_tip
        lagging_peers = [p for p in peers if (reference_tip - p.reported_height) >= 5]
        lag_ratio = (len(lagging_peers) / n_peers) if n_peers > 0 else 0.0
        s_lag = min(1.0, lag_ratio * 1.5)

        # ------------------------------------------------------------------
        # 6. NetworkX Node-Disjoint Paths to Core Backbone
        # ------------------------------------------------------------------
        disjoint_paths = peer_registry.evaluate_node_disjoint_paths_to_core(peer_profile)
        if disjoint_paths == 0:
            s_paths = 0.95
        elif disjoint_paths == 1:
            s_paths = 0.70
        elif disjoint_paths == 2:
            s_paths = 0.30
        else:
            s_paths = 0.05

        # ------------------------------------------------------------------
        # 7. Noisy-OR Combination
        # ------------------------------------------------------------------
        indicators = [
            IndicatorScore(
                name="Herfindahl ASN Concentration",
                raw_value=f"HHI={hhi:.2f} ({unique_asns} unique ASNs)",
                score=s_hhi,
                weight=0.25,
                description="Concentration index of peer routing tables across autonomous systems"
            ),
            IndicatorScore(
                name="Backbone Overlap",
                raw_value=f"{backbone_ratio:.1%} ({len(backbone_peers)}/{n_peers})",
                score=s_backbone,
                weight=0.20,
                description="Proportion of peer connections linked to verified honest network backbone"
            ),
            IndicatorScore(
                name="Disjoint Paths to Core",
                raw_value=f"{disjoint_paths} independent paths",
                score=s_paths,
                weight=0.20,
                description="NetworkX topological node-disjoint paths connecting candidate to honest core"
            ),
            IndicatorScore(
                name="Peer Freshness",
                raw_value=f"{fresh_ratio:.1%} <2 days (avg {avg_age:.1f} days)",
                score=s_fresh,
                weight=0.15,
                description="Share of newborn connections; eclipsing peers are predominantly fresh"
            ),
            IndicatorScore(
                name="Tip Lag",
                raw_value=f"{lag_ratio:.1%} lagging peers",
                score=s_lag,
                weight=0.10,
                description="Percentage of peers broadcasting stale / partitioned chain tip heights"
            ),
            IndicatorScore(
                name="Peer Count",
                raw_value=f"{n_peers} peers",
                score=s_count,
                weight=0.10,
                description="Degree centrality and starvation exposure of the candidate node"
            )
        ]

        prod = 1.0
        for ind in indicators:
            prod *= (1.0 - ind.weight * ind.score)
        risk = max(0.0, min(1.0, 1.0 - prod))

        max_possible_prod = 1.0
        for ind in indicators:
            max_possible_prod *= (1.0 - ind.weight * 1.0)
        norm_factor = 1.0 - max_possible_prod
        if norm_factor > 0:
            risk = min(1.0, risk / norm_factor)

        risk = round(risk, 3)

        # ------------------------------------------------------------------
        # 8. Evidence Generation
        # ------------------------------------------------------------------
        evidence = []
        critical = False

        # Concentration alone is not an attack; it is critical only when corroborated
        # by isolation from the honest core or by freshly built connections.
        isolated = backbone_ratio < 0.50 or disjoint_paths <= 1 or fresh_ratio >= 0.50
        # Takeover: a non-reputable ASN holds most of the table with fresh, unverified peers.
        takeover = (
            dominant_share >= 0.60 and not dominant_is_reputable
            and fresh_ratio >= 0.50 and backbone_ratio < 0.50 and n_peers >= 4
        )

        if hhi >= 0.70:
            if provider_hosted:
                evidence.append(
                    f"Peers concentrated in one known provider ASN ({dominant_asn}, HHI={hhi:.2f}), but all are "
                    f"established verified backbone connections; concentration discounted."
                )
            else:
                evidence.append(f"Severe peer ASN concentration: HHI={hhi:.2f} across only {unique_asns} autonomous system(s).")
                if unique_asns <= 1 and n_peers >= 4 and isolated:
                    critical = True

        if takeover:
            evidence.append(
                f"Routing table takeover: {dominant_share:.0%} of peers sit in unverified ASN {dominant_asn} "
                f"and {fresh_ratio:.0%} of connections are under 2 days old."
            )
            critical = True

        if backbone_ratio < 0.20:
            evidence.append(f"Critical backbone isolation: only {backbone_ratio:.1%} of peers connect to honest core.")

        if disjoint_paths <= 1:
            evidence.append(f"NetworkX routing vulnerability: only {disjoint_paths} node-disjoint path(s) to honest backbone.")

        if fresh_ratio >= 0.50 and n_peers >= 4:
            evidence.append(f"Coordinated peer churn: {len(fresh_peers)} of {n_peers} connections established within the past 2 days.")

        if lag_ratio > 0.50:
            evidence.append(f"Partitioned view: {lag_ratio:.1%} of peers report stale block heights lagging consensus tip.")

        if not evidence:
            evidence.append("Peer connectivity exhibits healthy topological dispersion across multiple ASNs and core backbone.")

        summary = f"Eclipse Risk: {risk:.2f}. " + (
            "CRITICAL Eclipse routing table monopolization detected!" if critical
            else "Well-connected and diversified peer graph."
        )

        return AgentOutput(
            agent_name=self.name,
            risk=risk,
            indicators=indicators,
            evidence=evidence,
            summary=summary,
            critical=critical
        )
