"""
CLI Entry Point for ASTRA: Autonomous Security and Threat Response using Agentic AI.
Supports commands: info, demo, admit, observe, monitor, eval.
Uses rich for polished console visualization.
"""

import sys
import argparse
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown

from astra.config import ASTRAConfig, DEFAULT_CONFIG
from astra.blockchain.backend import ChainBackend
from astra.blockchain.sim_chain import SimChain
from astra.blockchain.ganache_chain import GanacheChain
from astra.network.peer_registry import PeerRegistry
from astra.network.mempool import MempoolLog
from astra.network.propagation import BlockPropagationLog
from astra.scenarios.generator import ScenarioGenerator
from astra.pre_admission.monitor_agent import MonitorAgent
from astra.pre_admission.types import TrustEvaluation, AdminAction, Recommendation
from astra.admin.policies import AutoAdmin, InteractiveAdmin
from astra.observation.window import ObservationWindowManager
from astra.consensus_sim.simulator import ConsensusSimulator
from astra.consensus_sim.miner_strategies import MinerType
from astra.post_admission.continuous_monitor import ContinuousMonitor
from astra.evaluation.runner import EvaluationRunner
from astra.attack_lab import ATTACK_PLAYBOOK, DEFAULT_OUTPUT_DIR, launch_attack, analyse_with_agents, save_attack_run
from astra.evaluation.calibration import run_calibration, format_markdown as format_calibration_markdown
from astra.evaluation.ml_baseline import run_ml_baseline, format_markdown as format_ml_markdown

console = Console()


def get_backend(backend_name: str, config: ASTRAConfig) -> ChainBackend:
    if backend_name.lower() == "ganache":
        try:
            return GanacheChain(config.blockchain_rpc_url)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not connect to Ganache ({e}). Falling back to SimChain.[/yellow]")
            return SimChain(seed=42)
    return SimChain(seed=42)


def cmd_info(args, config: ASTRAConfig):
    console.print(Panel.fit(
        "[bold cyan]ASTRA: Autonomous Security & Threat Response using Agentic AI[/bold cyan]\n"
        "[dim]Two-Layer Multi-Agent Blockchain Node Admission Security & Continuous Monitoring[/dim]\n"
        "Researchers: Dhruv Basia & Amisha Rawat | Supervisor: Prof. Rahul Johari | USAR, GGSIPU",
        border_style="cyan"
    ))

    t = Table(title="ASTRA Mathematical Formulations & Configuration", border_style="dim")
    t.add_column("Parameter / Formula", style="bold")
    t.add_column("Specification", style="green")

    t.add_row("Attack Risk (AR)", f"0.30*S + 0.20*W + 0.20*F + 0.30*E")
    t.add_row("Positive Trust (PT)", f"0.25*I + 0.20*T + 0.20*N + 0.20*H + 0.15*B")
    t.add_row("Trust Factor (TF)", f"0.60*PT + 0.40*(1 - AR)")
    t.add_row("Decision Policy", f"TF >= TV ({config.threshold_tv}) -> Recommend ACCEPT, else REJECT")
    t.add_row("Escalation Flag", f"Triggered when any single agent risk >= {config.escalation_risk_threshold} or critical signature")
    t.add_row("Observation Window", f"First {config.observation_window_size} transactions (recompute H, B, TF per tx)")
    t.add_row("Blockchain RPC", config.blockchain_rpc_url)
    console.print(t)


def cmd_admit(args, config: ASTRAConfig):
    chain = get_backend(args.backend, config)
    peer_reg = PeerRegistry(seed=42)
    mempool = MempoolLog()
    prop_log = BlockPropagationLog()
    gen = ScenarioGenerator(seed=42)
    gen.populate_background(chain, peer_reg, mempool, prop_log)

    candidate = gen.create_candidate(args.type, f"CAND_{args.type.upper()}", chain, peer_reg, mempool, prop_log)
    monitor = MonitorAgent(config)

    eval_res: TrustEvaluation = monitor.evaluate_candidate(
        candidate_id=candidate.candidate_id,
        wallet_address=candidate.wallet_address,
        chain=chain,
        peer_profile=candidate.peer_profile,
        peer_registry=peer_reg,
        mempool_log=mempool,
        propagation_log=prop_log,
        candidate_mined_blocks=candidate.mined_blocks
    )

    admin = InteractiveAdmin() if args.interactive else AutoAdmin(use_escalation=True)
    decision = admin.decide(eval_res)

    _print_evaluation_table(eval_res, decision, candidate.candidate_type)


