import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

rpc_url = os.getenv("BLOCKCHAIN_RPC_URL")
w3 = Web3(Web3.HTTPProvider(rpc_url))

if not w3.is_connected():
    raise ConnectionError("Could not connect to Ganache.")

accounts = w3.eth.accounts

print("Connected to Ganache")
print("Accounts available:", len(accounts))

sender = accounts[0]
receiver = accounts[1]

print("\nSending transaction...")
print("From:", sender)
print("To:", receiver)

transaction = {
    "from": sender,
    "to": receiver,
    "value": w3.to_wei(1, "ether"),
    "gas": 21000,
    "gasPrice": w3.eth.gas_price,
    "nonce": w3.eth.get_transaction_count(sender)
}

tx_hash = w3.eth.send_transaction(transaction)

receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

print("\nTransaction completed")
print("Transaction hash:", tx_hash.hex())
print("Block number:", receipt.blockNumber)