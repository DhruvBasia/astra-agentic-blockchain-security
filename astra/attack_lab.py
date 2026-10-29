"""
Attack Lab: launch one attack against the blockchain, let the agentic pipeline
analyse it, and save the complete run to disk.

A run has three stages:
  1. launch_attack        - the attacker's transactions are executed on the chain backend
                            (real signed transactions when the backend is Ganache).
  2. analyse_with_agents  - the LangGraph admission graph runs the Sybil, Wallet, Finney and
                            Eclipse agents on the evidence, aggregates AR / PT / TF and pauses
                            for the administrator's decision.
  3. save_attack_run      - attack footprint, agent evidence and the decision are written
                            as a JSON record and a Markdown report.

Stage 2 is split into start_analysis (runs to the human_review pause) and
resume_analysis (continues with the administrator's decision), so that a user
interface can hold the paused graph while a human decides.
"""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from langgraph.types import Command

from astra.config import ASTRAConfig, DEFAULT_CONFIG
from astra.blockchain.backend import ChainBackend, TxRecord
from astra.network.peer_registry import PeerRegistry
from astra.network.mempool import MempoolLog, MempoolSighting
from astra.network.propagation import BlockPropagationLog
from astra.scenarios.generator import ScenarioGenerator, ScenarioCandidate
from astra.pre_admission.monitor_agent import MonitorAgent
from astra.pre_admission.types import TrustEvaluation, AdminAction, AdminDecisionRecord
from astra.admin.policies import AdminPolicy, AutoAdmin
from astra.orchestration.langgraph_flow import AdmissionContext, build_live_admission_graph


# What the attacker does in each attack (implemented in astra/scenarios/generator.py).
ATTACK_PLAYBOOK: Dict[str, Dict[str, Any]] = {
    "sybil": {
        "title": "Sybil Attack",
        "steps": [
            "One funder wallet creates the candidate plus 3 sibling identities.",
            "All 4 identities are funded with an identical 0.2 ETH within about a minute.",
            "The identities pass 0.01 ETH around in a closed ring to fake activity.",
            "The candidate then requests admission as if it were an independent node.",
        ],
    },
    "malicious_wallet": {
        "title": "Malicious Wallet (Spam / DoS) Attack",
        "steps": [
            "A fresh wallet is funded with 1.0 ETH.",
            "It fires 8 transactions less than 5 seconds apart (bot burst).",
            "Every transfer is a 0.0001 ETH dust payment to a small set of fresh addresses.",
            "Half of the transactions are sent so that they revert on-chain.",
        ],
    },
    "finney": {
        "title": "Finney Double-Spend Attack",
        "steps": [
            "The attacker mines a transfer of 0.4 ETH to its own stash wallet and keeps the block private.",
            "It pays a merchant the same 0.4 ETH using the SAME nonce (seen only in the mempool).",
            "The withheld block is then published, so the merchant payment can never confirm.",
        ],
    },
    "eclipse": {
        "title": "Eclipse Attack",
        "steps": [
            "The candidate's wallet history is ordinary (funded by an exchange).",
            "All 8 of its peer connections sit in one attacker-controlled ASN (AS99999_BOTNET).",
            "Those peers are freshly connected and report a chain tip 12 blocks behind.",
        ],
    },
}

DEFAULT_OUTPUT_DIR = os.path.join("results", "attack_runs")


@dataclass
class LaunchedAttack:
    """The attack as it exists on the ledger and in the network view, before any analysis."""
    attack_type: str
    title: str
    playbook_steps: List[str]
    candidate: ScenarioCandidate
    chain: ChainBackend
    peer_registry: PeerRegistry
    mempool_log: MempoolLog
    propagation_log: BlockPropagationLog
    known_exchanges: List[str]
    footprint: List[TxRecord]                 # on-chain transactions created by the attack
    mempool_sightings: List[MempoolSighting]  # unconfirmed transactions created by the attack
    started_at_utc: str

    def role_of(self, address: str) -> str:
        """Labels an address by its part in the attack."""
        addr = address.lower()
        if addr == self.candidate.wallet_address.lower():
            return "CANDIDATE"
        if addr in (a.lower() for a in self.candidate.related_cluster):
            return "cluster"
        if addr in (a.lower() for a in self.known_exchanges):
            return "exchange"
        return ""