def cmd_observe(args, config: ASTRAConfig):
    console.print(Panel(f"[bold yellow]ASTRA Observation Window Simulation (Type: {args.type})[/bold yellow]"))
    chain = get_backend(args.backend, config)
    peer_reg = PeerRegistry(seed=42)
    mempool = MempoolLog()
    prop_log = BlockPropagationLog()
    gen = ScenarioGenerator(seed=42)
    gen.populate_background(chain, peer_reg, mempool, prop_log)

    cand = gen.create_candidate(args.type, "OBSERVE_TARGET_01", chain, peer_reg, mempool, prop_log)
    obs = ObservationWindowManager(config=config)
    window_size = args.window or config.observation_window_size
    session = obs.start_session(cand.candidate_id, cand.wallet_address, window_size=window_size)

    t = Table(title=f"Observation Session: {cand.candidate_id} ({args.type.upper()})", border_style="yellow")
    t.add_column("Tx #", justify="center")
    t.add_column("Value (ETH)", justify="right")
    t.add_column("AR", justify="center")
    t.add_column("PT", justify="center")
    t.add_column("TF", justify="center")
    t.add_column("Status / Alert", style="bold")
    t.add_column("Suggested Action")

    ally = cand.related_cluster[0] if cand.related_cluster else chain.create_account()

    # Transfer sizes are kept within the candidate's funded balance so that no
    # transaction reverts for lack of funds (a revert is itself an alert condition).
    for i in range(1, window_size + 1):
        chain.advance_time(30.0)
        # From tx 5, if sleeper, activate malicious cluster
        if args.type == "sleeper" and i >= 5:
            tx = chain.send(sender=cand.wallet_address, to=ally, value_eth=0.2)
            step_res = obs.process_transaction(
                session, tx, chain, cand.peer_profile, peer_reg, mempool,
                known_related_cluster=cand.related_cluster
            )
        else:
            other = chain.create_account()
            tx = chain.send(sender=cand.wallet_address, to=other, value_eth=0.1)
            step_res = obs.process_transaction(session, tx, chain, cand.peer_profile, peer_reg, mempool)

        alert_txt = f"[red]{step_res.alert_reasons[0]}[/red]" if step_res.alert_raised else "[green]Normal[/green]"
        t.add_row(
            str(step_res.tx_index),
            f"{tx.value_eth:.2f}",
            f"{step_res.ar:.2f}",
            f"{step_res.pt:.2f}",
            f"{step_res.tf:.2f}",
            alert_txt,
            step_res.suggested_action.value
        )

    console.print(t)
    status_msg = "[bold green]Clean Graduation[/bold green]" if session.is_graduated else "[bold red]Graduation Blocked - Alert Raised to Administrator[/bold red]"
    console.print(f"\nFinal Session Status: {status_msg}")


def cmd_monitor(args, config: ASTRAConfig):
    scenario_map = {
        "selfish": MinerType.SELFISH,
        "51percent": MinerType.COALITION_51,
        "coalition_51": MinerType.COALITION_51,
        "withholding": MinerType.BLOCK_WITHHOLDING,
        "block_withholding": MinerType.BLOCK_WITHHOLDING,
        "race": MinerType.RACE_DOUBLE_SPEND,
        "race_double_spend": MinerType.RACE_DOUBLE_SPEND,
        "honest": MinerType.HONEST
    }
    s_type = scenario_map.get(args.scenario.lower(), MinerType.SELFISH)

    console.print(Panel(f"[bold magenta]ASTRA Continuous Post-Admission Monitoring ({s_type.value})[/bold magenta]"))
    sim = ConsensusSimulator(seed=42)
    sim.setup_miners(s_type)
    monitor = ContinuousMonitor(window_blocks=25)
    monitor.set_attack_start(sim.current_time)

    t = Table(title="Mining Timeline & Continuous Agent Alerts", border_style="magenta")
    t.add_column("Block #", justify="center")
    t.add_column("Miner")
    t.add_column("Delay", justify="right")
    t.add_column("Orphan?", justify="center")
    t.add_column("Active Alerts Emitted", style="bold red")

    for step in range(args.blocks):
        blocks = sim.step()
        for b in blocks:
            pool_stats = {
                m.miner_id: {"shares_submitted": m.pool_shares_submitted, "blocks_found": m.full_blocks_found}
                for m in sim.miners.values()
            }
            alerts = monitor.process_new_block(
                new_block=b,
                main_chain=sim.main_chain,
                orphaned_blocks=sim.orphaned_blocks,
                reorg_history=sim.reorg_history,
                propagation_log=sim.propagation_log,
                mempool_log=sim.mempool_log,
                miner_pool_stats=pool_stats
            )
            alert_str = "; ".join(a.alert_id for a in alerts) if alerts else "-"
            prop_rec = sim.propagation_log.get(b.block_number)
            d_val = f"{prop_rec.delay:.2f}s" if prop_rec else "-"
            t.add_row(
                str(b.block_number),
                b.miner[:16] + "...",
                d_val,
                "YES" if b.is_orphan else "No",
                alert_str
            )

    console.print(t)
    console.print(f"\n[bold]Total Unique Alerts Intercepted:[/bold] {len(monitor.alerts)}")
    if monitor.detection_delay is not None:
        console.print(f"[bold]Detection Latency:[/bold] {monitor.detection_delay:.2f} seconds after attack inception.")


