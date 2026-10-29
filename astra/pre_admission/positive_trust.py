"""
Positive Trust (PT) Engine.
Computes the five constituent trust pillars:
  I: Identity Trust
  T: Transaction Trust
  N: Network Trust
  H: Historical Trust
  B: Behaviour Consistency

Formula:
  PT = 0.25*I + 0.20*T + 0.20*N + 0.20*H + 0.15*B
"""

from typing import List, Dict, Any, Optional
import statistics
from astra.pre_admission.types import PositiveTrustScore
from astra.blockchain.backend import TxRecord
from astra.network.peer_registry import PeerProfile, PeerRegistry
from astra.config import ASTRAConfig, DEFAULT_CONFIG


class PositiveTrustEngine:
    """Evaluates legitimate positive trust attributes of a joining candidate node."""

    def __init__(self, config: ASTRAConfig = DEFAULT_CONFIG):
        self.config = config

    def evaluate(
        self,
        candidate_address: str,
        all_transactions: List[TxRecord],
        peer_profile: PeerProfile,
        peer_registry: PeerRegistry,
        current_time: float,
        has_conflicts: bool = False,
        prior_alerts_count: int = 0,
        known_exchanges: Optional[List[str]] = None
    ) -> PositiveTrustScore:
        c_addr = candidate_address.lower()
        exchanges = set(a.lower() for a in (known_exchanges or []))

        # Filter candidate transactions
        txs = [tx for tx in all_transactions if tx.sender.lower() == c_addr or tx.to.lower() == c_addr]
        txs.sort(key=lambda x: x.timestamp)
        out_txs = [tx for tx in txs if tx.sender.lower() == c_addr]

        # ------------------------------------------------------------------
        # 1. Identity Trust (I): Age, Funder Reputation, Distinct Sources
        # ------------------------------------------------------------------
        incoming = [tx for tx in txs if tx.to.lower() == c_addr and tx.status == 1]
        earliest_tx = incoming[0] if incoming else (txs[0] if txs else None)
        age_days = (current_time - earliest_tx.timestamp) / 86400.0 if earliest_tx else 0.0

        if age_days >= 60.0:
            s_age = 1.0
        elif age_days >= 30.0:
            s_age = 0.85
        elif age_days >= 7.0:
            s_age = 0.50
        elif age_days >= 1.0:
            s_age = 0.25
        else:
            s_age = 0.10

        funder = incoming[0].sender.lower() if incoming else None
        if funder in exchanges:
            s_funder = 1.0
        elif funder is not None:
            s_funder = 0.60
        else:
            s_funder = 0.30

        distinct_funders = len(set(tx.sender.lower() for tx in incoming))
        s_sources = min(1.0, 0.4 + (distinct_funders * 0.2))

        i_score = round(0.50 * s_age + 0.30 * s_funder + 0.20 * s_sources, 3)

        # ------------------------------------------------------------------
        # 2. Transaction Trust (T): Success Ratio, No Conflicts, Value Normality
        # ------------------------------------------------------------------
        if out_txs:
            success_count = sum(1 for tx in out_txs if tx.status == 1)
            success_ratio = success_count / len(out_txs)
            dust_count = sum(1 for tx in out_txs if tx.value_eth < 0.001)
            value_normality = 1.0 - (dust_count / len(out_txs))
        else:
            success_ratio = 0.85  # Clean unexecuted
            value_normality = 0.85

        s_conflict = 0.10 if has_conflicts else 1.0
        t_score = round(0.40 * success_ratio + 0.40 * s_conflict + 0.20 * value_normality, 3)

        # ------------------------------------------------------------------
        # 3. Network Trust (N): Peer Degree, ASN Diversity, Backbone Connectivity
        # ------------------------------------------------------------------
        n_peers = peer_profile.peer_count
        s_degree = min(1.0, n_peers / 8.0) if n_peers > 0 else 0.0

        unique_asns = len(set(peer_profile.asns))
        s_asn_div = min(1.0, unique_asns / 4.0) if unique_asns > 0 else 0.0

        backbone_count = sum(1 for p in peer_profile.peers if p.is_backbone or p.node_id in peer_registry.backbone_nodes)
        s_bb = (backbone_count / max(1, n_peers)) if n_peers > 0 else 0.0

        n_score = round(0.35 * s_degree + 0.35 * s_asn_div + 0.30 * s_bb, 3)

        # ------------------------------------------------------------------
        # 4. Historical Trust (H): History Length, Prior Alert History
        # ------------------------------------------------------------------
        tx_length_score = min(1.0, len(txs) / 20.0) if txs else 0.3
        if prior_alerts_count == 0:
            # Baseline neutral-positive trust for unflagged candidate
            s_alerts = 0.85 if len(txs) > 5 else 0.50
        else:
            s_alerts = max(0.05, 0.50 - (prior_alerts_count * 0.20))

        h_score = round(0.50 * tx_length_score + 0.50 * s_alerts, 3)

        # ------------------------------------------------------------------
        # 5. Behaviour Consistency (B): Stability Across Time
        # ------------------------------------------------------------------
        if len(out_txs) >= 4:
            mid = len(out_txs) // 2
            early_vals = [tx.value_eth for tx in out_txs[:mid]]
            recent_vals = [tx.value_eth for tx in out_txs[mid:]]
            mean_early = statistics.mean(early_vals)
            mean_recent = statistics.mean(recent_vals)
            max_mean = max(mean_early, mean_recent, 1e-9)
            val_drift = abs(mean_early - mean_recent) / max_mean
            b_score = round(max(0.10, min(1.0, 1.0 - val_drift)), 3)
        else:
            b_score = 0.70  # Default stable consistency

        # ------------------------------------------------------------------
        # 6. Total PT Formulation
        # PT = 0.25*I + 0.20*T + 0.20*N + 0.20*H + 0.15*B
        # ------------------------------------------------------------------
        pt_total = (
            self.config.weight_pt_i * i_score
            + self.config.weight_pt_t * t_score
            + self.config.weight_pt_n * n_score
            + self.config.weight_pt_h * h_score
            + self.config.weight_pt_b * b_score
        )
        pt_total = round(max(0.0, min(1.0, pt_total)), 3)

        details = {
            "identity_age_days": round(age_days, 1),
            "identity_score_I": i_score,
            "transaction_score_T": t_score,
            "network_score_N": n_score,
            "history_score_H": h_score,
            "behavior_score_B": b_score,
            "pt_total": pt_total
        }

        return PositiveTrustScore(
            i_score=i_score,
            t_score=t_score,
            n_score=n_score,
            h_score=h_score,
            b_score=b_score,
            pt_total=pt_total,
            details=details
        )