@dataclass
class AttackRun:
    """A finished run: the attack, what the agents concluded, and the administrator's decision."""
    attack: LaunchedAttack
    node_trace: List[str]
    evaluation: TrustEvaluation
    decision: AdminDecisionRecord

    @property
    def admitted(self) -> bool:
        return self.decision.action == AdminAction.ACCEPT


def launch_attack(attack_type: str, chain: ChainBackend, seed: int = 42) -> LaunchedAttack:
    """Builds normal background traffic, then executes the attack on the chain backend."""
    a_type = attack_type.lower()
    peer_reg = PeerRegistry(seed=seed)
    mempool = MempoolLog()
    prop_log = BlockPropagationLog()
    gen = ScenarioGenerator(seed=seed)
    gen.populate_background(chain, peer_reg, mempool, prop_log)

    tip_before = chain.block_number()
    sightings_before = len(mempool.all_sightings())
    started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    candidate = gen.create_candidate(a_type, f"NODE_{a_type.upper()}", chain, peer_reg, mempool, prop_log)

    footprint = [
        tx for tx in chain.all_transactions()
        if tx.block_number is not None and tx.block_number > tip_before
    ]
    footprint.sort(key=lambda tx: (tx.block_number, tx.nonce))

    playbook = ATTACK_PLAYBOOK.get(a_type, {})
    return LaunchedAttack(
        attack_type=a_type,
        title=playbook.get("title", a_type.replace("_", " ").title()),
        playbook_steps=playbook.get("steps", []),
        candidate=candidate,
        chain=chain,
        peer_registry=peer_reg,
        mempool_log=mempool,
        propagation_log=prop_log,
        known_exchanges=list(gen.exchanges),
        footprint=footprint,
        mempool_sightings=mempool.all_sightings()[sightings_before:],
        started_at_utc=started,
    )


@dataclass
class AnalysisSession:
    """A LangGraph admission run paused at human_review, waiting for the administrator."""
    attack: LaunchedAttack
    ctx: AdmissionContext
    graph: Any
    thread: Dict[str, Any]
    node_trace: List[str]

    @property
    def evaluation(self) -> TrustEvaluation:
        return self.ctx.evaluation

    def _run_until_pause(self, graph_input: Any, on_node: Optional[Callable[[str, Dict[str, Any]], None]]) -> None:
        for chunk in self.graph.stream(graph_input, config=self.thread, stream_mode="updates"):
            for node_name, update in chunk.items():
                if node_name == "__interrupt__":
                    continue
                self.node_trace.append(node_name)
                if on_node:
                    on_node(node_name, update or {})


def start_analysis(
    attack: LaunchedAttack,
    config: ASTRAConfig = DEFAULT_CONFIG,
    on_node: Optional[Callable[[str, Dict[str, Any]], None]] = None
) -> AnalysisSession:
    """
    Phase A: builds the live admission graph for the attacked candidate and runs
    collect -> 4 agents -> aggregate. The graph then interrupts at human_review and the
    returned session holds the evaluation the administrator must decide on.
    """
    cand = attack.candidate
    ctx = AdmissionContext(
        candidate_id=cand.candidate_id,
        wallet_address=cand.wallet_address,
        chain=attack.chain,
        peer_profile=cand.peer_profile,
        peer_registry=attack.peer_registry,
        mempool_log=attack.mempool_log,
        propagation_log=attack.propagation_log,
        candidate_mined_blocks=cand.mined_blocks,
        known_exchanges=attack.known_exchanges,
    )
    session = AnalysisSession(
        attack=attack,
        ctx=ctx,
        graph=build_live_admission_graph(ctx, MonitorAgent(config)),
        thread={"configurable": {"thread_id": f"attack_{cand.candidate_id}_{attack.started_at_utc}"}},
        node_trace=[],
    )
    session._run_until_pause({"candidate_id": cand.candidate_id, "wallet_address": cand.wallet_address}, on_node)
    return session


