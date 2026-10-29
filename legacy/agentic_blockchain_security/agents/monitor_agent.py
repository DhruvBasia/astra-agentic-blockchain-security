"""
STEP 3: Monitor Agent
Role: Ingests node join requests, validates inputs, extracts and structures
multi-dimensional evidence, and prepares the telemetry payload for specialized agents.
IMPORTANT: The Monitor Agent NEVER makes an accept/reject decision.
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class StructuredNodeEvidence:
    node_id: str
    wallet_address: str
    timestamp: float
    is_valid_format: bool
    
    # Sybil Evidence Indicators
    sybil_evidence: Dict[str, Any]
    
    # Attack Wallet Indicators
    wallet_evidence: Dict[str, Any]
    
    # Finney Attack Indicators
    finney_evidence: Dict[str, Any]
    
    # Eclipse Attack Indicators
    eclipse_evidence: Dict[str, Any]
    
    # Positive Trust Indicators
    positive_indicators: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MonitorAgent:
    """
    Monitor Agent responsible for intake, sanitization, evidence extraction,
    and structured routing to downstream risk and trust agents.
    """
    def __init__(self, name: str = "Admission Monitor Agent"):
        self.name = name

    def validate_request(self, raw_node: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validates schema integrity and cryptographic formatting"""
        if not raw_node.get("node_id"):
            return False, "Missing node_id"
        
        addr = raw_node.get("wallet_address", "")
        if not addr or not isinstance(addr, str) or not addr.startswith("0x"):
            return False, f"Invalid Ethereum wallet address format: {addr}"
        
        if raw_node.get("identity_age_days", 0) < 0:
            return False, "identity_age_days cannot be negative"
            
        if raw_node.get("peer_count", 0) < 0:
            return False, "peer_count cannot be negative"

        return True, None

    def process_join_request(self, raw_node: Dict[str, Any]) -> StructuredNodeEvidence:
        """
        Receives raw node join request, validates it, and compiles structured evidence.
        """
        is_valid, validation_err = self.validate_request(raw_node)
        if not is_valid:
            raise ValueError(f"MonitorAgent validation error: {validation_err}")

        # Extract Sybil Indicators
        sybil_evidence = {
            "identity_age_days": raw_node.get("identity_age_days", 0),
            "ip_subnet": raw_node.get("ip_subnet", "192.168.1.0/24"),
            "asn": raw_node.get("asn", "UNKNOWN_ASN"),
            "stake_eth": float(raw_node.get("stake_eth", 0.0)),
            "is_new_identity": raw_node.get("identity_age_days", 0) < 7
        }

        # Extract Wallet Anomaly Indicators
        wallet_evidence = {
            "tx_count": int(raw_node.get("transaction_count", 0)),
            "tx_frequency_per_min": float(raw_node.get("recent_tx_frequency_per_min", 0.0)),
            "failed_tx_ratio": float(raw_node.get("failed_tx_ratio", 0.0)),
            "previously_flagged": bool(raw_node.get("previously_flagged", False))
        }

        # Extract Finney Risk Indicators
        finney_evidence = {
            "has_conflicting_spends": bool(raw_node.get("has_conflicting_spends", False)),
            "withholding_block_flag": bool(raw_node.get("withholding_block_flag", False)),
            "zero_conf_spend_detected": bool(raw_node.get("has_conflicting_spends", False))
        }

        # Extract Eclipse Risk Indicators
        eclipse_evidence = {
            "peer_count": int(raw_node.get("peer_count", 0)),
            "peer_diversity_score": float(raw_node.get("peer_diversity_score", 0.5)),
            "suspicious_peer_ratio": float(raw_node.get("suspicious_peer_ratio", 0.0))
        }

        # Compile Positive Trust Base Features
        positive_indicators = {
            "identity_maturity_score": min(1.0, raw_node.get("identity_age_days", 0) / 60.0),
            "transaction_stability_score": max(0.0, 1.0 - raw_node.get("failed_tx_ratio", 0.0)),
            "network_connectivity_score": min(1.0, raw_node.get("peer_count", 0) / 10.0),
            "reputation_history": 0.5 if not raw_node.get("previously_flagged") else 0.1,
            "consistency_factor": 0.85
        }

        structured_evidence = StructuredNodeEvidence(
            node_id=raw_node["node_id"],
            wallet_address=raw_node["wallet_address"],
            timestamp=raw_node.get("join_time", time.time()),
            is_valid_format=True,
            sybil_evidence=sybil_evidence,
            wallet_evidence=wallet_evidence,
            finney_evidence=finney_evidence,
            eclipse_evidence=eclipse_evidence,
            positive_indicators=positive_indicators
        )

        return structured_evidence
