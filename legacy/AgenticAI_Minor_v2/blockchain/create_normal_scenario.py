import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

rpc_url = os.getenv("BLOCKCHAIN_RPC_URL")
w3 = Web3(Web3.HTTPProvider(rpc_url))

if not w3.is_connected():
    raise ConnectionError("Could not connect to Ganache.")

accounts = w3.eth.accounts


def run_normal_scenario():

    print("\n========================================")
    print("       NORMAL ACTIVITY TEST SCENARIO")
    print("========================================")

    print("Connected to Ganache")
    print("Accounts available:", len(accounts))

    # ACCOUNT ROLES
    account_a = accounts[7]
    account_b = accounts[8]
    account_c = accounts[9]

    target_a = accounts[1]
    target_b = accounts[5]
    target_c = accounts[6]

    print("\n========== ACCOUNT ROLES ==========")
    print("Account A :", account_a)
    print("Account B :", account_b)
    print("Account C :", account_c)

    print("\nTargets:")
    print("Target A  :", target_a)
    print("Target B  :", target_b)
    print("Target C  :", target_c)


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


    print("\n========== NORMAL TRANSACTIONS ==========")

    send_transaction(
        account_a,
        target_a,
        0.30
    )

    send_transaction(
        account_b,
        target_b,
        0.80
    )

    send_transaction(
        account_c,
        target_c,
        0.20
    )

    send_transaction(
        account_a,
        target_b,
        0.15
    )


    print("\n========================================")
    print("       NORMAL SCENARIO COMPLETED")
    print("========================================")

    print("\nThe accounts intentionally have:")
    print("- Different transaction amounts")
    print("- Different receiver patterns")
    print("- Different transaction behaviour")
    print("- No common funding sequence")


# Allows the file to still be run directly
if __name__ == "__main__":
    run_normal_scenario()