"""
ASTRA Research Streamlit Dashboard.
Five tabs:
  1. Attack Lab          (launch an attack on the chain, watch the agent graph run,
                          decide as the administrator at the human_review pause, save the run)
  2. Pre-Admission       (risk bars, AR/PT/TF, evidence, human decision buttons)
  3. Observation Window  (TF trace against TV, step alerts, graduation status)
  4. Post-Admission      (hash share, propagation delays, alert timeline)
  5. Evaluation          (benchmark, per-profile breakdown, calibration, learned baseline)
"""

import glob
import json
import os

import pandas as pd
import streamlit as st

from astra.config import DEFAULT_CONFIG
from astra.blockchain.sim_chain import SimChain
from astra.blockchain.ganache_chain import GanacheChain
from astra.network.peer_registry import PeerRegistry
from astra.network.mempool import MempoolLog
from astra.network.propagation import BlockPropagationLog
from astra.scenarios.generator import ScenarioGenerator
from astra.pre_admission.monitor_agent import MonitorAgent
from astra.pre_admission.types import TrustEvaluation, AdminAction, AdminDecisionRecord
from astra.observation.window import ObservationWindowManager
from astra.consensus_sim.simulator import ConsensusSimulator
from astra.consensus_sim.miner_strategies import MinerType
from astra.post_admission.continuous_monitor import ContinuousMonitor
from astra.evaluation.runner import EvaluationRunner
from astra.evaluation.dataset import build_population
from astra.evaluation.calibration import run_calibration
from astra.evaluation.ml_baseline import run_ml_baseline, MODEL_LABELS
from astra.attack_lab import (
    ATTACK_PLAYBOOK, DEFAULT_OUTPUT_DIR, launch_attack, start_analysis, resume_analysis, save_attack_run,
)

st.set_page_config(page_title="ASTRA: Blockchain Security Research", page_icon="🛡️", layout="wide")
st.title("🛡️ ASTRA: Agentic AI Blockchain Security")
st.caption("Autonomous Security and Threat Response using Agentic AI for Blockchain | USAR, GGSIPU")

cfg = DEFAULT_CONFIG
RESULTS_DIR = "results"


def make_chain(backend_choice: str):
    """SimChain, or Ganache with a visible fallback when the RPC is down."""
    if "Ganache" in backend_choice:
        try:
            return GanacheChain(cfg.blockchain_rpc_url)
        except Exception as e:
            st.warning(f"Could not connect to Ganache ({e}). Falling back to SimChain.")
    return SimChain(seed=42)


def risk_colour(risk: float) -> str:
    if risk >= cfg.escalation_risk_threshold:
        return "red"
    return "orange" if risk >= 0.40 else "green"


def load_json(name: str):
    path = os.path.join(RESULTS_DIR, name)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def metrics_table(rows: dict) -> pd.DataFrame:
    """rows: label -> metrics dict from classification_metrics / runner."""
    return pd.DataFrame([
        {
            "Decision rule": label,
            "Accuracy": f"{m['accuracy']:.1%}",
            "Precision": f"{m['precision']:.1%}",
            "Recall": f"{m['recall']:.1%}",
            "FPR": f"{m['fpr']:.1%}",
            "TP/FP/TN/FN": "{TP}/{FP}/{TN}/{FN}".format(**m["confusion_matrix"]),
        }
        for label, m in rows.items()
    ])


# ------------------------------------------------------------------------------
# Agent-graph drawing (Graphviz DOT rendered by Streamlit in the browser)
# ------------------------------------------------------------------------------
GRAPH_NODES = ["collect", "sybil_agent", "wallet_agent", "finney_agent", "eclipse_agent", "aggregate", "human_review"]
NODE_TITLES = {
    "collect": "Collect evidence", "sybil_agent": "Sybil Agent", "wallet_agent": "Wallet Agent",
    "finney_agent": "Finney Agent", "eclipse_agent": "Eclipse Agent", "aggregate": "Aggregate\\nAR / PT / TF",
    "human_review": "Human review",
}
STATE_STYLE = {
    "pending": ("#e8e8e8", "#777777"),
    "done": ("#c8f0c8", "#1f7a1f"),
    "waiting": ("#ffe08a", "#9a6b00"),
    "decided": ("#bfe0ff", "#0b4f8a"),
}


