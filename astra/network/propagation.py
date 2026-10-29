"""
Block propagation log tracking block discovery times vs network first-seen arrival.
Used to detect block withholding, hidden mining, and abnormal propagation latency.
"""

import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class PropagationRecord:
    block_number: int
    miner: str
    block_timestamp: float
    first_seen: float

    @property
    def delay(self) -> float:
        """Propagation delay in seconds (first_seen - block_timestamp)."""
        return max(0.0, self.first_seen - self.block_timestamp)


class BlockPropagationLog:
    """Stores arrival timing for all broadcast blocks."""

    def __init__(self):
        self._records: Dict[int, PropagationRecord] = {}

    def record(self, block_number: int, miner: str, block_timestamp: float, first_seen: float) -> PropagationRecord:
        rec = PropagationRecord(
            block_number=block_number,
            miner=miner.lower(),
            block_timestamp=float(block_timestamp),
            first_seen=float(first_seen)
        )
        self._records[block_number] = rec
        return rec

    def get(self, block_number: int) -> Optional[PropagationRecord]:
        return self._records.get(block_number)

    def all_records(self) -> List[PropagationRecord]:
        return list(self._records.values())

    def median_delay(self) -> float:
        if not self._records:
            return 0.8
        delays = [r.delay for r in self._records.values()]
        return statistics.median(delays) if delays else 0.8
