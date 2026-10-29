from blockchain.data_collector import BlockchainDataCollector
from agents.monitor_agent import MonitorAgent
from agents.sybil_agent import SybilAgent
from scoring.trust_calculator import TrustCalculator


def main():

    print("\n========================================")
    print("      BLOCKCHAIN NODE ADMISSION")
    print("========================================")

    # -----------------------------------------
    # STEP 1: Collect blockchain evidence
    # -----------------------------------------

    collector = BlockchainDataCollector()

    blockchain_data = collector.collect_all_data()

    # -----------------------------------------
    # STEP 2: Monitor Agent
    # -----------------------------------------

    monitor = MonitorAgent()

    monitor_evidence = monitor.analyze(
        blockchain_data
    )

    print("\n========== MONITOR EVIDENCE ==========")

    for key, value in monitor_evidence.items():
        print(f"{key}: {value}")

    # -----------------------------------------
    # STEP 3: Sybil Agent
    # -----------------------------------------

    sybil = SybilAgent()

    sybil_result = sybil.analyze(
        blockchain_data
    )

    # -----------------------------------------
    # STEP 4: Trust Assessment
    # -----------------------------------------

    calculator = TrustCalculator()

    trust_result = calculator.calculate(
        sybil_result
    )

    print("\n========== TRUST ASSESSMENT ==========")

    print(
        "Sybil Risk        :",
        round(
            trust_result["sybil_risk"],
            3
        )
    )

    print(
        "Provisional Trust :",
        round(
            trust_result["provisional_trust"],
            3
        )
    )

    print(
        "Trust Level       :",
        trust_result["trust_level"]
    )

    # -----------------------------------------
    # STEP 5: Admission recommendation
    # -----------------------------------------

    print("\n========== ADMISSION ASSESSMENT ==========")

    if sybil_result["risk_level"] == "HIGH":

        recommendation = "MANUAL REVIEW REQUIRED"

    elif sybil_result["risk_level"] == "MEDIUM":

        recommendation = "MANUAL REVIEW REQUIRED"

    else:

        recommendation = "PROVISIONAL ADMISSION"

    print(
        "Recommendation:",
        recommendation
    )

    # -----------------------------------------
    # STEP 6: Human decision
    # -----------------------------------------

    print("\n========== HUMAN-IN-THE-LOOP ==========")

    print(
        "Final admission decision must be made "
        "by the administrator."
    )


if __name__ == "__main__":
    main()