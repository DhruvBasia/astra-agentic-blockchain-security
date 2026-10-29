"""
SimChain: Pure-Python deterministic in-memory blockchain ledger.
Supports balances, nonces, gas fees, failed transactions, simulated clock, and block height.
"""

import hashlib
import random
from typing import List, Dict, Any, Optional
from astra.blockchain.backend import ChainBackend, TxRecord


class SimChain(ChainBackend):
    """Deterministic in-memory blockchain implementation."""

    def __init__(self, seed: int = 42, start_time: float = 1700000000.0):
        self.seed = seed
        self.rng = random.Random(seed)
        self.current_time = start_time
        self.current_block = 0
        
        # State storage
        self._balances: Dict[str, float] = {}
        self._nonces: Dict[str, int] = {}
        self._tx_history: List[TxRecord] = []
        self._blocks: List[Dict[str, Any]] = [
            {
                "number": 0,
                "timestamp": self.current_time,
                "hash": "0xgenesis00000000000000000000000000000000000000000000000000000000",
                "txs": []
            }
        ]

    def _generate_address(self) -> str:
        # Generates a pseudo-random checksummed hex Ethereum address
        raw = bytes([self.rng.randint(0, 255) for _ in range(20)])
        return "0x" + raw.hex().lower()

    def accounts(self) -> List[str]:
        return list(self._balances.keys())

    def create_account(self, initial_balance_eth: float = 0.0) -> str:
        addr = self._generate_address()
        while addr in self._balances:
            addr = self._generate_address()
        self._balances[addr] = float(initial_balance_eth)
        self._nonces[addr] = 0
        return addr

    def advance_time(self, seconds: float) -> None:
        self.current_time += max(0.0, float(seconds))

    def now(self) -> float:
        return self.current_time

    def balance(self, account: str) -> float:
        return self._balances.get(account.lower(), 0.0)

    def tx_count(self, account: str) -> int:
        return self._nonces.get(account.lower(), 0)

    def block_number(self) -> int:
        return self.current_block

    def all_transactions(self) -> List[TxRecord]:
        return list(self._tx_history)

    def info(self) -> Dict[str, Any]:
        return {
            "backend": "SimChain",
            "block_number": self.current_block,
            "timestamp": self.current_time,
            "total_accounts": len(self._balances),
            "total_transactions": len(self._tx_history),
            "deterministic_seed": self.seed
        }

    def sign_only(
        self,
        sender: str,
        to: str,
        value_eth: float,
        nonce: Optional[int] = None,
        data: str = "0x"
    ) -> TxRecord:
        s_norm = sender.lower()
        t_norm = to.lower()
        tx_nonce = nonce if nonce is not None else self._nonces.get(s_norm, 0)
        
        # Deterministic transaction hash
        raw_content = f"{s_norm}:{t_norm}:{value_eth}:{tx_nonce}:{self.current_time}:{data}"
        tx_hash = "0x" + hashlib.sha256(raw_content.encode()).hexdigest()
        
        return TxRecord(
            tx_hash=tx_hash,
            sender=s_norm,
            to=t_norm,
            value_eth=float(value_eth),
            fee_eth=0.00021,  # Standard 21,000 gas @ 10 gwei
            nonce=tx_nonce,
            timestamp=self.current_time,
            block_number=None,
            status=1,
            is_broadcast=False,
            raw_signed=f"0xsig_{tx_hash[:16]}",
            data=data
        )

    def send(
        self,
        sender: str,
        to: str,
        value_eth: float,
        fail: bool = False,
        nonce: Optional[int] = None,
        data: str = "0x"
    ) -> TxRecord:
        s_norm = sender.lower()
        t_norm = to.lower()

        if s_norm not in self._balances:
            self._balances[s_norm] = 0.0
            self._nonces[s_norm] = 0
        if t_norm not in self._balances:
            self._balances[t_norm] = 0.0
            self._nonces[t_norm] = 0

        current_nonce = self._nonces[s_norm]
        tx_nonce = nonce if nonce is not None else current_nonce
        
        # Standard EVM fee calculation: 21,000 gas * 10 Gwei = 0.00021 ETH
        fee_eth = 0.00021
        sender_bal = self._balances[s_norm]

        raw_content = f"{s_norm}:{t_norm}:{value_eth}:{tx_nonce}:{self.current_time}:{self.current_block + 1}:{data}:{fail}"
        tx_hash = "0x" + hashlib.sha256(raw_content.encode()).hexdigest()

        if fail:
            # Failed/Reverted Transaction:
            # In EVM: nonce is consumed, gas fee is charged, but value transfer is rolled back.
            self._nonces[s_norm] = tx_nonce + 1
            self._balances[s_norm] = max(0.0, sender_bal - fee_eth)
            status = 0
        else:
            # Successful Transaction:
            if sender_bal >= (value_eth + fee_eth):
                self._balances[s_norm] -= (value_eth + fee_eth)
                self._balances[t_norm] += value_eth
                self._nonces[s_norm] = tx_nonce + 1
                status = 1
            else:
                # Insufficient balance -> transaction fails/reverts
                self._nonces[s_norm] = tx_nonce + 1
                self._balances[s_norm] = max(0.0, sender_bal - fee_eth)
                status = 0

        # Mine 1 block for the transaction
        self.current_block += 1
        record = TxRecord(
            tx_hash=tx_hash,
            sender=s_norm,
            to=t_norm,
            value_eth=float(value_eth),
            fee_eth=fee_eth,
            nonce=tx_nonce,
            timestamp=self.current_time,
            block_number=self.current_block,
            status=status,
            is_broadcast=True,
            raw_signed=f"0xsig_{tx_hash[:16]}",
            data=data
        )

        self._tx_history.append(record)
        self._blocks.append({
            "number": self.current_block,
            "timestamp": self.current_time,
            "hash": "0xblock" + hashlib.sha256(f"{self.current_block}:{tx_hash}".encode()).hexdigest(),
            "txs": [record]
        })

        return record
