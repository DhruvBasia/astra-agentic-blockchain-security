"""
Configuration management for ASTRA.
All weights, thresholds, and simulation parameters are encapsulated here,
with overrides available via environment variables (.env).
"""

import os
from dataclasses import dataclass
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ASTRAConfig:
    # ----------------------------------------------------
    # Attack Risk (AR) Weights
    # AR = 0.30*S + 0.20*W + 0.20*F + 0.30*E
    # ----------------------------------------------------
    weight_sybil: float = float(os.getenv("ASTRA_WEIGHT_SYBIL", "0.30"))
    weight_wallet: float = float(os.getenv("ASTRA_WEIGHT_WALLET", "0.20"))
    weight_finney: float = float(os.getenv("ASTRA_WEIGHT_FINNEY", "0.20"))
    weight_eclipse: float = float(os.getenv("ASTRA_WEIGHT_ECLIPSE", "0.30"))

    # ----------------------------------------------------
    # Positive Trust (PT) Weights
    # PT = 0.25*I + 0.20*T + 0.20*N + 0.20*H + 0.15*B
    # ----------------------------------------------------
    weight_pt_i: float = float(os.getenv("ASTRA_WEIGHT_PT_I", "0.25"))
    weight_pt_t: float = float(os.getenv("ASTRA_WEIGHT_PT_T", "0.20"))
    weight_pt_n: float = float(os.getenv("ASTRA_WEIGHT_PT_N", "0.20"))
    weight_pt_h: float = float(os.getenv("ASTRA_WEIGHT_PT_H", "0.20"))
    weight_pt_b: float = float(os.getenv("ASTRA_WEIGHT_PT_B", "0.15"))

    # ----------------------------------------------------
    # Trust Factor (TF) Formulation
    # TF = 0.60*PT + 0.40*(1 - AR)
    # ----------------------------------------------------
    weight_tf_pt: float = float(os.getenv("ASTRA_WEIGHT_TF_PT", "0.60"))
    weight_tf_ar: float = float(os.getenv("ASTRA_WEIGHT_TF_AR", "0.40"))

    # Decision Threshold TV
    threshold_tv: float = float(os.getenv("ASTRA_THRESHOLD_TV", "0.70"))

    # Escalation Flag Threshold (Documented Extension)
    escalation_risk_threshold: float = float(os.getenv("ASTRA_ESCALATION_THRESHOLD", "0.75"))

    # ----------------------------------------------------
    # Observation Window Parameters
    # ----------------------------------------------------
    observation_window_size: int = int(os.getenv("ASTRA_OBSERVATION_WINDOW_SIZE", "10"))

    # ----------------------------------------------------
    # Blockchain Connection
    # ----------------------------------------------------
    blockchain_rpc_url: str = os.getenv("BLOCKCHAIN_RPC_URL", "http://127.0.0.1:7545")

    # ----------------------------------------------------
    # Consensus Simulation Defaults
    # ----------------------------------------------------
    block_time_mean_seconds: float = float(os.getenv("ASTRA_BLOCK_TIME_MEAN", "30.0"))
    block_propagation_delay_mean: float = float(os.getenv("ASTRA_PROP_DELAY_MEAN", "0.8"))
    tie_breaking_gamma: float = float(os.getenv("ASTRA_TIE_GAMMA", "0.5"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "AR_weights": {
                "Sybil": self.weight_sybil,
                "Wallet": self.weight_wallet,
                "Finney": self.weight_finney,
                "Eclipse": self.weight_eclipse,
            },
            "PT_weights": {
                "Identity (I)": self.weight_pt_i,
                "Transaction (T)": self.weight_pt_t,
                "Network (N)": self.weight_pt_n,
                "History (H)": self.weight_pt_h,
                "Behavior (B)": self.weight_pt_b,
            },
            "TF_weights": {
                "Positive Trust (PT)": self.weight_tf_pt,
                "Inverted Risk (1-AR)": self.weight_tf_ar,
            },
            "Threshold_TV": self.threshold_tv,
            "Escalation_Risk_Threshold": self.escalation_risk_threshold,
            "Observation_Window_Size": self.observation_window_size,
            "Blockchain_RPC": self.blockchain_rpc_url,
        }


# Global default configuration instance
DEFAULT_CONFIG = ASTRAConfig()
