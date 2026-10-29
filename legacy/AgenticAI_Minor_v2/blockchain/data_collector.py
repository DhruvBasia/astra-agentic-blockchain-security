import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()


class BlockchainDataCollector:

    def __init__(self):
        rpc_url = os.getenv("BLOCKCHAIN_RPC_URL")

        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not self.w3.is_connected():
            raise ConnectionError("Could not connect to Ganache.")

    def get_blockchain_info(self):
        latest_block = self.w3.eth.block_number
        accounts = self.w3.eth.accounts

        print("\n========== BLOCKCHAIN INFORMATION ==========")
        print("Network connected      : Yes")
        print("Latest block           :", latest_block)
        print("Number of accounts     :", len(accounts))

        return {
            "latest_block": latest_block,
            "accounts": accounts
        }

    def get_account_data(self):

        accounts = self.w3.eth.accounts
        account_data = []

        for address in accounts:

            balance_wei = self.w3.eth.get_balance(address)
            balance_eth = self.w3.from_wei(balance_wei, "ether")

            transaction_count = self.w3.eth.get_transaction_count(address)

            account = {
                "address": address,
                "balance_eth": float(balance_eth),
                "transaction_count": transaction_count
            }

            account_data.append(account)

        return account_data

    def get_transaction_data(self):

        latest_block = self.w3.eth.block_number
        transactions = []

        for block_number in range(latest_block + 1):

            block = self.w3.eth.get_block(
                block_number,
                full_transactions=True
            )

            for tx in block.transactions:

                block_timestamp = block["timestamp"]

                transaction = {
                    "block_number": block_number,
                    "transaction_hash": tx["hash"].hex(),
                    "sender": tx["from"],
                    "receiver": tx["to"],
                    "value_eth": float(
                        self.w3.from_wei(tx["value"], "ether")
                    ),
                    "timestamp": block_timestamp,
                    "transaction_index": tx["transactionIndex"],
                    "nonce": tx["nonce"]
                }

                transactions.append(transaction)

        return transactions

    def collect_all_data(self):

        blockchain_info = self.get_blockchain_info()
        accounts = self.get_account_data()
        transactions = self.get_transaction_data()

        data = {
            "blockchain": blockchain_info,
            "accounts": accounts,
            "transactions": transactions
        }

        return data


if __name__ == "__main__":

    collector = BlockchainDataCollector()

    data = collector.collect_all_data()

    print("\n========== ACCOUNT DATA ==========")

    for account in data["accounts"]:
        print(
            f"Address: {account['address']} | "
            f"Balance: {account['balance_eth']} ETH | "
            f"Transactions: {account['transaction_count']}"
        )

    print("\n========== TRANSACTION DATA ==========")

    for transaction in data["transactions"]:
        print(
            f"Block: {transaction['block_number']} | "
            f"From: {transaction['sender']} | "
            f"To: {transaction['receiver']} | "
            f"Value: {transaction['value_eth']} ETH | "
            f"Timestamp: {transaction['timestamp']} | "
            f"Tx Index: {transaction['transaction_index']} | "
            f"Nonce: {transaction['nonce']}"
        )