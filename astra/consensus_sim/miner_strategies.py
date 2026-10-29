"""
Miner strategies for the discrete-event PoW consensus simulator:
- Honest
- Selfish Mining (Eyal-Sirer state machine)
- Block Withholding
- 51% Hashpower Coalition
- Race Double-Spend
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


class MinerType(str, Enum):
    HONEST = "HONEST"
    SELFISH = "SELFISH"
    BLOCK_WITHHOLDING = "BLOCK_WITHHOLDING"
    COALITION_51 = "COALITION_51"
    RACE_DOUBLE_SPEND = "RACE_DOUBLE_SPEND"


@dataclass
class MinerAgentState:
    miner_id: str
    strategy: MinerType
    hashrate_share: float          # In [0, 1]
    private_chain: List[Any] = field(default_factory=list)
    lead: int = 0                  # Private lead over public tip
    pool_shares_submitted: int = 0
    full_blocks_found: int = 0
    withheld_count: int = 0
    attack_active: bool = False
    censored_addresses: List[str] = field(default_factory=list)