def cmd_attack(args, config: ASTRAConfig):
    attack_types = list(ATTACK_PLAYBOOK) if args.type == "all" else [args.type]
    summary = []

    for a_type in attack_types:
        chain = get_backend(args.backend, config)
        backend_name = chain.info().get("backend", args.backend)

        # ---------------- Stage 1: the attack happens on the blockchain ----------------
        console.print(Panel.fit(
            f"[bold red]STAGE 1 - ATTACK LAUNCHED: {ATTACK_PLAYBOOK.get(a_type, {}).get('title', a_type)}[/bold red]\n"
            f"[dim]Backend: {backend_name}[/dim]",
            border_style="red"
        ))
        attack = launch_attack(a_type, chain)
        for i, step in enumerate(attack.playbook_steps, 1):
            console.print(f"  {i}. {step}")

        t = Table(title=f"On-chain footprint of {attack.candidate.candidate_id}", border_style="red")
        t.add_column("Block", justify="right")
        t.add_column("Tx Hash")
        t.add_column("From")
        t.add_column("To")
        t.add_column("ETH", justify="right")
        t.add_column("Nonce", justify="right")
        t.add_column("Status")
        for tx in attack.footprint:
            frm_role, to_role = attack.role_of(tx.sender), attack.role_of(tx.to)
            t.add_row(
                str(tx.block_number),
                tx.tx_hash[:12] + "...",
                tx.sender[:10] + "..." + (f" [bold]{frm_role}[/bold]" if frm_role else ""),
                tx.to[:10] + "..." + (f" [bold]{to_role}[/bold]" if to_role else ""),
                f"{tx.value_eth:.4f}",
                str(tx.nonce),
                "[green]SUCCESS[/green]" if tx.status == 1 else "[red]REVERTED[/red]"
            )
        console.print(t)
        for s in attack.mempool_sightings:
            console.print(
                f"  Mempool (unconfirmed): {s.tx_hash[:12]}... {s.sender[:10]}... -> {s.to[:10]}... "
                f"{s.value_eth} ETH at nonce {s.nonce}"
            )
        profile = attack.candidate.peer_profile
        console.print(
            f"  Peer table: {profile.peer_count} peers across {len(set(profile.asns))} ASN(s): "
            f"{', '.join(sorted(set(profile.asns)))}"
        )

        # ---------------- Stage 2: the agents analyse it ----------------
        console.print(Panel.fit(
            "[bold cyan]STAGE 2 - AGENTIC AI ANALYSIS (LangGraph multi-agent graph)[/bold cyan]",
            border_style="cyan"
        ))

        def on_node(name: str, update: dict):
            if name == "collect":
                cd = update.get("chain_data", {})
                console.print(
                    f"  [cyan]collect[/cyan]        read {cd.get('transactions_scanned')} transactions "
                    f"up to block {cd.get('block_height')}"
                )
            elif name.endswith("_agent"):
                key = name.replace("_agent", "")
                risk = update.get(f"{key}_risk", 0.0)
                colour = "red" if risk >= config.escalation_risk_threshold else ("yellow" if risk >= 0.4 else "green")
                console.print(f"  [cyan]{name:<14}[/cyan] risk = [{colour}]{risk:.2f}[/{colour}]")
                for ev_line in update.get(f"{key}_evidence", []):
                    console.print(f"                   - {ev_line}")
            elif name == "aggregate":
                console.print(
                    f"  [cyan]aggregate[/cyan]      AR = {update['ar']:.2f} | PT = {update['pt']:.2f} | "
                    f"TF = {update['tf']:.2f} (TV = {update['tv']:.2f}) -> "
                    f"recommend [bold]{update['recommendation']}[/bold]"
                )
                for reason in update.get("escalation_reasons", []):
                    console.print(f"                   [yellow]escalation:[/yellow] {reason}")
                console.print("  [cyan]human_review[/cyan]   graph paused - waiting for the administrator")
            elif name == "human_review":
                console.print(
                    f"  [cyan]human_review[/cyan]   resumed with decision [bold]{update.get('admin_decision')}[/bold]"
                )

        admin = InteractiveAdmin() if args.interactive else AutoAdmin(use_escalation=True)
        run = analyse_with_agents(attack, admin=admin, config=config, on_node=on_node)

        # ---------------- Stage 3: decision and saved record ----------------
        json_path, md_path = save_attack_run(run, args.output)
        outcome = "[bold red]ADMITTED[/bold red]" if run.admitted else "[bold green]NOT ADMITTED[/bold green]"
        console.print(Panel.fit(
            f"[bold]STAGE 3 - DECISION: {run.decision.action.value}[/bold] ({run.decision.decided_by})\n"
            f"{run.decision.reason}\n"
            f"Candidate {outcome}\n\n"
            f"Saved: {json_path}\n"
            f"       {md_path}",
            border_style="green"
        ))
        summary.append((attack.title, run))

    if len(summary) > 1:
        st = Table(title="Attack Lab Summary", border_style="green")
        st.add_column("Attack", style="bold")
        for col in ("S", "W", "F", "E", "AR", "PT", "TF"):
            st.add_column(col, justify="center")
        st.add_column("Decision")
        for title, run in summary:
            ev = run.evaluation
            st.add_row(
                title,
                *(f"{ev.agent_outputs[n].risk:.2f}" for n in ("Sybil", "Wallet", "Finney", "Eclipse")),
                f"{ev.ar:.2f}", f"{ev.pt:.2f}", f"{ev.tf:.2f}",
                run.decision.action.value
            )
        console.print(st)


