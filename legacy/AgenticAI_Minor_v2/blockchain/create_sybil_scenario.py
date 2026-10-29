import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

rpc_url = os.getenv("BLOCKCHAIN_RPC_URL")
w3 = Web3(Web3.HTTPProvider(rpc_url))

if not w3.is_connected():
    raise ConnectionError("Could not connect to Ganache.")

accounts = w3.eth.accounts


def run_sybil_scenario():

    print("\n========================================")
    print("       SYBIL ATTACK TEST SCENARIO")
    print("========================================")

    print("Connected to Ganache")
    print("Accounts available:", len(accounts))


    # --------------------------------------------------
    # ACCOUNT ROLES
    # --------------------------------------------------

    funder = accounts[0]

    sybil_accounts = [
        accounts[2],
        accounts[3],
        accounts[4]
    ]

    target_x = accounts[5]
    target_y = accounts[6]


    print("\n========== ACCOUNT ROLES ==========")

    print("Common Funder :", funder)

    for i, account in enumerate(sybil_accounts, start=1):
        print(f"Candidate A{i} :", account)

    print("Target X      :", target_x)
    print("Target Y      :", target_y)


    # --------------------------------------------------
    # TRANSACTION FUNCTION
    # --------------------------------------------------

    def send_transaction(sender, receiver, amount_eth):

        nonce = w3.eth.get_transaction_count(sender)

        transaction = {
            "from": sender,
            "to": receiver,
            "value": w3.to_wei(amount_eth, "ether"),
            "gas": 21000,
            "gasPrice": w3.eth.gas_price,
            "nonce": nonce
        }

        tx_hash = w3.eth.send_transaction(transaction)

        receipt = w3.eth.wait_for_transaction_receipt(
            tx_hash
        )

        print(
            f"Transaction: {sender[:10]}... -> "
            f"{receiver[:10]}... | "
            f"{amount_eth} ETH | "
            f"Block: {receipt.blockNumber}"
        )

        return receipt


    # --------------------------------------------------
    # COMMON FUNDING
    # --------------------------------------------------

    print("\n========== COMMON FUNDING ==========")

    for account in sybil_accounts:

        send_transaction(
            funder,
            account,
            1.0
        )


    # --------------------------------------------------
    # COORDINATED TRANSACTIONS
    # --------------------------------------------------

    print("\n========== COORDINATED TRANSACTIONS ==========")

    for account in sybil_accounts:

        send_transaction(
            account,
            target_x,
            0.5
        )

        send_transaction(
            account,
            target_y,
            0.25
        )


    # --------------------------------------------------
    # COMPLETION
    # --------------------------------------------------

    print("\n========================================")
    print("       SYBIL SCENARIO COMPLETED")
    print("========================================")

    print("\nCandidate accounts performed:")
    print("- Same funding pattern")
    print("- Same receiver pattern")
    print("- Same transaction amounts")
    print("- Similar transaction sequence")


# --------------------------------------------------
# ALLOW DIRECT EXECUTION
# --------------------------------------------------

if __name__ == "__main__":
    run_sybil_scenario()