def graph_dot(states: dict, details: dict) -> str:
    lines = [
        "digraph ASTRA {", "rankdir=LR; bgcolor=transparent; nodesep=0.35; ranksep=0.6;",
        'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, penwidth=2];',
        'edge [color="#888888", penwidth=1.5];',
        'START [shape=circle, label="", width=0.25, style=filled, fillcolor="#444444"];',
        'END [shape=doublecircle, label="", width=0.25, style=filled, fillcolor="#444444"];',
    ]
    for n in GRAPH_NODES:
        fill, border = STATE_STYLE[states.get(n, "pending")]
        label = NODE_TITLES[n] + (f"\\n{details[n]}" if details.get(n) else "")
        lines.append(f'{n} [label="{label}", fillcolor="{fill}", color="{border}"];')
    lines += ["START -> collect;"]
    for a in ("sybil_agent", "wallet_agent", "finney_agent", "eclipse_agent"):
        lines += [f"collect -> {a};", f"{a} -> aggregate;"]
    lines += ["aggregate -> human_review;", "human_review -> END;", "}"]
    return "\n".join(lines)


def render_evaluation(eval_res: TrustEvaluation):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Attack Risk (AR)", f"{eval_res.ar:.2f}", help="0.30*S + 0.20*W + 0.20*F + 0.30*E")
    m2.metric("Positive Trust (PT)", f"{eval_res.pt:.2f}", help="0.25*I + 0.20*T + 0.20*N + 0.20*H + 0.15*B")
    m3.metric("Trust Factor (TF)", f"{eval_res.tf:.2f}", f"Threshold TV = {eval_res.tv:.2f}", delta_color="off")
    colour = "green" if eval_res.is_recommended_accept else "red"
    m4.markdown(f"**AI Recommendation**\n### :{colour}[{eval_res.recommendation.value}]")
    if eval_res.escalation_flag:
        st.warning("⚠️ **Escalation flag:** " + "; ".join(eval_res.escalation_reasons))

    cols = st.columns(4)
    for col, (name, out) in zip(cols, eval_res.agent_outputs.items()):
        with col:
            st.markdown(f"**{name} Agent** — :{risk_colour(out.risk)}[risk {out.risk:.2f}]" + (" 🔴 critical" if out.critical else ""))
            st.progress(min(1.0, out.risk))
            with st.expander("Evidence"):
                for e in out.evidence:
                    st.write(f"- {e}")
                st.caption("Indicators")
                st.dataframe(pd.DataFrame([
                    {"Indicator": i.name, "Observed": str(i.raw_value), "Score": round(i.score, 2), "Weight": i.weight}
                    for i in out.indicators
                ]), hide_index=True, width="stretch")
    ps = eval_res.pt_score
    st.caption(
        f"Positive Trust components: I={ps.i_score:.2f}, T={ps.t_score:.2f}, N={ps.n_score:.2f}, "
        f"H={ps.h_score:.2f}, B={ps.b_score:.2f}"
    )


tab_lab, tab_pre, tab_obs, tab_post, tab_eval = st.tabs([
    "⚔️ Attack Lab", "🚪 Pre-Admission Layer", "👁️ Observation Window",
    "📡 Post-Admission Monitoring", "📊 Research Evaluation",
])

