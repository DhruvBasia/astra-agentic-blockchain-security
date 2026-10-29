"""
Type definitions and dataclasses for the Post-Admission Continuous Monitoring Layer.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class PostAdmissionAlert:
    """An alert emitted by a post-admission continuous monitoring agent."""
    alert_id: str
    agent_name: str
    severity: AlertSeverity
    risk: float                     # Risk in [0, 1]
    suspect: str                    # Offending address / miner
    evidence: List[str]             # Specific technical evidence
    timestamp: float
    block_number: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def deduplication_key(self) -> str:
        """Returns a string key used to prevent redundant spamming of the same alert."""
        return f"{self.agent_name}:{self.suspect}:{self.severity.value}"


@dataclass
class BlockRecord:
    """Represents a mined block in the post-admission simulation."""
    block_number: int
    block_hash: str
    parent_hash: str
    miner: str
    timestamp: float                # Block header timestamp
    first_seen: float               # Network first-seen arrival timestamp
    transactions: List[Dict[str, Any]] = field(default_factory=list)
    is_orphan: bool = False
    is_main_chain: bool = True
    height: int = 0
