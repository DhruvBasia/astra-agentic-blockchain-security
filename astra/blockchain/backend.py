"""
Abstract base class and data models for blockchain backends.
Supports both SimChain (pure Python in-memory) and GanacheChain (Web3.py).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class TxRecord:
    """Represents a transaction on the blockchain or in the mempool."""
    tx_hash: str
    sender: str
    to: str
    value_eth: float
    fee_eth: float
    nonce: int
    timestamp: float
    block_number: Optional[int]
    status: int = 1                 # 1 = Success, 0 = Reverted/Failed
    is_broadcast: bool = True       # False for sign_only transactions
    raw_signed: Optional[str] = None
    data: str = "0x"


class ChainBackend(ABC):
    """Unified interface for blockchain interactions."""

    @abstractmethod
    def accounts(self) -> List[str]:
        """List all managed account addresses."""
        pass

    @abstractmethod
    def create_account(self, initial_balance_eth: float = 0.0) -> str:
        """Create a new account with optional initial funding."""
        pass

    @abstractmethod
    def send(
        self,
        sender: str,
        to: str,
        value_eth: float,
        fail: bool = False,
        nonce: Optional[int] = None,
        data: str = "0x"
    ) -> TxRecord:
        """Submit a transaction. If fail=True, the transaction consumes gas/nonce but reverts."""
        pass

    @abstractmethod
    def sign_only(
        self,
        sender: str,
        to: str,
        value_eth: float,
        nonce: Optional[int] = None,
        data: str = "0x"
    ) -> TxRecord:
        """Create and sign a transaction without broadcasting it to the chain."""
        pass

    @abstractmethod
    def advance_time(self, seconds: float) -> None:
        """Advance the blockchain clock by a given number of seconds."""
        pass

    @abstractmethod
    def now(self) -> float:
        """Return the current blockchain timestamp (in seconds)."""
        pass

    @abstractmethod
    def balance(self, account: str) -> float:
        """Return account balance in ETH."""
        pass

    @abstractmethod
    def tx_count(self, account: str) -> int:
        """Return the account nonce / transaction count."""
        pass

    @abstractmethod
    def block_number(self) -> int:
        """Return the current block number."""
        pass

    @abstractmethod
    def all_transactions(self) -> List[TxRecord]:
        """Return all on-chain mined transactions."""
        pass

    @abstractmethod
    def info(self) -> Dict[str, Any]:
        """Return human-readable metadata about the backend."""
        pass
