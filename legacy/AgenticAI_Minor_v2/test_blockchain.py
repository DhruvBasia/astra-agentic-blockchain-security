from web3 import Web3
from dotenv import load_dotenv
import os

load_dotenv()

rpc_url = os.getenv("BLOCKCHAIN_RPC_URL")

w3 = Web3(Web3.HTTPProvider(rpc_url))

if w3.is_connected():
    print("Connected to Ganache!")
else:
    print("Connection failed!")

print("Block number:", w3.eth.block_number)

print("\nAccounts:")
for account in w3.eth.accounts:
    print(account)