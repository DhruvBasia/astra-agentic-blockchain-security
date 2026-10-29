"""
GanacheChain: Web3.py backend connected to local Ganache RPC (port 7545).
- Unlocked Ganache accounts serve as genesis / exchange funders.
- Scenario accounts are locally generated keypairs signed via eth-account.
- Real on-chain failed transactions deployed via runtime bytecode `60006000fd` (PUSH1 0 PUSH1 0 REVERT).
- EVM time progression via evm_increaseTime & evm_mine.
"""

from typing import List, Dict, Any, Optional
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
from astra.blockchain.backend import ChainBackend, TxRecord


class GanacheChain(ChainBackend):
    """Ethereum testnet backend using Web3.py against Ganache."""

    # Deployment bytecode that deploys runtime code `60006000fd`
    REVERT_DEPLOY_BYTECODE = "0x6005600c60003960056000f360006000fd"

    def __init__(self, rpc_url: str = "http://127.0.0.1:7545"):
        self.rpc_url = rpc_url
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot connect to Ganache at {rpc_url}. Ensure Ganache is running.")

        self.genesis_accounts = [acc.lower() for acc in self.w3.eth.accounts]
        if not self.genesis_accounts:
            raise ValueError("Ganache node returned 0 accounts. Ensure --wallet.deterministic is enabled.")

        # Local account registry: address -> LocalAccount object
        self._local_accounts: Dict[str, LocalAccount] = {}
        self._revert_contract_address: Optional[str] = None
        self._init_revert_contract()

    def _init_revert_contract(self) -> None:
        """Deploys a minimal EVM contract that unconditionally executes REVERT."""
        try:
            funder = self.w3.eth.accounts[0]
            tx = {
                "from": funder,
                "data": self.REVERT_DEPLOY_BYTECODE,
                "gas": 150000,
                "gasPrice": self.w3.eth.gas_price
            }
            tx_hash = self.w3.eth.send_transaction(tx)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            self._revert_contract_address = receipt.contractAddress
        except Exception as e:
            # Fallback if already deployed or minor error
            self._revert_contract_address = None

    def accounts(self) -> List[str]:
        # Return both genesis accounts and generated scenario accounts
        all_accs = list(self.genesis_accounts)
        for addr in self._local_accounts.keys():
            if addr not in all_accs:
                all_accs.append(addr)
        return all_accs

    def create_account(self, initial_balance_eth: float = 0.0) -> str:
        new_acc: LocalAccount = Account.create()
        addr = new_acc.address.lower()
        self._local_accounts[addr] = new_acc

        if initial_balance_eth > 0:
            funder = None
            req_wei = self.w3.to_wei(initial_balance_eth + 0.05, "ether")
            for acc in self.w3.eth.accounts:
                if self.w3.eth.get_balance(acc) > req_wei:
                    funder = acc
                    break
            if not funder:
                funder = self.w3.eth.accounts[0]

            value_wei = self.w3.to_wei(initial_balance_eth, "ether")
            tx = {
                "from": funder,
                "to": new_acc.address,
                "value": value_wei,
                "gas": 21000,
                "gasPrice": self.w3.eth.gas_price,
                "nonce": self.w3.eth.get_transaction_count(funder)
            }
            tx_hash = self.w3.eth.send_transaction(tx)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return addr

    def advance_time(self, seconds: float) -> None:
        secs = int(max(1, seconds))
        self.w3.provider.make_request("evm_increaseTime", [secs])
        self.w3.provider.make_request("evm_mine", [])

    def now(self) -> float:
        latest_block = self.w3.eth.get_block("latest")
        return float(latest_block.timestamp)

    def balance(self, account: str) -> float:
        checksum = Web3.to_checksum_address(account)
        bal_wei = self.w3.eth.get_balance(checksum)
        return float(self.w3.from_wei(bal_wei, "ether"))

    def tx_count(self, account: str) -> int:
        checksum = Web3.to_checksum_address(account)
        return self.w3.eth.get_transaction_count(checksum)

    def block_number(self) -> int:
        return self.w3.eth.block_number

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
        s_check = Web3.to_checksum_address(sender)
        t_check = Web3.to_checksum_address(to)
        
        tx_nonce = nonce if nonce is not None else self.w3.eth.get_transaction_count(s_check)
        gas_price = self.w3.eth.gas_price
        
        tx_dict = {
            "from": s_check,
            "to": t_check,
            "value": self.w3.to_wei(value_eth, "ether"),
            "gas": 21000,
            "gasPrice": gas_price,
            "nonce": tx_nonce,
            "chainId": 1337,
            "data": data
        }

        # If we have the private key, sign it cryptographically
        raw_signed = None
        tx_hash = None
        if s_norm in self._local_accounts:
            acc = self._local_accounts[s_norm]
            signed = acc.sign_transaction(tx_dict)
            raw_signed = signed.raw_transaction.hex()
            tx_hash = signed.hash.hex()
        else:
            # Simulated hash for genesis account
            tx_hash = "0x" + Web3.keccak(text=f"{s_norm}:{t_norm}:{tx_nonce}:{value_eth}").hex()
            raw_signed = "0xsimulated_signature"

        fee_eth = float(self.w3.from_wei(21000 * gas_price, "ether"))

        return TxRecord(
            tx_hash=tx_hash,
            sender=s_norm,
            to=t_norm,
            value_eth=float(value_eth),
            fee_eth=fee_eth,
            nonce=tx_nonce,
            timestamp=self.now(),
            block_number=None,
            status=1,
            is_broadcast=False,
            raw_signed=raw_signed,
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
        s_check = Web3.to_checksum_address(sender)
        
        # If fail is requested and we have the revert contract, route call to revert contract
        destination = Web3.to_checksum_address(to)
        gas_limit = 21000
        if fail and self._revert_contract_address:
            destination = Web3.to_checksum_address(self._revert_contract_address)
            gas_limit = 60000

        tx_nonce = nonce if nonce is not None else self.w3.eth.get_transaction_count(s_check)
        gas_price = self.w3.eth.gas_price

        tx_dict = {
            "from": s_check,
            "to": destination,
            "value": self.w3.to_wei(value_eth, "ether"),
            "gas": gas_limit,
            "gasPrice": gas_price,
            "nonce": tx_nonce,
            "chainId": 1337,
            "data": data
        }

        if s_norm in self._local_accounts:
            # Locally generated account -> sign raw transaction and send
            acc = self._local_accounts[s_norm]
            signed = acc.sign_transaction(tx_dict)
            tx_hash_bytes = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hash = tx_hash_bytes.hex()
            raw_signed = signed.raw_transaction.hex()
        else:
            # Unlocked Ganache genesis account -> use send_transaction
            tx_hash_bytes = self.w3.eth.send_transaction(tx_dict)
            tx_hash = tx_hash_bytes.hex()
            raw_signed = "0xunlocked_signature"

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        block = self.w3.eth.get_block(receipt.blockNumber)
        
        fee_wei = receipt.gasUsed * receipt.effectiveGasPrice
        fee_eth = float(self.w3.from_wei(fee_wei, "ether"))

        return TxRecord(
            tx_hash=tx_hash,
            sender=s_norm,
            to=t_norm,
            value_eth=float(value_eth),
            fee_eth=fee_eth,
            nonce=tx_nonce,
            timestamp=float(block.timestamp),
            block_number=int(receipt.blockNumber),
            status=int(receipt.status),
            is_broadcast=True,
            raw_signed=raw_signed,
            data=data
        )

    def all_transactions(self) -> List[TxRecord]:
        txs: List[TxRecord] = []
        latest = self.w3.eth.block_number
        for b_num in range(latest + 1):
            block = self.w3.eth.get_block(b_num, full_transactions=True)
            for tx in block.transactions:
                try:
                    receipt = self.w3.eth.get_transaction_receipt(tx.hash)
                    status = receipt.status if receipt else 1
                    gas_used = receipt.gasUsed if receipt else 21000
                except Exception:
                    status = 1
                    gas_used = 21000

                val_eth = float(self.w3.from_wei(tx.value, "ether"))
                fee_eth = float(self.w3.from_wei(gas_used * tx.gasPrice, "ether"))
                
                txs.append(TxRecord(
                    tx_hash=tx.hash.hex(),
                    sender=tx["from"].lower(),
                    to=tx["to"].lower() if tx["to"] else "",
                    value_eth=val_eth,
                    fee_eth=fee_eth,
                    nonce=int(tx.nonce),
                    timestamp=float(block.timestamp),
                    block_number=b_num,
                    status=int(status),
                    is_broadcast=True
                ))
        return txs

    def info(self) -> Dict[str, Any]:
        return {
            "backend": "GanacheChain",
            "rpc_url": self.rpc_url,
            "connected": self.w3.is_connected(),
            "latest_block": self.w3.eth.block_number,
            "genesis_accounts": len(self.genesis_accounts),
            "revert_contract": self._revert_contract_address
        }
