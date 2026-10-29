"""
Verification Test for STEP 3: Monitor Agent
Validates ingestion, validation, and structured evidence extraction.
"""

from node_join import get_sample_join_requests
from agents.monitor_agent import MonitorAgent


def test_monitor_agent():
    print("=" * 70)
    print("STEP 3 VERIFICATION: Testing Monitor Agent Evidence Ingestion")
    print("=" * 70)

    monitor = MonitorAgent()
    samples = get_sample_join_requests()

    for category, req in samples.items():
        print(f"\n[Test Case: {category}] -> Ingesting Node: {req.node_id}")
        raw_dict = req.to_dict()
        
        # 1. Process via Monitor Agent
        evidence = monitor.process_join_request(raw_dict)
        
        # 2. Verify Output Attributes
        assert evidence.node_id == req.node_id
        assert evidence.is_valid_format is True
        assert "identity_age_days" in evidence.sybil_evidence
        assert "tx_frequency_per_min" in evidence.wallet_evidence
        assert "has_conflicting_spends" in evidence.finney_evidence
        assert "peer_diversity_score" in evidence.eclipse_evidence
        assert "identity_maturity_score" in evidence.positive_indicators

        print(f"  + Schema Validation: PASSED")
        print(f"  + Sybil Evidence: Age={evidence.sybil_evidence['identity_age_days']}d, Stake={evidence.sybil_evidence['stake_eth']} ETH")
        print(f"  + Wallet Evidence: Freq={evidence.wallet_evidence['tx_frequency_per_min']}/min, Failed Ratio={evidence.wallet_evidence['failed_tx_ratio']}")
        print(f"  + Finney Evidence: Conflicting Spend={evidence.finney_evidence['has_conflicting_spends']}, Withholding={evidence.finney_evidence['withholding_block_flag']}")
        print(f"  + Eclipse Evidence: Peers={evidence.eclipse_evidence['peer_count']}, Diversity={evidence.eclipse_evidence['peer_diversity_score']}, Suspicious={evidence.eclipse_evidence['suspicious_peer_ratio']}")

    print("\n" + "=" * 70)
    print("STEP 3: Monitor Agent Verified and Complete! Ready for Step 4 (Sybil Agent).")
    print("=" * 70)


if __name__ == "__main__":
    test_monitor_agent()
