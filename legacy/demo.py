"""
ASTRA: Blockchain Node Admission Security
Evaluation Demo Script for Minor Project
Authors: Dhruv Basia & Amisha Rawat | Supervisor: Prof. Rahul Johari
"""

import os
import sys

# Ensure local packages are importable
current_dir = os.path.dirname(os.path.abspath(__file__))
pkg_dir = os.path.join(current_dir, "agentic_blockchain_security")
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from blockchain.web3_client import get_web3_connection
from node_join import get_live_blockchain_nodes
from agents.monitor_agent import MonitorAgent
from agents.sybil_agent import SybilAgent
from agents.wallet_agent import WalletAgent
from agents.finney_agent import FinneyAgent
from agents.eclipse_agent import EclipseAgent
from scoring.trust_calculator import TrustCalculator


def run_node_admission(scenario_name: str, node_req):
    print("\n" + "=" * 70)
    print(f"EVALUATING SCENARIO: {scenario_name}")
    print("=" * 70)

    # STEP 2: Node Join Request (Real on-chain data)
    print(f"[STEP 2] Node Join Request Received")
    print(f"  * Node ID        : {node_req.node_id}")
    print(f"  * Wallet Address : {node_req.wallet_address}")
    print(f"  * On-Chain Stake : {node_req.stake_eth:.2f} ETH")
    print(f"  * On-Chain Nonce : {node_req.transaction_count} txs")
    print(f"  * Identity Age   : {node_req.identity_age_days} days")
    print(f"  * Peer Count     : {node_req.peer_count} peers")

    # STEP 3: Monitor Agent
    monitor = MonitorAgent()
    evidence = monitor.process_join_request(node_req.to_dict())
    print(f"\n[STEP 3] Monitor Agent: Evidence Extracted and Validated")

    # STEP 4: 4 Specialized Attack Agents
    sybil_res = SybilAgent().evaluate(evidence.sybil_evidence)
    wallet_res = WalletAgent().evaluate(evidence.wallet_evidence)
    finney_res = FinneyAgent().evaluate(evidence.finney_evidence)
    eclipse_res = EclipseAgent().evaluate(evidence.eclipse_evidence)

    sr = sybil_res["sybil_risk"]
    wr = wallet_res["wallet_risk"]
    fr = finney_res["finney_risk"]
    er = eclipse_res["eclipse_risk"]

    print(f"\n[STEP 4] Multi-Agent Attack Risk Evaluation (SAFE Suite)")
    print(f"  * Sybil Risk (SR)        : {sr:.2f}")
    print(f"  * Attack Wallet Risk (WR): {wr:.2f}")
    print(f"  * Finney Attack Risk (FR): {fr:.2f}")
    print(f"  * Eclipse Attack Risk (ER): {er:.2f}")

    # STEP 5: Trust Factor Calculation
    calc = TrustCalculator(tv_threshold=0.70)
    pos = evidence.positive_indicators
    res = calc.evaluate_admission(
        sr=sr, wr=wr, fr=fr, er=er,
        i=pos["identity_maturity_score"],
        t=pos["transaction_stability_score"],
        n=pos["network_connectivity_score"],
        h=0.50,
        b=pos["consistency_factor"]
    )

    print(f"\n[STEP 5] Trust Scoring")
    print(f"  * Attack Level (AL)      : {res['al']:.2f}  [Formula: 0.30(SR) + 0.20(WR) + 0.20(FR) + 0.30(ER)]")
    print(f"  * Positive Trust (PT)    : {res['pt']:.2f}  [Formula: 0.25(I) + 0.20(T) + 0.20(N) + 0.20(H) + 0.15(B)]")
    print(f"  * Trust Factor (TF)      : {res['tf']:.2f}  [Formula: 0.60(PT) + 0.40(1 - AL)]")
    print(f"  * Threshold Value (TV)   : {res['tv']:.2f}")

    # STEP 6: Final Decision
    print(f"\n[STEP 6] Final Admission Decision")
    if res["decision"] == "ACCEPT":
        print(f"  >>> DECISION: ACCEPTED (TF {res['tf']:.2f} > TV {res['tv']:.2f}) <<<")
        print(f"  Action: Node allowed to participate in consensus.")
    else:
        print(f"  >>> DECISION: REJECTED (TF {res['tf']:.2f} <= TV {res['tv']:.2f}) <<<")
        print(f"  Reason: {res['reason']}")
        print(f"  Action: Node blocked pre-admission. Zero damage to blockchain ledger.")


def main():
    print("=" * 70)
    print("ASTRA: AGENTIC AI BLOCKCHAIN NODE ADMISSION SECURITY")
    print("Minor Project Prototype | USAR, GGSIPU")
    print("=" * 70)

    # STEP 1: Verify Ganache Connection
    print("\n[STEP 1] Connecting to Ganache via Web3.py...")
    w3, info = get_web3_connection()
    if info["connected"]:
        print(f"  * Connected to Ganache: {info['rpc_url']}")
        print(f"  * Current Block Number: {info['block_number']}")
        print(f"  * Total Active Accounts: {len(info['accounts'])}")
    else:
        print("  * Ganache connection: Using local test accounts")

    # Fetch live nodes
    live_nodes = get_live_blockchain_nodes()

    # Run Honest Node Demo
    run_node_admission("Case 1: Honest Node Joining", live_nodes["HONEST"])

    # Run Sybil Attack Demo
    run_node_admission("Case 2: Sybil Attack Node Joining", live_nodes["SYBIL"])

    # Run Finney Attack Demo
    run_node_admission("Case 3: Finney Double-Spend Node Joining", live_nodes["FINNEY"])

    print("\n" + "=" * 70)
    print("DEMO COMPLETE: All nodes evaluated pre-admission.")
    print("=" * 70)


if __name__ == "__main__":
    main()