def cmd_eval(args, config: ASTRAConfig):
    console.print(Panel.fit(f"[bold green]Running Comprehensive Research Evaluation (n={args.n}, backend={args.backend})...[/bold green]"))
    runner = EvaluationRunner(config=config, seed=42)
    results = runner.generate_full_evaluation(backend_name=args.backend, n_candidates=args.n)

    pa = results["pre_admission"]
    f_met = pa["formula_only_metrics"]
    e_met = pa["formula_escalation_metrics"]

    t = Table(title="Evaluation Performance Summary", border_style="green")
    t.add_column("Metric", style="bold")
    t.add_column("Policy A: Formula Only (TF >= TV)", justify="center")
    t.add_column("Policy B: Formula + Escalation", justify="center")

    t.add_row("Total Evaluated", str(pa["total_evaluated"]), str(pa["total_evaluated"]))
    t.add_row("Accuracy", f"{f_met['accuracy']:.1%}", f"{e_met['accuracy']:.1%}")
    t.add_row("Precision", f"{f_met['precision']:.1%}", f"{e_met['precision']:.1%}")
    t.add_row("Recall (TPR)", f"{f_met['recall']:.1%}", f"{e_met['recall']:.1%}")
    t.add_row("False Positive Rate (FPR)", f"{f_met['fpr']:.1%}", f"{e_met['fpr']:.1%}")
    t.add_row("False Negative Rate (FNR)", f"{f_met['fnr']:.1%}", f"{e_met['fnr']:.1%}")
    console.print(t)

    console.print("\n[bold cyan]Reports Written Successfully:[/bold cyan]")
    console.print("  * JSON Results : [underline]results/eval_results.json[/underline]")
    console.print("  * Markdown Doc : [underline]results/eval_report.md[/underline]")