def resume_analysis(
    session: AnalysisSession,
    decision: AdminDecisionRecord,
    on_node: Optional[Callable[[str, Dict[str, Any]], None]] = None
) -> AttackRun:
    """Phase B: resumes the paused graph with the administrator's decision and finishes the run."""
    session._run_until_pause(
        Command(resume={"action": decision.action.value, "reason": decision.reason}), on_node
    )
    return AttackRun(attack=session.attack, node_trace=session.node_trace,
                     evaluation=session.evaluation, decision=decision)


def analyse_with_agents(
    attack: LaunchedAttack,
    admin: Optional[AdminPolicy] = None,
    config: ASTRAConfig = DEFAULT_CONFIG,
    on_node: Optional[Callable[[str, Dict[str, Any]], None]] = None
) -> AttackRun:
    """
    Runs the LangGraph admission graph on the attacked candidate end to end.
    The graph stops at the human_review interrupt; the administrator policy supplies the
    decision and the graph is resumed with it.
    """
    admin = admin or AutoAdmin(use_escalation=True)
    session = start_analysis(attack, config=config, on_node=on_node)
    decision = admin.decide(session.evaluation)
    return resume_analysis(session, decision, on_node=on_node)


def attack_run_to_dict(run: AttackRun) -> Dict[str, Any]:
    """Flattens a run into plain JSON-serializable data."""
    atk, ev, cand = run.attack, run.evaluation, run.attack.candidate
    return {
        "run": {
            "attack_type": atk.attack_type,
            "title": atk.title,
            "started_at_utc": atk.started_at_utc,
            "backend": atk.chain.info(),
            "candidate_id": cand.candidate_id,
            "candidate_wallet": cand.wallet_address,
            "ground_truth_label": cand.label,
        },
        "attack": {
            "playbook_steps": atk.playbook_steps,
            "on_chain_transactions": [
                {
                    "block": tx.block_number,
                    "tx_hash": tx.tx_hash,
                    "from": tx.sender,
                    "from_role": atk.role_of(tx.sender),
                    "to": tx.to,
                    "to_role": atk.role_of(tx.to),
                    "value_eth": tx.value_eth,
                    "fee_eth": tx.fee_eth,
                    "nonce": tx.nonce,
                    "status": "SUCCESS" if tx.status == 1 else "REVERTED",
                    "timestamp": tx.timestamp,
                }
                for tx in atk.footprint
            ],
            "mempool_sightings": [asdict(s) for s in atk.mempool_sightings],
            "peer_table": [asdict(p) for p in cand.peer_profile.peers],
        },
        "agentic_analysis": {
            "orchestration": "LangGraph StateGraph (collect -> 4 agents -> aggregate -> human_review)",
            "node_trace": run.node_trace,
            "agents": {
                name: {
                    "risk": out.risk,
                    "critical": out.critical,
                    "summary": out.summary,
                    "evidence": out.evidence,
                    "indicators": [asdict(ind) for ind in out.indicators],
                }
                for name, out in ev.agent_outputs.items()
            },
            "positive_trust": {
                "I": ev.pt_score.i_score,
                "T": ev.pt_score.t_score,
                "N": ev.pt_score.n_score,
                "H": ev.pt_score.h_score,
                "B": ev.pt_score.b_score,
            },
            "AR": ev.ar,
            "PT": ev.pt,
            "TF": ev.tf,
            "TV": ev.tv,
            "recommendation": ev.recommendation.value,
            "escalation_flag": ev.escalation_flag,
            "escalation_reasons": ev.escalation_reasons,
        },
        "admin_decision": {
            "action": run.decision.action.value,
            "reason": run.decision.reason,
            "decided_by": run.decision.decided_by,
        },
        "outcome": {"candidate_admitted": run.admitted},
    }


def _short(value: str, keep: int = 10) -> str:
    return value if len(value) <= keep + 3 else value[:keep] + "..."


