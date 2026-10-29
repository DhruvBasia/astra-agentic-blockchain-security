class MonitorAgent:

    def analyze(self, blockchain_data):

        print("\n========== MONITOR AGENT ==========")

        blockchain = blockchain_data["blockchain"]
        accounts = blockchain_data["accounts"]
        transactions = blockchain_data["transactions"]

        print("Blockchain connection : Active")
        print("Latest block          :", blockchain["latest_block"])
        print("Accounts observed     :", len(accounts))
        print("Transactions observed :", len(transactions))

        evidence = {
            "latest_block": blockchain["latest_block"],
            "account_count": len(accounts),
            "transaction_count": len(transactions)
        }

        return evidence