def cmd_calibrate(args, config: ASTRAConfig):
    console.print(Panel.fit(
        f"[bold green]Calibrating TV and the TF weights on seed {args.train_seed}, "
        f"testing on seeds {', '.join(map(str, args.test_seeds))} (n={args.n} each)...[/bold green]"
    ))
    result = run_calibration(train_seed=args.train_seed, test_seeds=tuple(args.test_seeds), n=args.n, config=config)
    console.print(Markdown(format_calibration_markdown(result)))
    console.print("\n[bold cyan]Written:[/bold cyan] results/calibration.json, results/calibration.md")


def cmd_ml(args, config: ASTRAConfig):
    console.print(Panel.fit(
        f"[bold green]Learned-classifier baseline: test seed {args.seed}, train seed {args.train_seed}, "
        f"n={args.n}, {args.folds}-fold CV...[/bold green]"
    ))
    result = run_ml_baseline(seed=args.seed, train_seed=args.train_seed, n=args.n, folds=args.folds, config=config)
    console.print(Markdown(format_ml_markdown(result)))
    console.print("\n[bold cyan]Written:[/bold cyan] results/ml_baseline.json, results/ml_baseline.md")


def cmd_demo(args, config: ASTRAConfig):
    console.print(Panel.fit(
        "[bold cyan]ASTRA: COMPLETE SYSTEM RESEARCH DEMONSTRATION[/bold cyan]\n"
        "[dim]Walking through Pre-Admission, Observation Window, and Post-Admission Surveillance[/dim]",
        border_style="cyan"
    ))

    chain = get_backend(args.backend, config)
    peer_reg = PeerRegistry(seed=42)
    mempool = MempoolLog()
    prop_log = BlockPropagationLog()
    gen = ScenarioGenerator(seed=42)
    gen.populate_background(chain, peer_reg, mempool, prop_log)
    monitor = MonitorAgent(config)
    admin = AutoAdmin(use_escalation=True)

    # 1. Honest Node Admission
    console.print("\n[bold underline]SCENARIO 1: Honest Candidate Requesting Admission[/bold underline]")
    c_honest = gen.create_candidate("honest", "NODE_HONEST_DEMO", chain, peer_reg, mempool, prop_log)
    res_h = monitor.evaluate_candidate(c_honest.candidate_id, c_honest.wallet_address, chain, c_honest.peer_profile, peer_reg, mempool, prop_log)
    dec_h = admin.decide(res_h)
    _print_evaluation_table(res_h, dec_h, "Honest Participant")

    # 2. Sybil Cluster Admission
    console.print("\n[bold underline]SCENARIO 2: Sybil Cluster Attack Requesting Admission[/bold underline]")
    c_sybil = gen.create_candidate("sybil", "NODE_SYBIL_DEMO", chain, peer_reg, mempool, prop_log)
    res_s = monitor.evaluate_candidate(c_sybil.candidate_id, c_sybil.wallet_address, chain, c_sybil.peer_profile, peer_reg, mempool, prop_log)
    dec_s = admin.decide(res_s)
    _print_evaluation_table(res_s, dec_s, "Sybil Pseudonym")

    # 3. Finney Attack Double-Spend
    console.print("\n[bold underline]SCENARIO 3: Finney Double-Spend & Block Withholding Attack[/bold underline]")
    c_finney = gen.create_candidate("finney", "NODE_FINNEY_DEMO", chain, peer_reg, mempool, prop_log)
    res_f = monitor.evaluate_candidate(c_finney.candidate_id, c_finney.wallet_address, chain, c_finney.peer_profile, peer_reg, mempool, prop_log, candidate_mined_blocks=c_finney.mined_blocks)
    dec_f = admin.decide(res_f)
    _print_evaluation_table(res_f, dec_f, "Finney Double-Spender")

    # 4. Eclipse Attack
    console.print("\n[bold underline]SCENARIO 4: Eclipse Routing Table Monopolization Attack[/bold underline]")
    c_ecl = gen.create_candidate("eclipse", "NODE_ECLIPSE_DEMO", chain, peer_reg, mempool, prop_log)
    res_e = monitor.evaluate_candidate(c_ecl.candidate_id, c_ecl.wallet_address, chain, c_ecl.peer_profile, peer_reg, mempool, prop_log)
    dec_e = admin.decide(res_e)
    _print_evaluation_table(res_e, dec_e, "Eclipsed Node")

    # 5. Observation Window on Sleeper Node
    console.print("\n[bold underline]LAYER 2: Observation Window on Sleeper Candidate[/bold underline]")
    obs = ObservationWindowManager(config=config)
    sleeper = gen.create_candidate("sleeper", "NODE_SLEEPER_DEMO", chain, peer_reg, mempool, prop_log)
    sess = obs.start_session(sleeper.candidate_id, sleeper.wallet_address, window_size=10)
    ally = sleeper.related_cluster[0] if sleeper.related_cluster else chain.create_account()

    for i in range(1, 8):
        chain.advance_time(30.0)
        if i >= 5:
            tx = chain.send(sender=sleeper.wallet_address, to=ally, value_eth=2.0)
            st = obs.process_transaction(sess, tx, chain, sleeper.peer_profile, peer_reg, mempool, known_related_cluster=sleeper.related_cluster)
        else:
            other = chain.create_account()
            tx = chain.send(sender=sleeper.wallet_address, to=other, value_eth=0.1)
            st = obs.process_transaction(sess, tx, chain, sleeper.peer_profile, peer_reg, mempool)

        if st.alert_raised:
            console.print(f"  [bold red]Transaction #{st.tx_index}: ALERT RAISED![/bold red] TF={st.tf:.2f} < TV ({st.tv:.2f}). Reason: {st.alert_reasons[0]}")
            console.print(f"  Administrator Action: [bold red]{st.suggested_action.value}[/bold red] (Sleeper node intercepted!)")
            break
        else:
            console.print(f"  Transaction #{st.tx_index}: Normal transfer. TF={st.tf:.2f} >= TV. Action: [green]CONTINUE[/green]")

    # 6. Post-Admission Continuous Monitoring
    console.print("\n[bold underline]LAYER 3: Post-Admission Surveillance (51% Hash Coalition)[/bold underline]")
    sim = ConsensusSimulator(seed=42)
    sim.setup_miners(MinerType.COALITION_51)
    cont_mon = ContinuousMonitor(window_blocks=20)
    cont_mon.set_attack_start(sim.current_time)

    for _ in range(12):
        b_list = sim.step()
        for b in b_list:
            alerts = cont_mon.process_new_block(
                new_block=b,
                main_chain=sim.main_chain,
                orphaned_blocks=sim.orphaned_blocks,
                reorg_history=sim.reorg_history,
                propagation_log=sim.propagation_log,
                mempool_log=sim.mempool_log
            )
            for a in alerts:
                console.print(f"  [bold magenta]ALERT: [{a.severity.value}] {a.agent_name}[/bold magenta] on Block #{a.block_number}: {a.evidence[0]}")

    console.print(Panel.fit("[bold green]ASTRA Research Demo Complete: Both Layers Fully Functional![/bold green]", border_style="green"))


