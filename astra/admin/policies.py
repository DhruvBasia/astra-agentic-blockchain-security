"""
Administrator Policies for Human-in-the-Loop decision governance:
- InteractiveAdmin: Prompts human administrator in CLI.
- AutoAdmin: Evaluates policy for automated benchmarks and batch testing.
"""

from abc import ABC, abstractmethod
from typing import Optional
from astra.pre_admission.types import (
    TrustEvaluation,
    AdminAction,
    AdminDecisionRecord,
    Recommendation
)


class AdminPolicy(ABC):
    """Abstract base class for human administration decisions."""

    @abstractmethod
    def decide(self, evaluation: TrustEvaluation) -> AdminDecisionRecord:
        pass


class AutoAdmin(AdminPolicy):
    """
    Automated administrator decision policy for reproducible research benchmarking.
    Supports two evaluation modes:
      1. Formula Only: Strictly follows TF >= TV recommendation.
      2. Formula + Escalation: Rejects on REJECT, investigates if escalation_flag=True, otherwise accepts.
    """

    def __init__(self, use_escalation: bool = True):
        self.use_escalation = use_escalation

    def decide(self, evaluation: TrustEvaluation) -> AdminDecisionRecord:
        if evaluation.recommendation == Recommendation.REJECT:
            action = AdminAction.REJECT
            reason = f"Trust Factor ({evaluation.tf:.2f}) strictly below threshold TV ({evaluation.tv:.2f})"
        elif self.use_escalation and evaluation.escalation_flag:
            action = AdminAction.INVESTIGATE
            reason = f"Escalation flag triggered: {'; '.join(evaluation.escalation_reasons)}"
        else:
            action = AdminAction.ACCEPT
            reason = f"Trust Factor ({evaluation.tf:.2f}) satisfies threshold TV ({evaluation.tv:.2f})"

        return AdminDecisionRecord(
            candidate_id=evaluation.candidate_id,
            action=action,
            reason=reason,
            decided_by="AutoAdminPolicy",
            timestamp=evaluation.timestamp,
            evidence_reviewed=evaluation.escalation_reasons
        )


class InteractiveAdmin(AdminPolicy):
    """Prompts human operator via terminal input."""

    def decide(self, evaluation: TrustEvaluation) -> AdminDecisionRecord:
        print("\n" + "=" * 65)
        print("          HUMAN ADMINISTRATOR DECISION REQUIRED")
        print("=" * 65)
        print(f"Candidate ID     : {evaluation.candidate_id}")
        print(f"Wallet Address   : {evaluation.wallet_address}")
        print(f"Trust Factor (TF): {evaluation.tf:.2f} (Threshold TV: {evaluation.tv:.2f})")
        print(f"Attack Risk (AR) : {evaluation.ar:.2f}")
        print(f"Positive Trust   : {evaluation.pt:.2f}")
        print(f"AI Recommendation: {evaluation.recommendation.value}")
        print(f"Escalation Flag  : {'TRIGGERED' if evaluation.escalation_flag else 'CLEAN'}")
        
        if evaluation.escalation_reasons:
            print("\nEscalation Warnings:")
            for r in evaluation.escalation_reasons:
                print(f"  [!] {r}")

        print("\nAvailable Administrator Actions:")
        print("  [A] Accept candidate into network")
        print("  [R] Reject candidate (block pre-admission)")
        print("  [I] Request detailed investigation")

        choice = input("\nEnter decision [A/R/I] (Default A): ").strip().upper()
        if choice == "R":
            action = AdminAction.REJECT
            reason = "Administrator manually rejected candidate."
        elif choice == "I":
            action = AdminAction.INVESTIGATE
            reason = "Administrator routed candidate for forensic audit."
        else:
            action = AdminAction.ACCEPT
            reason = "Administrator accepted candidate into consensus."

        return AdminDecisionRecord(
            candidate_id=evaluation.candidate_id,
            action=action,
            reason=reason,
            decided_by="HumanCLIAdmin",
            timestamp=evaluation.timestamp,
            evidence_reviewed=evaluation.escalation_reasons
        )
