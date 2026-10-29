"""
Mempool log tracking unconfirmed transaction sightings and conflict detection.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple


@dataclass
class MempoolSighting:
    """Represents an observed transaction in the P2P mempool."""
    tx_hash: str
    sender: str
    nonce: int
    to: str
    value_eth: float
    fee_eth: float
    seen_at: float
    is_mined: bool = False


class MempoolLog:
    """Stores all broadcast transaction sightings across the peer network."""

    def __init__(self):
        self._sightings: List[MempoolSighting] = []
        # Index: (sender.lower(), nonce) -> List of sightings
        self._by_sender_nonce: Dict[Tuple[str, int], List[MempoolSighting]] = {}
        # Index: tx_hash.lower() -> sighting
        self._by_hash: Dict[str, MempoolSighting] = {}

    def record(
        self,
        tx_hash: str,
        sender: str,
        nonce: int,
        to: str,
        value_eth: float,
        fee_eth: float,
        seen_at: float,
        is_mined: bool = False
    ) -> MempoolSighting:
        s_norm = sender.lower()
        t_norm = to.lower()
        h_norm = tx_hash.lower()

        sighting = MempoolSighting(
            tx_hash=h_norm,
            sender=s_norm,
            nonce=nonce,
            to=t_norm,
            value_eth=float(value_eth),
            fee_eth=float(fee_eth),
            seen_at=float(seen_at),
            is_mined=is_mined
        )
        self._sightings.append(sighting)
        self._by_hash[h_norm] = sighting

        key = (s_norm, nonce)
        if key not in self._by_sender_nonce:
            self._by_sender_nonce[key] = []
        self._by_sender_nonce[key].append(sighting)

        return sighting

    def get_by_sender_nonce(self, sender: str, nonce: int) -> List[MempoolSighting]:
        return self._by_sender_nonce.get((sender.lower(), nonce), [])

    def mark_mined(self, tx_hash: str) -> None:
        h_norm = tx_hash.lower()
        if h_norm in self._by_hash:
            self._by_hash[h_norm].is_mined = True

    def all_sightings(self) -> List[MempoolSighting]:
        return list(self._sightings)