# ==============================================================================
# TAB 1: ATTACK LAB
# ==============================================================================
with tab_lab:
    st.subheader("Attack → Agentic Analysis → Human Decision → Saved Record")
    st.write(
        "Launch a real attack against the chain, watch the LangGraph multi-agent graph analyse it node by node, "
        "then decide as the administrator while the graph is paused at `human_review`."
    )

    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        attack_type = st.selectbox(
            "Attack to launch", list(ATTACK_PLAYBOOK),
            format_func=lambda k: ATTACK_PLAYBOOK[k]["title"], key="lab_attack_type"
        )
    with c2:
        lab_backend = st.radio("Blockchain backend", ["SimChain (In-Memory)", "Ganache (Port 7545)"],
                               horizontal=True, key="lab_backend")
    with c3:
        st.write("")
        launch = st.button("⚔️ Launch attack & run agents", type="primary", width="stretch")

    with st.expander("Attack playbook", expanded=False):
        for i, step in enumerate(ATTACK_PLAYBOOK[attack_type]["steps"], 1):
            st.write(f"{i}. {step}")

    if launch:
        for key in ("lab_session", "lab_run", "lab_saved", "lab_log", "lab_states", "lab_details"):
            st.session_state.pop(key, None)

        with st.status("Stage 1 — executing the attack on the blockchain", expanded=True) as s1:
            chain = make_chain(lab_backend)
            attack = launch_attack(attack_type, chain)
            st.write(f"Backend: **{chain.info().get('backend')}** · candidate `{attack.candidate.candidate_id}` "
                     f"(`{attack.candidate.wallet_address}`)")
            s1.update(label=f"Stage 1 — {attack.title} executed: {len(attack.footprint)} on-chain transactions", state="complete")

        st.session_state["lab_attack"] = attack
        states = {n: "pending" for n in GRAPH_NODES}
        details = {}
        log_lines = []
        st.session_state["lab_states"], st.session_state["lab_details"], st.session_state["lab_log"] = states, details, log_lines

        st.markdown("#### Stage 2 — agentic analysis (LangGraph)")
        graph_box = st.empty()
        log_box = st.empty()
        graph_box.graphviz_chart(graph_dot(states, details))

        def on_node(name: str, update: dict):
            states[name] = "done"
            if name == "collect":
                cd = update.get("chain_data", {})
                details[name] = f"{cd.get('transactions_scanned')} txs, tip {cd.get('block_height')}"
                log_lines.append(f"`collect` read {cd.get('transactions_scanned')} transactions up to block {cd.get('block_height')}")
            elif name.endswith("_agent"):
                key = name.replace("_agent", "")
                risk = update.get(f"{key}_risk", 0.0)
                details[name] = f"risk {risk:.2f}"
                log_lines.append(f"`{name}` → risk **{risk:.2f}**: " + " · ".join(update.get(f"{key}_evidence", [])[:2]))
            elif name == "aggregate":
                details[name] = f"TF {update['tf']:.2f} vs TV {update['tv']:.2f}"
                states["human_review"] = "waiting"
                details["human_review"] = "paused — waiting"
                log_lines.append(
                    f"`aggregate` → AR {update['ar']:.2f} · PT {update['pt']:.2f} · TF {update['tf']:.2f} "
                    f"→ recommend **{update['recommendation']}**"
                )
                log_lines.append("`human_review` → graph interrupted; waiting for the administrator")
            graph_box.graphviz_chart(graph_dot(states, details))
            log_box.markdown("\n".join(f"- {l}" for l in log_lines))

        session = start_analysis(attack, config=cfg, on_node=on_node)
        st.session_state["lab_session"] = session
        st.rerun()

    # ---- Paused at human_review: show evidence and ask the administrator ----
    if "lab_session" in st.session_state and "lab_run" not in st.session_state:
        session = st.session_state["lab_session"]
        attack = session.attack
        st.markdown(f"#### Stage 1 — {attack.title} on {attack.chain.info().get('backend')}")
        st.dataframe(pd.DataFrame([
            {
                "Block": tx.block_number, "Tx hash": tx.tx_hash[:14] + "…",
                "From": tx.sender[:10] + "…" + (f" ({attack.role_of(tx.sender)})" if attack.role_of(tx.sender) else ""),
                "To": tx.to[:10] + "…" + (f" ({attack.role_of(tx.to)})" if attack.role_of(tx.to) else ""),
                "ETH": tx.value_eth, "Nonce": tx.nonce, "Status": "SUCCESS" if tx.status == 1 else "REVERTED",
            }
            for tx in attack.footprint
        ]), hide_index=True, width="stretch")
        for s in attack.mempool_sightings:
            st.info(f"Mempool (unconfirmed): `{s.tx_hash[:14]}…` {s.sender[:10]}… → {s.to[:10]}… {s.value_eth} ETH at nonce {s.nonce}")
        prof = attack.candidate.peer_profile
        st.caption(f"Peer table: {prof.peer_count} peers across {len(set(prof.asns))} ASN(s): {', '.join(sorted(set(prof.asns)))}")

        st.markdown("#### Stage 2 — agentic analysis (LangGraph)")
        st.graphviz_chart(graph_dot(st.session_state["lab_states"], st.session_state["lab_details"]))
        st.markdown("\n".join(f"- {l}" for l in st.session_state["lab_log"]))
        st.divider()
        render_evaluation(session.evaluation)

        st.divider()
        st.markdown("#### Stage 3 — your decision (the graph is paused at `human_review`)")
        d1, d2, d3 = st.columns(3)
        chosen = None
        if d1.button("✅ Accept into consensus", width="stretch"):
            chosen = (AdminAction.ACCEPT, "Administrator accepted the candidate after reviewing the evidence.")
        if d2.button("🚫 Reject (block admission)", type="primary", width="stretch"):
            chosen = (AdminAction.REJECT, "Administrator rejected the candidate on the agents' evidence.")
        if d3.button("🔍 Send for investigation", width="stretch"):
            chosen = (AdminAction.INVESTIGATE, "Administrator routed the candidate for forensic investigation.")
        if chosen:
            action, reason = chosen
            decision = AdminDecisionRecord(
                candidate_id=attack.candidate.candidate_id, action=action, reason=reason,
                decided_by="DashboardAdministrator", timestamp=session.evaluation.timestamp,
                evidence_reviewed=session.evaluation.escalation_reasons,
            )
            run = resume_analysis(session, decision)
            st.session_state["lab_run"] = run
            st.session_state["lab_saved"] = save_attack_run(run, DEFAULT_OUTPUT_DIR)
            st.session_state["lab_states"]["human_review"] = "decided"
            st.session_state["lab_details"]["human_review"] = action.value
            st.rerun()

    # ---- Finished run ----
    if "lab_run" in st.session_state:
        run = st.session_state["lab_run"]
        json_path, md_path = st.session_state["lab_saved"]
        st.markdown(f"#### {run.attack.title} — run complete")
        st.graphviz_chart(graph_dot(st.session_state["lab_states"], st.session_state["lab_details"]))
        render_evaluation(run.evaluation)
        if run.admitted:
            st.error(f"Decision **{run.decision.action.value}** — the attacker was ADMITTED. {run.decision.reason}")
        else:
            st.success(f"Decision **{run.decision.action.value}** — candidate NOT admitted. {run.decision.reason}")
        st.caption(f"Node execution order: {' → '.join(run.node_trace)}")
        with open(md_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        with open(json_path, "r", encoding="utf-8") as f:
            json_text = f.read()
        b1, b2, b3 = st.columns(3)
        b1.download_button("⬇️ Download report (.md)", md_text, file_name=os.path.basename(md_path), width="stretch")
        b2.download_button("⬇️ Download record (.json)", json_text, file_name=os.path.basename(json_path), width="stretch")
        if b3.button("🔁 New attack", width="stretch"):
            for key in ("lab_session", "lab_run", "lab_saved", "lab_log", "lab_states", "lab_details", "lab_attack"):
                st.session_state.pop(key, None)
            st.rerun()
        with st.expander("Saved report"):
            st.markdown(md_text)

    st.divider()
    with st.expander(f"📁 Saved attack runs in `{DEFAULT_OUTPUT_DIR}/`"):
        saved = sorted(glob.glob(os.path.join(DEFAULT_OUTPUT_DIR, "*.json")), reverse=True)
        if not saved:
            st.write("No saved runs yet.")
        else:
            rows = []
            for p in saved:
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        d = json.load(f)
                    rows.append({
                        "File": os.path.basename(p), "Attack": d["run"]["title"],
                        "Backend": d["run"]["backend"].get("backend", "?"),
                        "TF": d["agentic_analysis"]["TF"], "Recommendation": d["agentic_analysis"]["recommendation"],
                        "Decision": d["admin_decision"]["action"], "By": d["admin_decision"]["decided_by"],
                    })
                except Exception:
                    continue
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            pick = st.selectbox("Open a saved report", [os.path.basename(p) for p in saved])
            md_file = os.path.join(DEFAULT_OUTPUT_DIR, pick.replace(".json", ".md"))
            if os.path.isfile(md_file):
                with open(md_file, "r", encoding="utf-8") as f:
                    st.markdown(f.read())

# ==============================================================================
# TAB 2: PRE-ADMISSION LAYER
# ==============================================================================
with tab_pre:
    st.subheader("Gateway Pre-Admission Screening")
    st.write("Candidate nodes are evaluated before admission by four specialized agents. "
             "The system recommends; the **human administrator holds final authority**.")

    col_ctrl1, col_ctrl2 = st.columns([2, 1])
    with col_ctrl1:
        cand_type = st.selectbox("Candidate profile", [
            "honest", "honest_power_user", "honest_single_cloud", "honest_fee_bumper",
            "sybil", "stealthy_sybil", "malicious_wallet", "finney", "eclipse", "partial_eclipse", "sleeper",
        ])
    with col_ctrl2:
        backend_choice = st.radio("Blockchain backend", ["SimChain (In-Memory)", "Ganache (Port 7545)"], horizontal=True)

    if st.button("🚀 Evaluate candidate", type="primary"):
        with st.spinner("Collecting blockchain evidence and dispatching specialized agents..."):
            chain = make_chain(backend_choice)
            peer_reg, mempool, prop_log = PeerRegistry(seed=42), MempoolLog(), BlockPropagationLog()
            gen = ScenarioGenerator(seed=42)
            gen.populate_background(chain, peer_reg, mempool, prop_log)
            candidate = gen.create_candidate(cand_type, f"CAND_{cand_type.upper()}", chain, peer_reg, mempool, prop_log)
            st.session_state["latest_eval"] = MonitorAgent(cfg).evaluate_candidate(
                candidate_id=candidate.candidate_id, wallet_address=candidate.wallet_address, chain=chain,
                peer_profile=candidate.peer_profile, peer_registry=peer_reg, mempool_log=mempool,
                propagation_log=prop_log, candidate_mined_blocks=candidate.mined_blocks,
                known_exchanges=gen.exchanges,
            )
            st.session_state["candidate_type"] = cand_type

    if "latest_eval" in st.session_state:
        st.divider()
        render_evaluation(st.session_state["latest_eval"])
        st.divider()
        st.subheader("Human-in-the-Loop Administrator Decision")
        h1, h2, h3 = st.columns(3)
        cid = st.session_state["latest_eval"].candidate_id
        if h1.button("✅ Accept candidate into consensus", width="stretch"):
            st.success(f"Candidate {cid} ACCEPTED by administrator.")
        if h2.button("🚫 Reject candidate (block pre-admission)", type="primary", width="stretch"):
            st.error(f"Candidate {cid} REJECTED by administrator.")
        if h3.button("🔍 Route for forensic investigation", width="stretch"):
            st.info(f"Candidate {cid} routed for investigation.")

# ==============================================================================
# TAB 3: OBSERVATION WINDOW
# ==============================================================================
with tab_obs:
    st.subheader("Sliding Observation Window (First 8–10 Transactions)")
    st.write("Admitted nodes stay under high-frequency surveillance during probation. "
             "Historical trust (H) and behavioural consistency (B) are recomputed per transaction.")

    o1, o2 = st.columns(2)
    with o1:
        obs_cand_type = st.selectbox("Candidate profile for probation", ["sleeper", "honest"])
    with o2:
        obs_window_len = st.slider("Observation window size (transactions)", min_value=8, max_value=12, value=10)

    if st.button("▶️ Run observation window"):
        chain = SimChain(seed=42)
        peer_reg, mempool, prop_log = PeerRegistry(seed=42), MempoolLog(), BlockPropagationLog()
        gen = ScenarioGenerator(seed=42)
        gen.populate_background(chain, peer_reg, mempool, prop_log)
        cand = gen.create_candidate(obs_cand_type, "OBS_TEST_NODE", chain, peer_reg, mempool, prop_log)
        obs_mgr = ObservationWindowManager(config=cfg)
        session = obs_mgr.start_session(cand.candidate_id, cand.wallet_address, window_size=obs_window_len)
        ally = cand.related_cluster[0] if cand.related_cluster else chain.create_account()

        history = []
        for step in range(1, obs_window_len + 1):
            chain.advance_time(30.0)
            if obs_cand_type == "sleeper" and step >= 5:
                tx = chain.send(sender=cand.wallet_address, to=ally, value_eth=0.2)
                res = obs_mgr.process_transaction(session, tx, chain, cand.peer_profile, peer_reg, mempool,
                                                  known_related_cluster=cand.related_cluster)
            else:
                tx = chain.send(sender=cand.wallet_address, to=chain.create_account(), value_eth=0.1)
                res = obs_mgr.process_transaction(session, tx, chain, cand.peer_profile, peer_reg, mempool)
            history.append({
                "Tx Index": res.tx_index, "TF": res.tf, "Threshold TV": res.tv, "AR": res.ar, "PT": res.pt,
                "H (History)": res.h_score, "B (Behavior)": res.b_score,
                "Alert": "ALERT" if res.alert_raised else "CLEAN", "Action": res.suggested_action.value,
                "Reason": res.alert_reasons[0] if res.alert_reasons else "",
            })
        df_obs = pd.DataFrame(history)
        st.line_chart(df_obs.set_index("Tx Index")[["TF", "Threshold TV"]])
        st.dataframe(df_obs, hide_index=True, width="stretch")
        if session.is_graduated:
            st.success("🎉 Candidate completed the window cleanly and GRADUATED to regular consensus.")
        else:
            st.error("🚨 ALERT: candidate exhibited a malicious shift. Graduation blocked; administrator notified.")

# ==============================================================================
# TAB 4: POST-ADMISSION CONTINUOUS MONITORING
# ==============================================================================
with tab_post:
    st.subheader("Network-Wide Consensus & Mining Surveillance")
    st.write("Four continuous agents monitor blocks on a sliding window: 51% dominance, double-spending, "
             "selfish mining and block withholding.")
    scenario_selected = st.radio(
        "Active miner scenario",
        ["Honest Baseline", "Selfish Mining", "51% Hash Coalition", "Block Withholding", "Race Double-Spend"],
        horizontal=True,
    )
    scenario_enum_map = {
        "Honest Baseline": MinerType.HONEST, "Selfish Mining": MinerType.SELFISH,
        "51% Hash Coalition": MinerType.COALITION_51, "Block Withholding": MinerType.BLOCK_WITHHOLDING,
        "Race Double-Spend": MinerType.RACE_DOUBLE_SPEND,
    }
    if st.button("⚡ Simulate consensus & run continuous agents"):
        sim = ConsensusSimulator(seed=42)
        sim.setup_miners(scenario_enum_map[scenario_selected])
        cont_mon = ContinuousMonitor(window_blocks=25)
        cont_mon.set_attack_start(sim.current_time)
        timeline = []
        with st.spinner("Mining blocks and running continuous multi-agent surveillance..."):
            for _ in range(30):
                for b in sim.step():
                    pool_stats = {
                        m.miner_id: {"shares_submitted": m.pool_shares_submitted, "blocks_found": m.full_blocks_found}
                        for m in sim.miners.values()
                    }
                    alerts = cont_mon.process_new_block(
                        new_block=b, main_chain=sim.main_chain, orphaned_blocks=sim.orphaned_blocks,
                        reorg_history=sim.reorg_history, propagation_log=sim.propagation_log,
                        mempool_log=sim.mempool_log, miner_pool_stats=pool_stats,
                    )
                    rec = sim.propagation_log.get(b.block_number)
                    timeline.append({
                        "Block": b.block_number, "Miner": b.miner[:18], "Delay (s)": round(rec.delay, 2) if rec else None,
                        "Orphan": b.is_orphan, "Alerts": "; ".join(a.alert_id for a in alerts),
                    })
        p1, p2, p3 = st.columns(3)
        p1.metric("Blocks mined", len(sim.main_chain))
        p2.metric("Orphaned blocks", len(sim.orphaned_blocks))
        p3.metric("Alerts intercepted", len(cont_mon.alerts))
        if cont_mon.detection_delay is not None:
            st.caption(f"Detection latency: {cont_mon.detection_delay:.1f}s after attack inception")
        st.dataframe(pd.DataFrame(timeline), hide_index=True, width="stretch")
        st.subheader("Emitted security alerts")
        if cont_mon.alerts:
            for a in cont_mon.alerts:
                with st.expander(f"[{a.severity.value}] {a.agent_name} — suspect {a.suspect[:16]}… (block #{a.block_number})"):
                    st.write(f"**Risk score:** {a.risk:.2f}")
                    for ev in a.evidence:
                        st.write(f"- {ev}")
        else:
            st.success("No security alerts triggered. Consensus operation is healthy.")

# ==============================================================================
# TAB 5: RESEARCH EVALUATION
# ==============================================================================
with tab_eval:
    st.subheader("Research Evaluation Benchmark")
    st.caption("Synthetic simulation results on the standard 120-candidate population (57 honest, 63 attacking).")

    e1, e2, e3 = st.columns(3)
    run_bench = e1.button("📊 Run 120-candidate benchmark", width="stretch")
    run_calib = e2.button("🎯 Calibrate TV / weights (seed 7 → unseen seeds)", width="stretch")
    run_mlb = e3.button("🤖 Run learned-classifier baseline", width="stretch")

    if run_bench:
        with st.spinner("Running the 120-candidate benchmark..."):
            st.session_state["benchmark_data"] = EvaluationRunner(config=cfg, seed=42).generate_full_evaluation(n_candidates=120)
            st.session_state["population"] = build_population(seed=42, n=120, config=cfg)
    if run_calib:
        with st.spinner("Searching TV and w_PT on seed 7, scoring on seeds 42, 1, 2, 3, 4 (about a minute)..."):
            run_calibration(train_seed=7, test_seeds=(42, 1, 2, 3, 4), n=120, config=cfg)
    if run_mlb:
        with st.spinner("Training logistic regression, random forest and isolation forest..."):
            run_ml_baseline(seed=42, train_seed=7, n=120, config=cfg)

    bench = st.session_state.get("benchmark_data") or load_json("eval_results.json")
    if bench:
        pa = bench["pre_admission"]
        st.markdown("#### Hand-written decision rule")
        st.dataframe(metrics_table({
            "Policy A — formula alone (TF ≥ TV)": pa["formula_only_metrics"],
            "Policy B — formula + escalation flag": pa["formula_escalation_metrics"],
        }), hide_index=True, width="stretch")
        atk_rows = [
            {"Attack": atk, "Detected (B)": s["detected"], "Total": s["total"],
             "Rate": f"{s['detected'] / s['total']:.0%}" if s["total"] else "-"}
            for atk, s in pa["per_attack_escalation"].items()
        ]
        st.dataframe(pd.DataFrame(atk_rows), hide_index=True, width="stretch")

    if "population" in st.session_state:
        st.markdown("#### Per-profile breakdown (seed 42)")
        pop = st.session_state["population"]
        by_type = {}
        for r in pop:
            by_type.setdefault(r.candidate_type, []).append(r)
        rows = []
        for t, rs in by_type.items():
            n = len(rs)
            rows.append({
                "Profile": t, "Truth": rs[0].label, "n": n,
                "Mean TF": round(sum(r.tf for r in rs) / n, 3),
                "S": round(sum(r.risks["Sybil"] for r in rs) / n, 2), "W": round(sum(r.risks["Wallet"] for r in rs) / n, 2),
                "F": round(sum(r.risks["Finney"] for r in rs) / n, 2), "E": round(sum(r.risks["Eclipse"] for r in rs) / n, 2),
                "A: accept/reject": f"{sum(r.action_formula == AdminAction.ACCEPT for r in rs)} / {sum(r.action_formula == AdminAction.REJECT for r in rs)}",
                "B: accept/investigate/reject": f"{sum(r.action_escalation == AdminAction.ACCEPT for r in rs)} / "
                                                 f"{sum(r.action_escalation == AdminAction.INVESTIGATE for r in rs)} / "
                                                 f"{sum(r.action_escalation == AdminAction.REJECT for r in rs)}",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        chart = pd.DataFrame({"TF": [r.tf for r in pop], "Profile": [r.candidate_type for r in pop]})
        st.scatter_chart(chart.reset_index(), x="index", y="TF", color="Profile", height=300)

    calib = load_json("calibration.json")
    if calib:
        st.markdown("#### Calibrated decision rule")
        rule, default = calib["calibrated_rule"], calib["default_rule"]
        r1, r2 = st.columns(2)
        r1.metric("Default rule", f"TV {default['tv']:.2f} · w_PT {default['w_pt']:.2f} · w_AR {default['w_ar']:.2f}")
        r2.metric("Calibrated rule", f"TV {rule['tv']:.3f} · w_PT {rule['w_pt']:.2f} · w_AR {rule['w_ar']:.2f}",
                  help=f"Fitted on seed {calib['protocol']['train_seed']}; margin {rule['train_margin']:.3f}")
        names = {
            "formula_default": "Formula alone, default rule", "escalation_default": "Formula + escalation, default rule",
            "formula_calibrated": "Formula alone, calibrated rule", "escalation_calibrated": "Formula + escalation, calibrated rule",
        }
        mean = calib["mean_over_test_seeds"]
        st.dataframe(pd.DataFrame([
            {"Decision rule": label, "Accuracy": f"{mean[k]['accuracy']:.1%}", "Balanced acc.": f"{mean[k]['balanced_accuracy']:.1%}",
             "Precision": f"{mean[k]['precision']:.1%}", "Recall": f"{mean[k]['recall']:.1%}", "FPR": f"{mean[k]['fpr']:.1%}"}
            for k, label in names.items()
        ]), hide_index=True, width="stretch")
        st.caption(f"Mean over unseen seeds {', '.join(map(str, calib['protocol']['test_seeds']))}.")

    mlb = load_json("ml_baseline.json")
    if mlb:
        st.markdown("#### Learned classifiers vs the hand-written rule")
        p = mlb["protocol"]
        st.caption(f"Test seed {p['test_seed']}; cross-seed training seed {p['train_seed']}; {p['cv_folds']}-fold CV.")
        rows = {
            "Formula alone (hand rule)": mlb["formula_on_test_population"]["formula_default"],
            "Formula + escalation (hand rule)": mlb["formula_on_test_population"]["escalation_default"],
        }
        for proto, plabel in (("cross_validation", "CV"), ("cross_seed", "cross-seed")):
            for view, vlabel in (("agent_level", "9 agent features"), ("indicator_level", "all indicators")):
                for model, m in mlb["models"][proto][view].items():
                    rows[f"{MODEL_LABELS[model]} — {plabel}, {vlabel}"] = m
        st.dataframe(metrics_table(rows), hide_index=True, width="stretch")
        lw = mlb["learned_agent_weights"]
        st.markdown("**Hand weights vs learned logistic-regression coefficients** (positive favours admission)")
        st.dataframe(pd.DataFrame([
            {"Feature": k, "Hand weight": lw["hand_weights"][k], "Learned coefficient": lw["learned"][k]}
            for k in lw["hand_weights"]
        ]), hide_index=True, width="stretch")
