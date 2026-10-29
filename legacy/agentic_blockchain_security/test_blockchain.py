"""
STEP 1: Blockchain Connection Verification
Connects to Ganache local test network using Web3.py
"""

from blockchain.web3_client import get_web3_connection


def main():
    print("=" * 60)
    print("STEP 1: Testing Web3 / Ganache Connection...")
    print("=" * 60)

    w3, info = get_web3_connection()

    if info["connected"]:
        print(f"Connected to Ganache successfully! ({info['rpc_url']})")
        print(f"Current Block number: {info['block_number']}")
        print(f"Available Accounts ({len(info['accounts'])}):")
        for acc in info["accounts"][:5]:
            bal = w3.eth.get_balance(acc)
            print(f"  {acc} (Balance: {w3.from_wei(bal, 'ether')} ETH)")
    else:
        print(f"[Notice] Ganache GUI is not actively listening on {info['rpc_url']}.")
        print("Using Local Simulation Fallback Accounts for prototype demonstration:")
        for acc in info["accounts"]:
            print(f"  {acc}")

    print("=" * 60)
    print("STEP 1: Blockchain Client Ready!")
    print("=" * 60)


if __name__ == "__main__":
    main()