def _markdown_report(data: Dict[str, Any]) -> str:
    run, atk, ai, dec = data["run"], data["attack"], data["agentic_analysis"], data["admin_decision"]
    lines = [
        f"# ASTRA Attack Run: {run['title']}",
        "",
        f"- **Run started:** {run['started_at_utc']}",
        f"- **Blockchain backend:** {run['backend'].get('backend', 'unknown')}",
        f"- **Candidate:** {run['candidate_id']} (`{run['candidate_wallet']}`)",
        f"- **Ground truth:** {run['ground_truth_label']}",
        "",
        "## 1. Attack executed",
        "",
    ]
    lines += [f"{i}. {step}" for i, step in enumerate(atk["playbook_steps"], 1)]
    lines += [
        "",
        f"### On-chain transactions ({len(atk['on_chain_transactions'])})",
        "",
        "| Block | Tx hash | From | To | Value (ETH) | Nonce | Status |",
        "| ---: | :--- | :--- | :--- | ---: | ---: | :--- |",
    ]
    for tx in atk["on_chain_transactions"]:
        frm = _short(tx["from"]) + (f" ({tx['from_role']})" if tx["from_role"] else "")
        to = _short(tx["to"]) + (f" ({tx['to_role']})" if tx["to_role"] else "")
        lines.append(
            f"| {tx['block']} | `{_short(tx['tx_hash'], 14)}` | {frm} | {to} | "
            f"{tx['value_eth']:.4f} | {tx['nonce']} | {tx['status']} |"
        )
    if atk["mempool_sightings"]:
        lines += ["", "### Unconfirmed mempool transactions", ""]
        for s in atk["mempool_sightings"]:
            lines.append(
                f"- `{_short(s['tx_hash'], 14)}` from {_short(s['sender'])} to {_short(s['to'])}: "
                f"{s['value_eth']} ETH at nonce {s['nonce']} (mined: {s['is_mined']})"
            )
    lines += [
        "",
        f"### Peer table ({len(atk['peer_table'])} peers)",
        "",
        "| Peer | IP | ASN | Connection age (days) | Reported height | Backbone |",
        "| :--- | :--- | :--- | ---: | ---: | :--- |",
    ]
    for p in atk["peer_table"]:
        lines.append(
            f"| {p['node_id']} | {p['ip']} | {p['asn']} | {p['connection_age_days']:.1f} | "
            f"{p['reported_height']} | {p['is_backbone']} |"
        )
    lines += [
        "",
        "## 2. Agentic AI analysis",
        "",
        f"Orchestration: {ai['orchestration']}",
        "",
        f"Node execution order: {' -> '.join(ai['node_trace'])}",
        "",
    ]
    for name, out in ai["agents"].items():
        lines += [f"### {name} Agent - risk {out['risk']:.2f}" + (" (CRITICAL)" if out["critical"] else ""), ""]
        lines += [f"- {e}" for e in out["evidence"]]
        lines.append("")
    pt = ai["positive_trust"]
    lines += [
        "### Trust computation",
        "",
        f"- Attack Risk **AR = {ai['AR']:.3f}** (0.30*S + 0.20*W + 0.20*F + 0.30*E)",
        f"- Positive Trust **PT = {ai['PT']:.3f}** "
        f"(I={pt['I']:.2f}, T={pt['T']:.2f}, N={pt['N']:.2f}, H={pt['H']:.2f}, B={pt['B']:.2f})",
        f"- Trust Factor **TF = {ai['TF']:.3f}** against threshold TV = {ai['TV']:.2f}",
        f"- AI recommendation: **{ai['recommendation']}**",
        f"- Escalation flag: **{'TRIGGERED' if ai['escalation_flag'] else 'CLEAN'}**",
    ]
    lines += [f"  - {r}" for r in ai["escalation_reasons"]]
    lines += [
        "",
        "## 3. Administrator decision",
        "",
        f"- **Action:** {dec['action']}",
        f"- **Reason:** {dec['reason']}",
        f"- **Decided by:** {dec['decided_by']}",
        "",
        f"**Outcome:** candidate {'ADMITTED to' if data['outcome']['candidate_admitted'] else 'NOT ADMITTED to'} the network.",
        "",
    ]
    return "\n".join(lines)


def save_attack_run(run: AttackRun, output_dir: str = DEFAULT_OUTPUT_DIR) -> Tuple[str, str]:
    """Writes the run as <timestamp>_<attack>_<backend>.json and .md; returns both paths."""
    os.makedirs(output_dir, exist_ok=True)
    data = attack_run_to_dict(run)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backend = str(data["run"]["backend"].get("backend", "chain")).lower()
    base = os.path.join(output_dir, f"{stamp}_{run.attack.attack_type}_{backend}")

    json_path, md_path = base + ".json", base + ".md"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(_markdown_report(data))
    return json_path, md_path
