"""
Main Entry Point for Agentic AI Blockchain Node Admission Security
Allows evaluating sample benchmark nodes or entering custom node telemetry.
"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from workflow.graph import AdmissionWorkflowGraph
from node_join import get_sample_join_requests


def main():
    print("=" * 75)
    print("🛡️  AGENTIC AI-BASED BLOCKCHAIN NODE ADMISSION SECURITY")
    print("    Pre-Admission Trust Evaluation (TF vs TV) & SAFE Attack Defense")
    print("=" * 75)

    graph = AdmissionWorkflowGraph(tv_threshold=0.70)
    samples = get_sample_join_requests()

    print("\nSelect a node admission scenario to evaluate:")
    print("  1. Honest Node (NODE_HONEST_01)")
  
    print("  2. Sybil Identity Node (NODE_SYBIL_01)")
    print("  3. Attack Wallet Node (NODE_WALLET_RISK_01)")
    print("  4. Finney Double-Spend Node (NODE_FINNEY_RISK_01)")
    print("  5. Eclipse Isolation Node (NODE_ECLIPSE_RISK_01)")
    print("  6. Run Complete Evaluation Suite (All 7 Benchmarks)")

    choice = input("\nEnter choice (1-6) [default: 6]: ").strip() or "6"

    if choice == "1":
        node_req = samples["HONEST"].to_dict()
    elif choice == "2":
        node_req = samples["SYBIL"].to_dict()
    elif choice == "3":
        node_req = samples["ATTACK_WALLET"].to_dict()
    elif choice == "4":
        node_req = samples["FINNEY"].to_dict()
    elif choice == "5":
        node_req = samples["ECLIPSE"].to_dict()
    else:
        from tests.test_trust import run_evaluation
        run_evaluation()
        return

    print("\n" + "-" * 75)
    print(f"[*] Processing Join Request for: {node_req['node_id']} ({node_req['wallet_address']})")
    print("-" * 75)

    result = graph.run(node_req)

    print(f"\n[DECISION]: >>> {result['decision']} <<<")
    print(f"  Reason: {result['reason']}")
    print(f"\n[SCORES]:")
    print(f"  Trust Factor (TF)       : {result['tf']:.3f} (Threshold TV = {result['tv']:.2f})")
    print(f"  Overall Attack Level (AL): {result['al']:.3f}")
    print(f"  Positive Trust (PT)     : {result['pt']:.3f}")
    print(f"\n[ATTACK RISK BREAKDOWN]:")
    print(f"  - Sybil Risk (SR)       : {result['risk_scores']['SR']:.3f}")
    print(f"  - Wallet Risk (WR)      : {result['risk_scores']['WR']:.3f}")
    print(f"  - Finney Risk (FR)      : {result['risk_scores']['FR']:.3f}")
    print(f"  - Eclipse Risk (ER)     : {result['risk_scores']['ER']:.3f}")
    print(f"\n[POSITIVE TRUST PARAMETERS]:")
    for k, v in result['positive_parameters'].items():
        print(f"  - Parameter {k}          : {v:.3f}")
    print(f"\n[AGENT EXPLANATIONS]:")
    for exp in result['agent_explanations']:
        print(f"  * {exp}")
    print(f"\n[EXPLAINABLE SUMMARY]:")
    print(f"  {result['summary']}")
    print("=" * 75)


if __name__ == "__main__":
    main()
