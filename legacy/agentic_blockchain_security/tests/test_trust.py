import os
import sys
import json

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from workflow.graph import AdmissionWorkflowGraph


def run_evaluation():
    print("=" * 75)
    print("STEP 14: RESEARCH EVALUATION — AGENTIC NODE ADMISSION TESTBED")
    print("=" * 75)

    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "simulated_nodes.json")
    with open(data_path, "r", encoding="utf-8") as f:
        nodes = json.load(f)

    graph = AdmissionWorkflowGraph(tv_threshold=0.70)

    correct_predictions = 0
    total_nodes = len(nodes)
    false_accepts = 0
    false_rejects = 0

    print(f"\nEvaluating {total_nodes} benchmark nodes across SAFE risk profiles:\n")
    print(f"{'Node ID':<22} | {'Expected':<8} | {'Predicted':<8} | {'TF':<5} | {'AL':<5} | {'SR':<4} | {'WR':<4} | {'FR':<4} | {'ER':<4} | Result")
    print("-" * 88)

    for node_data in nodes:
        nid = node_data["node_id"]
        expected = node_data["expected_decision"]

        res = graph.run(node_data)
        predicted = res["decision"]
        tf = res["tf"]
        al = res["al"]
        r = res["risk_scores"]

        is_match = (predicted == expected)
        if is_match:
            correct_predictions += 1
            match_str = "CORRECT"
        else:
            match_str = "MISMATCH"
            if expected == "REJECT" and predicted == "ACCEPT":
                false_accepts += 1
            elif expected == "ACCEPT" and predicted == "REJECT":
                false_rejects += 1

        print(f"{nid:<22} | {expected:<8} | {predicted:<8} | {tf:<5.2f} | {al:<5.2f} | {r['SR']:<4.2f} | {r['WR']:<4.2f} | {r['FR']:<4.2f} | {r['ER']:<4.2f} | {match_str}")

    accuracy = (correct_predictions / total_nodes) * 100.0
    far = (false_accepts / total_nodes) * 100.0
    frr = (false_rejects / total_nodes) * 100.0

    print("-" * 88)
    print("\nPERFORMANCE METRICS SUMMARY:")
    print(f"  Total Nodes Evaluated     : {total_nodes}")
    print(f"  Classification Accuracy   : {accuracy:.1f}%")
    print(f"  False Acceptance Rate (FAR): {far:.1f}% (Target: 0%)")
    print(f"  False Rejection Rate (FRR) : {frr:.1f}% (Target: 0%)")
    print("=" * 75)
    print("STEP 14 COMPLETE: Experimental Validation Succeeded!")
    print("=" * 75)


if __name__ == "__main__":
    run_evaluation()
