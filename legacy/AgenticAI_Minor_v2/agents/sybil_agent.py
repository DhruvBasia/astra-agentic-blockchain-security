from collections import defaultdict


class SybilAgent:

    # Prototype weights
    FUNDING_WEIGHT = 0.35
    BEHAVIOR_WEIGHT = 0.30
    TIMING_WEIGHT = 0.15
    INTERACTION_WEIGHT = 0.20
    def analyze(self, blockchain_data):

        accounts = blockchain_data["accounts"]
        transactions = blockchain_data["transactions"]

        print("\n========== SYBIL AGENT ==========")

        # -----------------------------------------
        # Build outgoing transaction history
        # -----------------------------------------

        outgoing = defaultdict(list)

        # Build incoming transaction history
        incoming = defaultdict(list)

        for tx in transactions:

            sender = tx["sender"]
            receiver = tx["receiver"]

            outgoing[sender].append(tx)

            if receiver is not None:
                incoming[receiver].append(tx)

        # -----------------------------------------
        # Find active accounts
        # -----------------------------------------

        active_accounts = [
            account["address"]
            for account in accounts
            if len(outgoing[account["address"]]) > 0
        ]

        if len(active_accounts) < 2:

            print("Not enough active accounts.")

            return {
                "risk_score": 0.0,
                "risk_level": "INSUFFICIENT EVIDENCE",
                "suspicious_group": [],
                "evidence": [
                    "Not enough active accounts for Sybil analysis."
                ]
            }

        # -----------------------------------------
        # Compare account pairs
        # -----------------------------------------

        pair_results = []

        for i in range(len(active_accounts)):

            for j in range(i + 1, len(active_accounts)):

                account_a = active_accounts[i]
                account_b = active_accounts[j]

                tx_a = outgoing[account_a]
                tx_b = outgoing[account_b]

                behavior = self.calculate_behavior_similarity(
                    tx_a,
                    tx_b
                )

                timing = self.calculate_timing_similarity(
                    tx_a,
                    tx_b
                )

                interaction = self.calculate_interaction_similarity(
                    tx_a,
                    tx_b
                )

                common_funding = self.calculate_common_funding(
                    account_a,
                    account_b,
                    incoming
                )

                pair_score = (
                    self.FUNDING_WEIGHT * common_funding
                    + self.BEHAVIOR_WEIGHT * behavior
                    + self.TIMING_WEIGHT * timing
                    + self.INTERACTION_WEIGHT * interaction
                )

                pair_results.append({
                    "account_a": account_a,
                    "account_b": account_b,
                    "common_funding": common_funding,
                    "behavior_similarity": behavior,
                    "timing_similarity": timing,
                    "interaction_similarity": interaction,
                    "pair_score": pair_score
                })

        # -----------------------------------------
        # Find strongest suspicious pair
        # -----------------------------------------

        strongest_pair = max(
            pair_results,
            key=lambda x: x["pair_score"]
        )

        risk_score = strongest_pair["pair_score"]

        # -----------------------------------------
        # Risk classification
        # -----------------------------------------

        if risk_score >= 0.70:
            risk_level = "HIGH"

        elif risk_score >= 0.40:
            risk_level = "MEDIUM"

        else:
            risk_level = "LOW"

        # -----------------------------------------
        # Identify suspicious group
        # -----------------------------------------

        suspicious_group = [
            strongest_pair["account_a"],
            strongest_pair["account_b"]
        ]

        # Add accounts that are also strongly
        # similar to the suspicious pair
        reference_account = strongest_pair["account_a"]

        for result in pair_results:

            if (
                result["account_a"] == reference_account
                and result["pair_score"] >= 0.70
            ):

                if result["account_b"] not in suspicious_group:
                    suspicious_group.append(
                        result["account_b"]
                    )

            elif (
                result["account_b"] == reference_account
                and result["pair_score"] >= 0.70
            ):

                if result["account_a"] not in suspicious_group:
                    suspicious_group.append(
                        result["account_a"]
                    )

        # -----------------------------------------
        # Generate evidence
        # -----------------------------------------

        evidence = []

        if strongest_pair["common_funding"] >= 0.70:

            evidence.append(
                "Candidate accounts received funds "
                "from the same transaction-level funding source."
            )

        if strongest_pair["behavior_similarity"] >= 0.70:

            evidence.append(
                "Candidate accounts show highly similar "
                "transaction behaviour."
            )

        if strongest_pair["interaction_similarity"] >= 0.70:

            evidence.append(
                "Candidate accounts interact with the "
                "same counterparties."
            )

        if strongest_pair["timing_similarity"] >= 0.70:

            evidence.append(
                "Candidate accounts show closely "
                "coordinated transaction timing."
            )

        if not evidence:

            evidence.append(
                "No strong coordinated identity pattern detected."
            )

        # -----------------------------------------
        # Print results
        # -----------------------------------------

        print(
            "Active accounts          :",
            len(active_accounts)
        )

        print(
            "Strongest pair           :",
            strongest_pair["account_a"],
            "<->",
            strongest_pair["account_b"]
        )

        print(
            "Common funding           :",
            round(
                strongest_pair["common_funding"],
                3
            )
        )

        print(
            "Behaviour similarity     :",
            round(
                strongest_pair["behavior_similarity"],
                3
            )
        )

        print(
            "Timing similarity        :",
            round(
                strongest_pair["timing_similarity"],
                3
            )
        )

        print(
            "Interaction similarity  :",
            round(
                strongest_pair["interaction_similarity"],
                3
            )
        )

        print(
            "Overall Sybil Risk       :",
            round(risk_score, 3)
        )

        print(
            "Risk Level               :",
            risk_level
        )

        print("\nSuspicious group:")

        for account in suspicious_group:
            print("-", account)

        print("\nEvidence:")

        for item in evidence:
            print("-", item)

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "suspicious_group": suspicious_group,
            "common_funding": strongest_pair[
                "common_funding"
            ],
            "behavior_similarity": strongest_pair[
                "behavior_similarity"
            ],
            "timing_similarity": strongest_pair[
                "timing_similarity"
            ],
            "interaction_similarity": strongest_pair[
                "interaction_similarity"
            ],
            "evidence": evidence
        }

    # ==================================================
    # BEHAVIOUR SIMILARITY
    # ==================================================

    def calculate_behavior_similarity(
        self,
        tx_a,
        tx_b
    ):

        if not tx_a or not tx_b:
            return 0.0

        receivers_a = {
            tx["receiver"]
            for tx in tx_a
            if tx["receiver"] is not None
        }

        receivers_b = {
            tx["receiver"]
            for tx in tx_b
            if tx["receiver"] is not None
        }

        if not receivers_a or not receivers_b:
            return 0.0

        intersection = receivers_a.intersection(
            receivers_b
        )

        union = receivers_a.union(
            receivers_b
        )

        receiver_similarity = (
            len(intersection) /
            len(union)
        )

        # Compare average transaction value

        avg_a = (
            sum(tx["value_eth"] for tx in tx_a)
            / len(tx_a)
        )

        avg_b = (
            sum(tx["value_eth"] for tx in tx_b)
            / len(tx_b)
        )

        max_value = max(
            avg_a,
            avg_b,
            1e-9
        )

        value_similarity = 1 - (
            abs(avg_a - avg_b)
            / max_value
        )

        value_similarity = max(
            0.0,
            min(1.0, value_similarity)
        )

        # Compare number of transactions

        count_difference = abs(
            len(tx_a) - len(tx_b)
        )

        max_count = max(
            len(tx_a),
            len(tx_b),
            1
        )

        count_similarity = 1 - (
            count_difference / max_count
        )

        return (
            0.50 * receiver_similarity
            + 0.30 * value_similarity
            + 0.20 * count_similarity
        )

    # ==================================================
    # INTERACTION SIMILARITY
    # ==================================================

    def calculate_interaction_similarity(
        self,
        tx_a,
        tx_b
    ):

        receivers_a = {
            tx["receiver"]
            for tx in tx_a
            if tx["receiver"] is not None
        }

        receivers_b = {
            tx["receiver"]
            for tx in tx_b
            if tx["receiver"] is not None
        }

        if not receivers_a or not receivers_b:
            return 0.0

        intersection = receivers_a.intersection(
            receivers_b
        )

        union = receivers_a.union(
            receivers_b
        )

        return len(intersection) / len(union)

    # ==================================================
    # TIMING SIMILARITY
    # ==================================================

    def calculate_timing_similarity(self, tx_a, tx_b):

        if not tx_a or not tx_b:
            return 0.0

        # Compare transactions using blockchain block distance
        # instead of relying only on timestamps.
        block_differences = []

        for transaction_a in tx_a:
            for transaction_b in tx_b:

                block_a = transaction_a.get("block_number")
                block_b = transaction_b.get("block_number")

                if block_a is not None and block_b is not None:
                    block_differences.append(
                        abs(block_a - block_b)
                    )

        if not block_differences:
            return 0.0

        minimum_block_difference = min(block_differences)

        # Transactions in the same or adjacent blocks are
        # more temporally related than transactions far apart.
        if minimum_block_difference == 0:
            return 1.0

        elif minimum_block_difference == 1:
            return 0.5

        elif minimum_block_difference == 2:
            return 0.25

        else:
            return 0.0
    # ==================================================
    # COMMON FUNDING
    # ==================================================

    def calculate_common_funding(
        self,
        account_a,
        account_b,
        incoming
    ):

        funders_a = {
            tx["sender"]
            for tx in incoming[account_a]
            if tx["sender"] != account_a
        }

        funders_b = {
            tx["sender"]
            for tx in incoming[account_b]
            if tx["sender"] != account_b
        }

        if not funders_a or not funders_b:
            return 0.0

        common_funders = funders_a.intersection(
            funders_b
        )

        if not common_funders:
            return 0.0

        union = funders_a.union(
            funders_b
        )

        return (
            len(common_funders)
            / len(union)
        )