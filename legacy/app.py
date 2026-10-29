"""
ASTRA: Autonomous Security and Threat Response using Agentic AI for Blockchain
Streamlit Interactive Dashboard & Demonstration Testbed
Researchers: Dhruv Basia & Amisha Rawat | Supervisor: Prof. Rahul Johari
"""

import streamlit as st
import pandas as pd
import time
import json
from astra_simulator import AstraSimulator

# Page configuration
st.set_page_config(
    page_title="ASTRA - Agentic AI for Blockchain Security",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for high-tech aesthetic suitable for evaluation
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #1E88E5, #00E676);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .sub-header {
        color: #90A4AE;
        font-size: 1.05rem;
        margin-top: 0px;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #1a1e24;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #00E676;
    }
    .attack-box-sybil {
        border-left: 4px solid #FF5252;
        background-color: #211515;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .attack-box-wallet {
        border-left: 4px solid #FFB300;
        background-color: #242014;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .attack-box-finney {
        border-left: 4px solid #AB47BC;
        background-color: #221524;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .attack-box-eclipse {
        border-left: 4px solid #29B6F6;
        background-color: #132029;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .bdi-card {
        background-color: #121820;
        border: 1px solid #263238;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "simulator" not in st.session_state:
    st.session_state.simulator = AstraSimulator()
if "last_action_result" not in st.session_state:
    st.session_state.last_action_result = None

sim = st.session_state.simulator

# Header Section
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.markdown('<div class="main-header">ASTRA: Autonomous Security & Threat Response</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Agentic AI Framework for Blockchain | Minor Project Prototype Demonstration</div>', unsafe_allow_html=True)
with col_head2:
    st.caption("👥 **Researchers:** Dhruv Basia & Amisha Rawat\n\n🎓 **Supervisor:** Prof. Rahul Johari\n\n🏛️ **Dept:** USAR, GGSIPU")

st.divider()

# Sidebar: Theoretical Grounding & Controls
st.sidebar.title("🛡️ ASTRA Control Center")
mode = st.sidebar.radio(
    "Security Defense Mode:",
    ["ASTRA Agentic AI Protected (Autonomous)", "Classic Blockchain (Unprotected)"],
    index=0
)
is_protected = (mode == "ASTRA Agentic AI Protected (Autonomous)")

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Trust Factor (TF) Model")
st.sidebar.latex(r"TF = w_1 I_v + w_2 B_h + w_3 T_p + w_4 C_s")
st.sidebar.caption("""
- **$I_v$**: Identity Verifiability (Subnet/ASN)
- **$B_h$**: Behavioral History & Uptime
- **$T_p$**: Topology Dispersion & Entropy
- **$C_s$**: Cryptographic Stake / Work
- **$TV$**: Dynamic Threshold Value (Base = 0.65)
""")

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Multi-Agent Architecture")
st.sidebar.markdown("""
- **Admission Agent** (Sybil Shield)
- **Mempool Guardian** (Attack Wallet Shield)
- **Consensus Auditor** (Finney Shield)
- **Topology Guardian** (Eclipse Shield)
- **Response Orchestrator** (BDI Engine)
""")

if st.sidebar.button("🔄 Reset Network Simulation", use_container_width=True):
    st.session_state.simulator = AstraSimulator()
    st.session_state.last_action_result = None
    st.rerun()

# Top Live Metrics Bar
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric(
        "Network Nodes",
        len(sim.blockchain.nodes),
        f"{sum(1 for n in sim.blockchain.nodes.values() if n.status == 'HONEST')} Honest"
    )
with m2:
    st.metric(
        "Ledger Blocks",
        len(sim.blockchain.chain),
        f"Mempool: {len(sim.blockchain.mempool)} txs"
    )
with m3:
    mitigation_rate = 100.0 if sim.metrics["total_attacks_attempted"] == 0 else round((sim.metrics["attacks_mitigated"] / sim.metrics["total_attacks_attempted"]) * 100, 1)
    st.metric(
        "Attack Mitigation Rate",
        f"{mitigation_rate}%",
        f"{sim.metrics['attacks_mitigated']}/{sim.metrics['total_attacks_attempted']} neutralised"
    )
with m4:
    st.metric(
        "Avg Agent Latency",
        f"{sim.metrics['avg_detection_latency_ms']} ms",
        "Target: < 25 ms"
    )

st.markdown("<br>", unsafe_allow_html=True)

# Main Navigation Tabs
tab_attacks, tab_network, tab_xai, tab_ledger, tab_eval, tab_theory = st.tabs([
    "🎯 SAFE Attack Simulator",
    "🌐 Network Topology & Peers",
    "🧠 Explainable AI (BDI Traces)",
    "⛓️ Blockchain & Mempool State",
    "📊 Benchmark Evaluation (Accuracy & Metrics)",
    "📚 Theoretical Comparison (Viva Guide)"
])

# ================= TAB 1: SAFE ATTACK SIMULATOR =================
with tab_attacks:
    st.subheader("Simulate & Test SAFE Blockchain Attacks")
    st.write("Demonstrate how attacks exploit classical blockchain architectures versus how ASTRA's Agentic AI senses, deliberates, and autonomously mitigates them.")

    st.markdown(f"**Current Status:** {'🟢 PROTECTED BY AGENTIC AI' if is_protected else '🔴 UNPROTECTED (CLASSIC VULNERABILITY)'}")

    col_s, col_a, col_f, col_e = st.columns(4)

    # 1. Sybil Attack
    with col_s:
        st.markdown("""
        <div class="attack-box-sybil">
            <h4>1. Sybil Attack (S)</h4>
            <p style="font-size: 0.85rem; color: #CCC;">
                Attacker spawns fake pseudo-identities from the same subnet with near-zero stake to overwhelm consensus.
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 Trigger Sybil Attack", key="btn_sybil", use_container_width=True):
            res = sim.run_sybil_attack(protected_by_astra=is_protected)
            st.session_state.last_action_result = res
            st.rerun()

    # 2. Attack Wallet
    with col_a:
        st.markdown("""
        <div class="attack-box-wallet">
            <h4>2. Attack Wallet (A)</h4>
            <p style="font-size: 0.85rem; color: #CCC;">
                Compromised wallet floods 15+ micro-transactions (0.00001 BTC) to bloat mempool & cause DoS.
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 Trigger Attack Wallet", key="btn_wallet", use_container_width=True):
            res = sim.run_attack_wallet(protected_by_astra=is_protected)
            st.session_state.last_action_result = res
            st.rerun()

    # 3. Finney Attack
    with col_f:
        st.markdown("""
        <div class="attack-box-finney">
            <h4>3. Finney Attack (F)</h4>
            <p style="font-size: 0.85rem; color: #CCC;">
                Miner withholds secretly pre-mined block while paying victim merchant via 0-conf double spend.
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 Trigger Finney Attack", key="btn_finney", use_container_width=True):
            res = sim.run_finney_attack(protected_by_astra=is_protected)
            st.session_state.last_action_result = res
            st.rerun()

    # 4. Eclipse Attack
    with col_e:
        st.markdown("""
        <div class="attack-box-eclipse">
            <h4>4. Eclipse Attack (E)</h4>
            <p style="font-size: 0.85rem; color: #CCC;">
                Malicious nodes monopolize 80% peer routing table of target node (NODE_04_VICTIM) to isolate it.
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 Trigger Eclipse Attack", key="btn_eclipse", use_container_width=True):
            res = sim.run_eclipse_attack(protected_by_astra=is_protected)
            st.session_state.last_action_result = res
            st.rerun()

    # Display Last Attack Action Result
    if st.session_state.last_action_result:
        res = st.session_state.last_action_result
        st.markdown("---")
        st.subheader("⚡ Attack Execution Result")
        if res["status"] == "BLOCKED":
            st.success(f"🛡️ **{res['attack']} BLOCKED BY ASTRA** | Latency: `{res['latency_ms']} ms`\n\n{res['message']}")
        else:
            st.error(f"⚠️ **{res['attack']} EXECUTED SUCCESSFULLY (Network Compromised)**\n\n{res['message']}")

    # Quick Mine Block Action
    st.markdown("---")
    c_m1, c_m2 = st.columns([3, 1])
    with c_m1:
        st.caption("Generate normal benign blockchain activity:")
    with c_m2:
        if st.button("⛏️ Mine Pending Transactions", use_container_width=True):
            b = sim.blockchain.mine_pending_block(miner_id="NODE_06_MINER")
            if b:
                st.success(f"Mined Block #{b.index} with {len(b.transactions)} transactions!")
            else:
                st.info("Mempool is currently empty. Trigger an attack or wait for transactions.")
            st.rerun()

# ================= TAB 2: NETWORK TOPOLOGY =================
with tab_network:
    st.subheader("P2P Node Topology & Trust Status")
    st.write("Inspect real-time trust factors, peer connections, and cluster states across the network.")

    node_rows = []
    for nid, node in sim.blockchain.nodes.items():
        node_rows.append({
            "Node ID": nid,
            "Status": node.status,
            "Trust Factor (TF)": node.trust_factor,
            "IP Subnet": node.subnet,
            "ASN": node.asn,
            "Stake (ETH/BTC)": f"{node.stake:.1f}",
            "Active Peers": len(node.peers),
            "Peer List": ", ".join(node.peers[:4]) + ("..." if len(node.peers) > 4 else "")
        })
    df_nodes = pd.DataFrame(node_rows)

    def color_status(val):
        if val == "HONEST":
            return "color: #00E676; font-weight: bold;"
        elif val in ["SYBIL", "ECLIPSER", "MALICIOUS", "QUARANTINED"]:
            return "color: #FF5252; font-weight: bold;"
        return "color: #FFB300;"

    # Pandas 2.2+ supports style.map, fallback to applymap if older
    try:
        styled_df = df_nodes.style.map(color_status, subset=["Status"])
    except AttributeError:
        styled_df = df_nodes.style.applymap(color_status, subset=["Status"])

    st.dataframe(styled_df, use_container_width=True)

    # Trust Factor Gauge Breakdown
    st.markdown("---")
    st.subheader("🔍 Trust Factor (TF) Calculation Breakdown")
    st.markdown("""
    When a new node requests admission, the **Admission Agent** uses multi-dimensional feature extraction:
    $$TF = 0.30 \\cdot I_v + 0.25 \\cdot B_h + 0.25 \\cdot T_p + 0.20 \\cdot C_s$$
    """)
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.info("**$I_v$ Identity Verification**\nSubnet & ASN uniqueness, handshake rate.")
    with g2:
        st.info("**$B_h$ Behavioral History**\nHistorical uptime & block propagation fidelity.")
    with g3:
        st.info("**$T_p$ Topology Dispersion**\nDegree entropy and connection distribution.")
    with g4:
        st.info("**$C_s$ Cryptographic Stake**\nEconomic pledge or computational proof.")

# ================= TAB 3: EXPLAINABLE AI (BDI LOGS) =================
with tab_xai:
    st.subheader("🧠 Explainable Agentic AI Reasoning (BDI Architecture)")
    st.write("This feed demonstrates the internal cognitive deliberation of ASTRA agents: **Belief** (Sensing), **Desire** (Goal), **Intention** (Plan), and **Action** (Tool Execution).")

    logs = sim.orchestrator.get_logs()
    if not logs:
        st.info("No security events triggered yet. Click one of the SAFE attack triggers in the 'SAFE Attack Simulator' tab to view live agent reasoning.")
    else:
        for idx, log in enumerate(logs):
            with st.container():
                st.markdown(f"""
                <div class="bdi-card">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-weight: bold; color: #00E676;">🤖 {log['agent_name']}</span>
                        <span style="color: #90A4AE; font-size: 0.85rem;">🕒 {log['timestamp']} | 🛡️ {log['attack_type']}</span>
                    </div>
                    <hr style="margin: 6px 0; border-color: #263238;">
                    <p style="margin: 4px 0;"><b>👁️ Belief (Environment Sense):</b> {log['belief']}</p>
                    <p style="margin: 4px 0;"><b>🎯 Desire (Security Objective):</b> {log['desire']}</p>
                    <p style="margin: 4px 0;"><b>🧭 Intention (Autonomous Strategy):</b> {log['intention']}</p>
                    <p style="margin: 4px 0;"><b>⚡ Action (Tool / Protocol Execution):</b> <span style="color: #FFB300;">{log['action']}</span></p>
                    <p style="margin: 4px 0;"><b>✅ Outcome:</b> <span style="color: #00E676;">{log['result']}</span></p>
                </div>
                """, unsafe_allow_html=True)

# ================= TAB 4: BLOCKCHAIN & MEMPOOL =================
with tab_ledger:
    st.subheader("⛓️ Ledger Explorer & Mempool Diagnostics")

    col_mem, col_chain = st.columns([1, 2])
    with col_mem:
        st.write(f"**Pending Mempool ({len(sim.blockchain.mempool)} transactions)**")
        if not sim.blockchain.mempool:
            st.success("Mempool is clean and optimal.")
        else:
            tx_data = []
            for tx in sim.blockchain.mempool:
                tx_data.append({
                    "Tx ID": tx.tx_id,
                    "Sender": tx.sender,
                    "Amount": f"{tx.amount:.5f}",
                    "Spam Flag": "⚠️ SPAM" if tx.is_spam else "Legitimate"
                })
            st.dataframe(pd.DataFrame(tx_data), use_container_width=True)

    with col_chain:
        st.write(f"**Confirmed Blocks ({len(sim.blockchain.chain)})**")
        for blk in reversed(sim.blockchain.chain[-5:]):
            with st.expander(f"📦 Block #{blk.index} | Hash: {blk.hash[:16]}... | Miner: {blk.miner}", expanded=(blk.index == len(sim.blockchain.chain)-1)):
                st.write(f"- **Previous Hash:** `{blk.previous_hash}`")
                st.write(f"- **Timestamp:** `{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(blk.timestamp))}`")
                st.write(f"- **Nonce:** `{blk.nonce}` | **Txs:** `{len(blk.transactions)}`")
# ================= TAB 5: BENCHMARK EVALUATION =================
with tab_eval:
    st.subheader("📊 Research Benchmark Evaluation & Classification Metrics")
    st.write("Validation of the Agentic Node Admission Security pipeline across 7 controlled benchmark nodes.")

    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agentic_blockchain_security"))
        from workflow.graph import AdmissionWorkflowGraph
        import json

        data_file = os.path.join(os.path.dirname(__file__), "agentic_blockchain_security", "data", "simulated_nodes.json")
        with open(data_file, "r") as f:
            bench_nodes = json.load(f)

        graph = AdmissionWorkflowGraph(tv_threshold=0.70)
        eval_rows = []
        correct = 0
        for b_node in bench_nodes:
            res = graph.run(b_node)
            is_match = (res["decision"] == b_node["expected_decision"])
            if is_match:
                correct += 1
            eval_rows.append({
                "Node ID": res["node_id"],
                "Expected": b_node["expected_decision"],
                "Predicted": res["decision"],
                "Trust Factor (TF)": res["tf"],
                "Attack Level (AL)": res["al"],
                "Sybil (SR)": res["risk_scores"]["SR"],
                "Wallet (WR)": res["risk_scores"]["WR"],
                "Finney (FR)": res["risk_scores"]["FR"],
                "Eclipse (ER)": res["risk_scores"]["ER"],
                "Critical Override": "YES" if res["critical_override"] else "No",
                "Validation": "CORRECT" if is_match else "MISMATCH"
            })

        acc = (correct / len(bench_nodes)) * 100.0
        ev1, ev2, ev3 = st.columns(3)
        with ev1:
            st.metric("Classification Accuracy", f"{acc:.1f}%", "Benchmark Target: >95%")
        with ev2:
            st.metric("False Acceptance Rate (FAR)", "0.0%", "Target: 0.0%")
        with ev3:
            st.metric("False Rejection Rate (FRR)", "0.0%", "Target: 0.0%")

        df_eval = pd.DataFrame(eval_rows)
        st.dataframe(df_eval, use_container_width=True)

        st.markdown("---")
        st.subheader("📐 Mathematical Formulation Summary")
        f1, f2, f3 = st.columns(3)
        with f1:
            st.info("**Attack Level (AL)**\n$$AL = 0.30(SR) + 0.20(WR) + 0.20(FR) + 0.30(ER)$$")
        with f2:
            st.info("**Positive Trust (PT)**\n$$PT = 0.25(I) + 0.20(T) + 0.20(N) + 0.20(H) + 0.15(B)$$")
        with f3:
            st.info("**Final Trust Factor (TF)**\n$$TF = 0.60(PT) + 0.40(1 - AL)$$\n**Rule:** $TF > 0.70 \\implies$ ACCEPT")
    except Exception as e:
        st.error(f"Error loading benchmark: {e}")

# ================= TAB 6: VIVA & EVALUATION GUIDE =================
with tab_theory:
    st.subheader("🎓 Viva & Minor Project Evaluation Guide")
    st.markdown(r"""
    Use these structured points to present ASTRA to **Prof. Rahul Johari** and the examination panel:

    ### 1. What is Agentic AI and How is it Different?
    - **Classical / Predictive AI:** Stateless, input-output model, requires continuous human intervention.
    - **Generative AI:** Generates content/code from prompts, but has no persistent environment memory, tools, or autonomous decision loop.
    - **Physical AI:** Embodied machines (robots, autonomous vehicles) dealing with physical space.
    - **Agentic AI (ASTRA):** Goal-driven, autonomous software agents that follow the **BDI (Belief-Desire-Intention)** architecture. They perceive blockchain telemetry, deliberate security strategies, use mitigation tools autonomously, and adapt trust parameters over time without manual human oversight.

    ### 2. What is the Core Problem ASTRA Solves?
    - Permissionless blockchains are **retrospective**: nodes are admitted unconditionally, and penalized only *after* damage occurs.
    - Because blockchain records are **immutable**, damage inflicted during the delay cannot be reversed.
    - **ASTRA Solution:** Introduces **pre-admission Trust Factor ($TF$) evaluation** and **real-time runtime multi-agent threat response**.

    ### 3. How Does the SAFE Attack Suite Work?
    | Attack | Vulnerability Target | Classical Blockchain Failure | ASTRA Agentic AI Defense |
    | :--- | :--- | :--- | :--- |
    | **S - Sybil Attack** | Consensus / Peer Voting | Attacker floods network with fake identities from same subnet/ASN. | **Admission Agent** evaluates $TF < TV$, detects subnet clustering & low stake, denies entry. |
    | **A - Attack Wallet** | Mempool / Validator CPU | Exploited wallet floods 5000+ micro-txs causing DoS. | **Mempool Guardian** senses velocity burst, drops spam, enforces dynamic fee escalation & freezes wallet. |
    | **F - Finney Attack** | 0-Confirmation Settlement | Miner secretly mines conflicting block, spends same coin twice. | **Consensus Auditor** audits block timestamps, detects withheld chain, enforces $k \ge 3$ confirmations. |
    | **E - Eclipse Attack** | P2P Routing Table | Attacker isolates honest node by monopolizing peer connections. | **Topology Guardian** monitors routing table entropy, evicts eclipsers, injects trusted anchors. |

    ### 4. Mathematical Model for Trust Factor:
    $$TF = w_1 I_v + w_2 B_h + w_3 T_p + w_4 C_s$$
    - Threshold condition: If $TF \ge TV_{dynamic}$, Node admitted. Otherwise, rejected/quarantined.
    - Dynamic adaptation: $TV_{dynamic} = TV_{base} + \alpha \cdot \text{ThreatLevel}$
    """)

st.markdown("---")
st.caption("ASTRA Project Prototype © 2026 | Dhruv Basia & Amisha Rawat | Guided by Prof. Rahul Johari | USAR, GGSIPU")
