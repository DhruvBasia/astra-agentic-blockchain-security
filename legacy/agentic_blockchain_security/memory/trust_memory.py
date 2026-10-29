"""
STEP 12: Trust Memory
Stores admission history, Trust Factor (TF) trajectories, Attack Levels (AL),
and decisions for continuous adaptation over time.
"""

import time
import json
from typing import Dict, Any, List, Optional


class TrustMemory:
    """
    Lightweight, persistent in-memory and JSON storage for node admission history.
    """
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self.memory: Dict[str, List[Dict[str, Any]]] = {}

    def record_decision(
        self,
        node_id: str,
        wallet_address: str,
        tf: float,
        al: float,
        decision: str,
        risk_scores: Dict[str, float],
        positive_parameters: Dict[str, float],
        reason: str
    ) -> Dict[str, Any]:
        """Records an admission evaluation in memory"""
        record = {
            "node_id": node_id,
            "wallet_address": wallet_address,
            "tf": tf,
            "al": al,
            "decision": decision,
            "risk_scores": risk_scores,
            "positive_parameters": positive_parameters,
            "reason": reason,
            "timestamp": time.time(),
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        if node_id not in self.memory:
            self.memory[node_id] = []
        self.memory[node_id].append(record)

        if self.storage_path:
            self.save_to_disk()

        return record

    def get_node_history(self, node_id: str) -> List[Dict[str, Any]]:
        """Retrieves past records for a specific node"""
        return self.memory.get(node_id, [])

    def get_latest_record(self, node_id: str) -> Optional[Dict[str, Any]]:
        history = self.get_node_history(node_id)
        return history[-1] if history else None

    def get_all_records(self) -> List[Dict[str, Any]]:
        all_recs = []
        for records in self.memory.values():
            all_recs.extend(records)
        return sorted(all_recs, key=lambda x: x["timestamp"], reverse=True)

    def save_to_disk(self):
        if not self.storage_path:
            return
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            print(f"[TrustMemory] Warning: Could not write to disk: {e}")
