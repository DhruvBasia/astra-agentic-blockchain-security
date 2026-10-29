"""
Type definitions and dataclasses for the Pre-Admission Layer.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class Recommendation(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    INVESTIGATE = "INVESTIGATE"


class AdminAction(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    INVESTIGATE = "INVESTIGATE"
    REMOVE = "REMOVE"
    CONTINUE = "CONTINUE"


@dataclass
class IndicatorScore:
    """Represents a single measured security indicator."""
    name: str
    raw_value: Any
    score: float       # In [0.0, 1.0], higher = higher risk or impact
    weight: float      # Relative indicator weight
    description: str


@dataclass
class AgentOutput:
    """Output produced by a specialized pre-admission agent."""
    agent_name: str
    risk: float                     # Aggregated risk in [0.0, 1.0]
    indicators: List[IndicatorScore]
    evidence: List[str]             # Human-readable evidence items
    summary: str                    # Concise textual summary
    critical: bool = False          # True if a critical attack signature was observed


@dataclass
class PositiveTrustScore:
    """Breakdown of the 5 Positive Trust (PT) components."""
    i_score: float                  # Identity trust in [0, 1]
    t_score: float                  # Transaction trust in [0, 1]
    n_score: float                  # Network trust in [0, 1]
    h_score: float                  # Historical trust in [0, 1]
    b_score: float                  # Behaviour consistency in [0, 1]
    pt_total: float                 # Weighted PT in [0, 1]
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrustEvaluation:
    """Overall pre-admission evaluation result."""
    candidate_id: str
    wallet_address: str
    ar: float                       # Attack Risk in [0, 1]
    pt: float                       # Positive Trust in [0, 1]
    tf: float                       # Trust Factor in [0, 1]
    tv: float                       # Threshold Value (0.70)
    recommendation: Recommendation
    escalation_flag: bool           # True if any agent risk >= 0.75 or critical evidence found
    escalation_reasons: List[str]
    agent_outputs: Dict[str, AgentOutput]
    pt_score: PositiveTrustScore
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_recommended_accept(self) -> bool:
        return self.recommendation == Recommendation.ACCEPT


@dataclass
class AdminDecisionRecord:
    """Audit log of human administrator's final decision."""
    candidate_id: str
    action: AdminAction
    reason: str
    decided_by: str = "HumanAdministrator"
    timestamp: float = 0.0
    evidence_reviewed: List[str] = field(default_factory=list)
