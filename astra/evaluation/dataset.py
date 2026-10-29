"""
Benchmark population builder shared by the evaluation runner, the threshold
calibration and the machine-learning baseline.

A population is the standard ASTRA candidate mix (57 honest / 63 attacking at
n = 120) generated on the simulated ledger from one seed, with every candidate
evaluated by the MonitorAgent after the whole population exists. Each record
keeps the agent risks, the Positive Trust components and every indicator score,
so that any decision rule, hand-written or learned, can be scored on the same data.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from astra.config import ASTRAConfig, DEFAULT_CONFIG
from astra.blockchain.sim_chain import SimChain
from astra.network.peer_registry import PeerRegistry
from astra.network.mempool import MempoolLog
from astra.network.propagation import BlockPropagationLog
from astra.scenarios.generator import ScenarioGenerator
from astra.pre_admission.monitor_agent import MonitorAgent
from astra.pre_admission.types import AdminAction, TrustEvaluation
from astra.admin.policies import AutoAdmin


# Candidate mix of the benchmark (counts at n = 125, scaled to the requested n).
PROFILE_MIX: List[Tuple[str, int]] = [
    ("honest", 20), ("honest_power_user", 15), ("honest_single_cloud", 15), ("honest_fee_bumper", 10),
    ("sybil", 15), ("stealthy_sybil", 10), ("malicious_wallet", 15), ("finney", 10),
    ("eclipse", 10), ("partial_eclipse", 5),
]

AGENT_NAMES = ("Sybil", "Wallet", "Finney", "Eclipse")
PT_NAMES = ("I", "T", "N", "H", "B")


@dataclass
class CandidateRecord:
    candidate_id: str
    candidate_type: str
    is_attacker: bool
    tf: float
    ar: float
    pt: float
    tv: float
    risks: Dict[str, float]                 # agent name -> risk
    pt_components: Dict[str, float]         # I, T, N, H, B
    indicators: Dict[str, float]            # "Agent:Indicator name" -> score
    escalation_flag: bool
    action_formula: AdminAction
    action_escalation: AdminAction
    evaluation: Optional[TrustEvaluation] = field(default=None, repr=False)

    @property
    def label(self) -> str:
        return "ATTACK" if self.is_attacker else "HONEST"


def profile_counts(n: int) -> List[Tuple[str, int]]:
    scale = n / 125.0
    return [(c_type, max(1, int(round(count * scale)))) for c_type, count in PROFILE_MIX]


def build_population(seed: int = 42, n: int = 120, config: ASTRAConfig = DEFAULT_CONFIG) -> List[CandidateRecord]:
    """Generates and evaluates one benchmark population on the simulated ledger."""
    chain = SimChain(seed=seed)
    peer_registry = PeerRegistry(seed=seed)
    mempool_log = MempoolLog()
    propagation_log = BlockPropagationLog()
    generator = ScenarioGenerator(seed=seed)
    monitor = MonitorAgent(config)
    generator.populate_background(chain, peer_registry, mempool_log, propagation_log)

    candidates = []
    idx = 1
    for c_type, count in profile_counts(n):
        for _ in range(count):
            candidates.append(generator.create_candidate(
                c_type, f"CAND_{idx:03d}", chain, peer_registry, mempool_log, propagation_log
            ))
            idx += 1

    admin_formula = AutoAdmin(use_escalation=False)
    admin_escalation = AutoAdmin(use_escalation=True)
    records: List[CandidateRecord] = []
    for c in candidates:
        ev = monitor.evaluate_candidate(
            candidate_id=c.candidate_id,
            wallet_address=c.wallet_address,
            chain=chain,
            peer_profile=c.peer_profile,
            peer_registry=peer_registry,
            mempool_log=mempool_log,
            propagation_log=propagation_log,
            candidate_mined_blocks=c.mined_blocks,
            known_exchanges=generator.exchanges,
        )
        records.append(CandidateRecord(
            candidate_id=c.candidate_id,
            candidate_type=c.candidate_type,
            is_attacker=(c.label == "ATTACK"),
            tf=ev.tf, ar=ev.ar, pt=ev.pt, tv=ev.tv,
            risks={name: out.risk for name, out in ev.agent_outputs.items()},
            pt_components={
                "I": ev.pt_score.i_score, "T": ev.pt_score.t_score, "N": ev.pt_score.n_score,
                "H": ev.pt_score.h_score, "B": ev.pt_score.b_score,
            },
            indicators={
                f"{name}:{ind.name}": ind.score
                for name, out in ev.agent_outputs.items() for ind in out.indicators
            },
            escalation_flag=ev.escalation_flag,
            action_formula=admin_formula.decide(ev).action,
            action_escalation=admin_escalation.decide(ev).action,
            evaluation=ev,
        ))
    return records


# ----------------------------------------------------------------------------
# Feature views
# ----------------------------------------------------------------------------
AGENT_LEVEL_FEATURES: List[str] = [f"risk:{a}" for a in AGENT_NAMES] + [f"pt:{p}" for p in PT_NAMES]


def indicator_feature_names(records: Sequence[CandidateRecord]) -> List[str]:
    names = set()
    for r in records:
        names.update(r.indicators)
    return AGENT_LEVEL_FEATURES + sorted(f"ind:{n}" for n in names)


def feature_vector(record: CandidateRecord, names: Sequence[str]) -> List[float]:
    out = []
    for name in names:
        kind, _, key = name.partition(":")
        if kind == "risk":
            out.append(record.risks.get(key, 0.0))
        elif kind == "pt":
            out.append(record.pt_components.get(key, 0.0))
        else:
            out.append(record.indicators.get(key, 0.0))
    return out


def feature_matrix(records: Sequence[CandidateRecord], names: Sequence[str]) -> List[List[float]]:
    return [feature_vector(r, names) for r in records]


def labels(records: Sequence[CandidateRecord]) -> List[int]:
    return [1 if r.is_attacker else 0 for r in records]


# ----------------------------------------------------------------------------
# Metrics (positive class = attacker flagged)
# ----------------------------------------------------------------------------
def classification_metrics(y_true: Sequence[int], y_pred: Sequence[int]) -> Dict[str, object]:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    total = tp + fp + tn + fn
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    return {
        "accuracy": round((tp + tn) / total, 4) if total else 0.0,
        "balanced_accuracy": round((recall + specificity) / 2.0, 4),
        "precision": round(tp / (tp + fp), 4) if (tp + fp) else 0.0,
        "recall": round(recall, 4),
        "fpr": round(fp / (fp + tn), 4) if (fp + tn) else 0.0,
        "fnr": round(fn / (fn + tp), 4) if (fn + tp) else 0.0,
        "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
    }


def policy_predictions(records: Sequence[CandidateRecord], policy: str, tv: Optional[float] = None,
                       w_pt: Optional[float] = None) -> List[int]:
    """
    Decisions of a hand-written policy as 0/1 'flagged' labels.
      formula:    flagged if TF < TV
      escalation: flagged if TF < TV or the escalation flag is set
    Optional tv / w_pt override the threshold and the TF composition
    (TF = w_pt*PT + (1-w_pt)*(1-AR)), which is what the calibration searches over.
    """
    preds = []
    for r in records:
        threshold = r.tv if tv is None else tv
        tf = r.tf if w_pt is None else (w_pt * r.pt + (1.0 - w_pt) * (1.0 - r.ar))
        flagged = tf < threshold
        if policy == "escalation":
            flagged = flagged or r.escalation_flag
        preds.append(1 if flagged else 0)
    return preds
