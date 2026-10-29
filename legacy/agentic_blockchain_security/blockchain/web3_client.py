"""
Blockchain Connection Client using Web3.py
Connects to local Ganache instance (http://127.0.0.1:7545)
"""

import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL = os.getenv("BLOCKCHAIN_RPC_URL", "http://127.0.0.1:7545")


def get_web3_connection(rpc_url: str = RPC_URL):
    """
    Connects to local Ethereum RPC (Ganache).
    Returns Web3 instance and connection info dictionary.
    """
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    is_connected = w3.is_connected()

    if is_connected:
        try:
            block_number = w3.eth.block_number
            accounts = list(w3.eth.accounts)
        except Exception:
            block_number = 0
            accounts = []
        return w3, {
            "connected": True,
            "rpc_url": rpc_url,
            "block_number": block_number,
            "accounts": accounts,
            "mode": "GANACHE_LIVE"
        }
    else:
        # Fallback simulated accounts if Ganache GUI is not currently active
        mock_accounts = [
            "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1",
            "0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0",
            "0x22d491Bde2303f2f1338540c66537775E73980E0",
            "0xE11BA2b4D45Eaed5996Cd0823791E0C93114882d",
            "0xd03ea8624C8C5987235048901fB614fDcA89b117"
        ]
        return w3, {
            "connected": False,
            "rpc_url": rpc_url,
            "block_number": 0,
            "accounts": mock_accounts,
            "mode": "SIMULATION_FALLBACK"
        }