def _print_evaluation_table(eval_res: TrustEvaluation, decision, c_type: str):
    t = Table(title=f"Evaluation: {eval_res.candidate_id} ({c_type})", border_style="dim")
    t.add_column("Agent / Component", style="bold")
    t.add_column("Score / Risk", justify="center")
    t.add_column("Key Observable Evidence")

    for name, out in eval_res.agent_outputs.items():
        ev_sample = out.evidence[0] if out.evidence else "Clean"
        t.add_row(f"{name} Agent", f"Risk: {out.risk:.2f}", ev_sample)

    t.add_row("Attack Risk (AR)", f"{eval_res.ar:.2f}", "Weighted sum: 0.30*S + 0.20*W + 0.20*F + 0.30*E")
    t.add_row("Positive Trust (PT)", f"{eval_res.pt:.2f}", "Weighted sum: 0.25*I + 0.20*T + 0.20*N + 0.20*H + 0.15*B")
    t.add_row("Trust Factor (TF)", f"{eval_res.tf:.2f}", f"Formula: 0.60*PT + 0.40*(1 - AR) [Threshold: {eval_res.tv:.2f}]")
    t.add_row("AI Recommendation", eval_res.recommendation.value, f"TF {'meets' if eval_res.is_recommended_accept else 'fails'} threshold")
    t.add_row("Escalation Flag", "TRIGGERED" if eval_res.escalation_flag else "CLEAN", "; ".join(eval_res.escalation_reasons) or "None")
    t.add_row("Admin Decision", decision.action.value, f"Human administrator confirmed: {decision.reason}")

    console.print(t)


