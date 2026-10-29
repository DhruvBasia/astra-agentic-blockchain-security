import streamlit as st

from blockchain.data_collector import BlockchainDataCollector
from blockchain.create_normal_scenario import run_normal_scenario
from blockchain.create_sybil_scenario import run_sybil_scenario

from agents.monitor_agent import MonitorAgent
from agents.sybil_agent import SybilAgent
from scoring.trust_calculator import TrustCalculator


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Blockchain Node Security",
    page_icon="🔐",
    layout="wide"
)


# --------------------------------------------------
# TITLE
# --------------------------------------------------

st.title("🔐 Blockchain Node Security")

st.write(
    "Agentic AI-Based Blockchain Node Admission "
    "and Continuous Security Monitoring"
)

st.divider()


# --------------------------------------------------
# CURRENT BLOCKCHAIN STATUS
# --------------------------------------------------

collector = BlockchainDataCollector()
blockchain_data = collector.collect_all_data()

blockchain = blockchain_data["blockchain"]
accounts = blockchain_data["accounts"]
transactions = blockchain_data["transactions"]


st.subheader("⛓️ Blockchain Status")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Connection", "ACTIVE")

with col2:
    st.metric(
        "Latest Block",
        blockchain["latest_block"]
    )

with col3:
    st.metric(
        "Accounts",
        len(accounts)
    )

with col4:
    st.metric(
        "Transactions",
        len(transactions)
    )


st.divider()


# --------------------------------------------------
# SCENARIO SELECTION
# --------------------------------------------------

st.subheader("🧪 Security Scenario")

st.write(
    "Select the blockchain activity scenario you want "
    "to generate and analyze."
)

scenario = st.radio(
    "Choose Scenario:",
    [
        "🟢 Normal Scenario",
        "🔴 Sybil Attack Scenario"
    ],
    horizontal=True
)


if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False


if st.button(
    "▶️ Run Scenario & Analyze",
    type="primary",
    use_container_width=True
):

    # --------------------------------------------------
    # NORMAL SCENARIO
    # --------------------------------------------------

    if scenario == "🟢 Normal Scenario":

        st.info(
            "Generating normal blockchain activity..."
        )

        run_normal_scenario()

        st.success(
            "Normal scenario generated successfully."
        )


    # --------------------------------------------------
    # SYBIL SCENARIO
    # --------------------------------------------------

    else:

        st.warning(
            "Generating controlled Sybil attack scenario..."
        )

        run_sybil_scenario()

        st.success(
            "Sybil scenario generated successfully."
        )


    # --------------------------------------------------
    # COLLECT NEW DATA
    # --------------------------------------------------

    collector = BlockchainDataCollector()
    blockchain_data = collector.collect_all_data()

    monitor = MonitorAgent()
    monitor_result = monitor.analyze(
        blockchain_data
    )

    sybil = SybilAgent()
    sybil_result = sybil.analyze(
        blockchain_data
    )

    calculator = TrustCalculator()

    trust_result = calculator.calculate(
        sybil_result
    )

    st.session_state.analysis_complete = True
    st.session_state.sybil_result = sybil_result
    st.session_state.trust_result = trust_result
    st.session_state.blockchain_data = blockchain_data


# --------------------------------------------------
# DISPLAY RESULTS
# --------------------------------------------------

if st.session_state.analysis_complete:

    sybil_result = st.session_state.sybil_result
    trust_result = st.session_state.trust_result
    blockchain_data = st.session_state.blockchain_data

    st.divider()

    st.subheader("🛡️ Security Analysis Result")

    # --------------------------------------------------
    # MAIN RESULT
    # --------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Sybil Risk",
            f"{sybil_result['risk_score']:.3f}"
        )

    with col2:

        st.metric(
            "Risk Level",
            sybil_result["risk_level"]
        )

    with col3:

        st.metric(
            "Provisional Trust",
            f"{trust_result['provisional_trust']:.3f}"
        )


    st.divider()


    # --------------------------------------------------
    # EVIDENCE
    # --------------------------------------------------

    st.subheader("📊 Detection Evidence")

    col1, col2 = st.columns(2)

    with col1:

        st.write("**Common Funding**")

        st.progress(
            sybil_result["common_funding"]
        )

        st.caption(
            f"{sybil_result['common_funding']:.3f}"
        )


        st.write("**Behaviour Similarity**")

        st.progress(
            sybil_result["behavior_similarity"]
        )

        st.caption(
            f"{sybil_result['behavior_similarity']:.3f}"
        )


    with col2:

        st.write("**Interaction Similarity**")

        st.progress(
            sybil_result["interaction_similarity"]
        )

        st.caption(
            f"{sybil_result['interaction_similarity']:.3f}"
        )


        st.write("**Timing Similarity**")

        st.progress(
            sybil_result["timing_similarity"]
        )

        st.caption(
            f"{sybil_result['timing_similarity']:.3f}"
        )


    st.divider()


    # --------------------------------------------------
    # SUSPICIOUS GROUP
    # --------------------------------------------------

    st.subheader("🚨 Suspicious Accounts")

    suspicious_group = sybil_result[
        "suspicious_group"
    ]

    if suspicious_group:

        for account in suspicious_group:

            st.code(account)

    else:

        st.write(
            "No suspicious group identified."
        )


    st.divider()


    # --------------------------------------------------
    # DETECTION REASONS
    # --------------------------------------------------

    st.subheader("🧾 Detection Evidence")

    for evidence in sybil_result["evidence"]:

        st.write(
            "•",
            evidence
        )


    st.divider()


    # --------------------------------------------------
    # ADMISSION ASSESSMENT
    # --------------------------------------------------

    st.subheader("🚦 Admission Assessment")

    if sybil_result["risk_level"] == "HIGH":

        st.error(
            "⚠️ MANUAL REVIEW REQUIRED"
        )

    elif sybil_result["risk_level"] == "MEDIUM":

        st.warning(
            "⚠️ MANUAL REVIEW REQUIRED"
        )

    else:

        st.success(
            "✅ PROVISIONAL ADMISSION"
        )


    st.info(
        "The system provides evidence and a recommendation. "
        "The final admission decision is made by the administrator."
    )