def main():
    parser = argparse.ArgumentParser(description="ASTRA: Autonomous Security and Threat Response using Agentic AI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # info
    subparsers.add_parser("info", help="Display system architecture, formulas, and configuration")

    # dashboard
    subparsers.add_parser("dashboard", help="Launch the Streamlit research dashboard")

    # demo
    demo_p = subparsers.add_parser("demo", help="Run complete narrated walk through both layers")
    demo_p.add_argument("--backend", choices=["sim", "ganache"], default="sim", help="Blockchain backend")

    # admit
    admit_p = subparsers.add_parser("admit", help="Evaluate single candidate node pre-admission")
    admit_p.add_argument("--type", "--candidate", dest="type", default="sybil", help="Candidate profile type (honest, sybil, malicious_wallet, finney, eclipse)")
    admit_p.add_argument("--backend", choices=["sim", "ganache"], default="sim", help="Blockchain backend")
    admit_p.add_argument("--interactive", action="store_true", help="Prompt human administrator for decision")

    # observe
    obs_p = subparsers.add_parser("observe", help="Run 8-10 transaction observation window")
    obs_p.add_argument("--type", "--candidate", dest="type", default="sleeper", help="Candidate profile type (sleeper, honest)")
    obs_p.add_argument("--backend", choices=["sim", "ganache"], default="sim", help="Blockchain backend")
    obs_p.add_argument("--window", type=int, default=None, help="Observation window size in transactions (default: config value)")

    # monitor
    mon_p = subparsers.add_parser("monitor", help="Run post-admission continuous monitoring simulation")
    mon_p.add_argument(
        "--scenario",
        choices=["selfish", "51percent", "coalition_51", "withholding", "block_withholding", "race", "race_double_spend", "honest"],
        default="selfish"
    )
    mon_p.add_argument("--backend", choices=["sim", "ganache"], default="sim")
    mon_p.add_argument("--blocks", type=int, default=25, help="Number of mining rounds to simulate")

    # attack
    atk_p = subparsers.add_parser("attack", help="Launch an attack on the chain, analyse it with the agent graph, save the run")
    atk_p.add_argument("--type", default="sybil", help=f"Attack to launch ({', '.join(ATTACK_PLAYBOOK)}, all) or any candidate profile")
    atk_p.add_argument("--backend", choices=["sim", "ganache"], default="sim", help="Blockchain backend")
    atk_p.add_argument("--interactive", action="store_true", help="Prompt human administrator for decision")
    atk_p.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Directory for the saved JSON / Markdown run records")

    # calibrate
    cal_p = subparsers.add_parser("calibrate", help="Learn TV and the TF weights on one seed, test on unseen seeds")
    cal_p.add_argument("--train-seed", type=int, default=7)
    cal_p.add_argument("--test-seeds", type=int, nargs="+", default=[42, 1, 2, 3, 4])
    cal_p.add_argument("--n", type=int, default=120, help="Candidates per population")

    # ml
    ml_p = subparsers.add_parser("ml", help="Compare the TF rule with logistic regression, random forest and isolation forest")
    ml_p.add_argument("--seed", type=int, default=42, help="Test population seed")
    ml_p.add_argument("--train-seed", type=int, default=7, help="Cross-seed training population seed")
    ml_p.add_argument("--n", type=int, default=120)
    ml_p.add_argument("--folds", type=int, default=5)

    # eval
    eval_p = subparsers.add_parser("eval", help="Run full evaluation benchmark suite")
    eval_p.add_argument("--n", type=int, default=120, help="Number of candidate nodes to evaluate")
    eval_p.add_argument("--backend", choices=["sim", "ganache"], default="sim")

    args = parser.parse_args()
    cfg = DEFAULT_CONFIG

    if args.command == "info":
        cmd_info(args, cfg)
    elif args.command == "dashboard":
        import os
        import subprocess
        dash = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.py")
        sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", dash]))
    elif args.command == "demo":
        cmd_demo(args, cfg)
    elif args.command == "admit":
        cmd_admit(args, cfg)
    elif args.command == "observe":
        cmd_observe(args, cfg)
    elif args.command == "monitor":
        cmd_monitor(args, cfg)
    elif args.command == "attack":
        cmd_attack(args, cfg)
    elif args.command == "calibrate":
        cmd_calibrate(args, cfg)
    elif args.command == "ml":
        cmd_ml(args, cfg)
    elif args.command == "eval":
        cmd_eval(args, cfg)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
