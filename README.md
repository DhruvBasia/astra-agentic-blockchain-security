# ASTRA: Autonomous Security and Threat Response using Agentic AI for Blockchain
### B.Tech (AI & DS) Research Prototype & Evaluation Framework
**Institution:** University School of Automation and Robotics (USAR), GGSIPU  
**Researchers:** Dhruv Basia & Amisha Rawat  
**Supervisor:** Prof. Rahul Johari  

### Demo video (4 min)
**[▶ Watch on YouTube](https://youtu.be/p092B3Q_7OI)** — the four pre-admission attacks explained, how ASTRA's agents and Trust Factor decide, then all four attacks run live on a local Ethereum chain (Ganache): the LangGraph multi-agent graph analyses each one, pauses for the human administrator, and the run is saved. The four runs shown are in [`results/attack_runs/`](results/attack_runs/) (`20261029_*`).

### Reproduce in three commands
```bash
pip install -r requirements.txt
pytest -q tests/                            # 26 tests, no blockchain needed
python -m astra eval --backend sim --n 120  # regenerates results/eval_report.md
```
Live-chain runs additionally need Ganache (`npx ganache --port 7545 --wallet.deterministic true`), then `python -m astra attack --type all --backend ganache` or the dashboard (`python -m astra dashboard`).

---

## 1. System Overview

**ASTRA** is a two-layer, multi-agent autonomous security framework engineered to safeguard decentralized blockchain networks against pre-admission intrusions, stealthy probation behaviors, and post-admission consensus manipulations.

The core architecture strictly separates responsibilities into three phases:

1. **Pre-Admission Layer:** When a candidate node requests network admission, the **Monitor Agent** extracts verifiable blockchain and peer-to-peer telemetry and dispatches four specialized agents:
   - **Sybil Agent ($S$):** Funding graph cluster analysis, burst sibling detection, closed-loop transfers, and behavioral Jaccard similarity.
   - **Wallet Agent ($W$):** Transaction burstiness ($<10\text{s}$ inter-arrival), dusting behavior, repeated transfers, fan-out ratios, failed-tx ratios, and median/MAD population $z$-scores.
   - **Finney Agent ($F$):** Cross-layer mempool conflict matching against on-chain transactions by `(sender, nonce)`, distinguishing legitimate Replace-By-Fee (RBF) from divergent recipient double-spends and withheld block discovery.
   - **Eclipse Agent ($E$):** Peer degree distribution, Autonomous System Number (ASN) Herfindahl-Hirschman Index (HHI), backbone overlap, peer freshness, tip lag, and NetworkX node-disjoint paths avoiding attacker-dominated ASNs.
2. **Observation Window (Probation):** Newly admitted nodes enter a strict observation period lasting their first **8–10 transactions** (default: 10). After each transaction, features are re-extracted, historical trust ($H$) and behavioral consistency ($B$) are updated, and the Trust Factor ($TF$) is dynamically recomputed. If $TF < TV$ or specific malicious indicators fire (conflicting transaction, repeated sibling cluster routing), an alert is escalated to the administrator (`CONTINUE`, `INVESTIGATE`, or `REMOVE`). A node graduates to continuous monitoring **only if the window completes cleanly with zero active alerts**.
3. **Post-Admission Continuous Monitoring Layer:** Four specialized surveillance agents monitor sliding block windows across the active network:
   - **51% Attack Agent:** Per-entity main-chain block share with a Wilson 95% lower bound (merging Sybil-linked miner clusters), deep reorganization tracking ($\text{depth} \ge 3$), and transaction censorship detection.
   - **Double-Spending Agent:** Identifies `(sender, nonce)` conflicts across mempool, canonical chain, and orphaned forks, as well as confirmed-then-reversed merchant payments.
   - **Selfish Mining Agent:** Eyal–Sirer state machine tracking, elevated orphan rate anomalies, burst releases ($\le 1\text{s}$) of consecutive blocks by the same miner with withholding lags, and stale block timestamps.
   - **Block Withholding Agent:** Abnormal publication delay tracking against network median and binomial cumulative probability ($p < 0.02$) testing for mining pool share sabotage.

### Human-in-the-Loop Governance
ASTRA strictly enforces the **Human-in-the-Loop** mandate:
> **The AI agents recommend; a human administrator makes the final binding decision.**
Under no circumstance do autonomous agents unilaterally alter consensus rules, evict peers, or modify ledger balances without administrative policy execution.

---

## 2. Exact Mathematical Formulations

All calculations adhere strictly to the project progress report formulations:

### Attack Risk ($AR$)
$$AR = 0.30 \cdot S + 0.20 \cdot W + 0.20 \cdot F + 0.30 \cdot E$$
Where $S, W, F, E \in [0, 1]$ are attack risk scores computed via **Noisy-OR** indicator aggregation:
$$\text{risk} = \frac{1 - \prod_{i} (1 - w_i \cdot s_i)}{1 - \prod_{i} (1 - w_i)}$$

### Positive Trust ($PT$)
$$PT = 0.25 \cdot I + 0.20 \cdot T + 0.20 \cdot N + 0.20 \cdot H + 0.15 \cdot B$$
- $I$: Identity Trust (account age, funder reputation, funding diversity, absence of burst funding)
- $T$: Transaction Trust (success ratio, zero conflict history, value normality)
- $N$: Network Trust (peer count, ASN dispersion, backbone overlap)
- $H$: Historical Trust (track record length, age, absence of prior alerts)
- $B$: Behavioral Consistency (drift between early and recent feature profiles)

### Trust Factor ($TF$) and Decision Policy
$$TF = 0.60 \cdot PT + 0.40 \cdot (1 - AR)$$

$$\text{Recommendation} = \begin{cases} \text{ACCEPT}, & \text{if } TF \ge TV \\ \text{REJECT}, & \text{if } TF < TV \end{cases}$$
Default Trust Value Threshold: $TV = 0.70$.

### Documented Extension: Escalation Flag
The Monitor Agent attaches an **escalation flag** whenever:
1. Any single agent's risk score is $\ge 0.75$, OR
2. An agent discovers critical attack evidence (e.g., active conflicting double-spend or routing table monopoly).

The recommendation remains strictly $TF$-based; the escalation flag advises the human administrator to request manual investigation (`INVESTIGATE`).

---

## 3. Blockchain Backends: Real vs. Simulated

ASTRA supports two switchable implementations of the `ChainBackend` abstraction:

```
                  ┌────────────────────────────────────────┐
                  │       ChainBackend Interface           │
                  │ (accounts, send, sign_only, now, etc.) │
                  └───────────────────┬────────────────────┘
                                      │
            ┌─────────────────────────┴─────────────────────────┐
            ▼                                                   ▼
┌─────────────────────────┐                       ┌──────────────────────────┐
│   SimChain Backend      │                       │  GanacheChain Backend    │
│ Pure Python Ledger      │                       │ Web3.py against Ganache  │
│ Zero setup, fast, seed  │                       │ Real EVM, local signing, │
│ reproducible            │                       │ bytecode reverts on-chain│
└─────────────────────────┘                       └──────────────────────────┘
```

### Honest Disclaimer: What is Real vs. What is Simulated
- **In `GanacheChain` Mode:**
  - **REAL:** Keypair generation (via `eth-account`), local transaction signing, EVM state transitions, gas consumption, account balances, transaction receipts, block headers, and EVM contract reverts (deployed runtime bytecode `60006000fd` = `PUSH1 0 PUSH1 0 REVERT` causing status `0` receipts) are **100% real Ethereum blockchain data** executed on Ganache.
  - **SIMULATED:** Ganache runs as a single instamining process without real P2P nodes, unmined mempools, or competing miners. Therefore, the **P2P peer overlay graph (`PeerRegistry`), unconfirmed mempool sightings (`MempoolLog`), block propagation delays (`BlockPropagationLog`), and multi-miner PoW consensus competition are simulated** across both backends.
- **In `SimChain` Mode:**
  - All ledger balances, nonces, timestamps, and fees are simulated deterministically in pure Python, requiring zero external dependencies and executing instantaneously.

---

## 4. Project Structure

```
astra/
├── __init__.py
├── __main__.py                   # Unified CLI entry point
├── config.py                     # Central configuration & .env loader
├── dashboard.py                  # Streamlit 5-tab research dashboard (incl. Attack Lab)
├── admin/
│   ├── policies.py               # AutoAdmin & InteractiveAdmin policies
├── blockchain/
│   ├── backend.py                # ChainBackend ABC & TxRecord
│   ├── sim_chain.py              # Pure-Python ledger implementation
│   └── ganache_chain.py          # Web3.py Ganache integration
├── consensus_sim/
│   ├── miner_strategies.py       # Honest, Selfish, 51%, Withholding, Race miners
│   └── simulator.py              # Discrete-event PoW consensus engine
├── attack_lab.py                 # Attack -> LangGraph analysis (pause/resume) -> saved record
├── evaluation/
│   ├── runner.py                 # Benchmarking runner & markdown generator
│   ├── dataset.py                # Shared benchmark population + feature views + metrics
│   ├── calibration.py            # TV / weight search on one seed, scored on unseen seeds
│   └── ml_baseline.py            # Logistic regression, random forest, isolation forest
├── network/
│   ├── mempool.py                # MempoolLog & conflict tracking
│   ├── peer_registry.py          # PeerRegistry, PeerProfile, NetworkX graph
│   └── propagation.py            # BlockPropagationLog & latency analytics
├── observation/
│   └── window.py                 # 10-tx probation window manager
├── orchestration/
│   ├── plain_orchestrator.py     # Pure-Python admission workflow
│   └── langgraph_flow.py         # LangGraph StateGraph flow with interrupt()
├── post_admission/
│   ├── attack_51_agent.py        # 51% dominance agent (Wilson lower bound)
│   ├── block_withholding_agent.py# Binomial pool sabotage & delay agent
│   ├── continuous_monitor.py     # Sliding window continuous surveillance
│   ├── double_spend_agent.py     # Cross-layer fork & mempool conflict agent
│   ├── selfish_mining_agent.py   # Eyal-Sirer state machine & burst release agent
│   └── types.py                  # Post-admission dataclasses
├── pre_admission/
│   ├── eclipse_agent.py          # Eclipse routing table agent (HHI, disjoint paths)
│   ├── finney_agent.py           # Finney pre-mine & conflict agent
│   ├── monitor_agent.py          # Master pre-admission orchestrator
│   ├── positive_trust.py         # PT engine (I, T, N, H, B metrics)
│   ├── sybil_agent.py            # Sybil cluster & funding graph agent
│   ├── types.py                  # Pre-admission dataclasses
│   └── wallet_agent.py           # Wallet anomaly & MAD z-score agent
└── scenarios/
    └── generator.py              # 11 candidate profiles & organic traffic generator

tests/
├── test_formulas.py              # Mathematical formula unit tests
├── test_agents.py                # Pre-admission agent unit tests
├── test_observation_window.py    # Probation window & sleeper unit tests
├── test_post_admission.py        # Consensus attack simulation unit tests
├── test_attack_lab.py            # Attack lab + live LangGraph graph tests
├── test_learned_evaluation.py    # Dataset, calibration and ML baseline tests
└── test_e2e.py                   # End-to-end evaluation & LangGraph tests

results/
├── eval_results.json             # Empirical benchmark metrics (JSON)
├── eval_report.md                # Markdown evaluation report
├── calibration.{json,md}         # Calibrated rule and unseen-seed scores
├── ml_baseline.{json,md}         # Learned-classifier comparison
└── attack_runs/                  # One JSON + Markdown record per Attack Lab run

paper/eval_breakdown.py           # Per-profile benchmark table used in the book chapter
start_ganache.bat                 # Starts Ganache on port 7545 (Windows)
legacy/                           # Earlier prototypes, kept for history (see legacy/README.md)
```

---

## 5. Installation & Setup

### Prerequisites
- Python 3.10+ (Python 3.11–3.14 supported)
- Node.js & npm (optional, only required for live Ganache mode)

### 1. Virtual Environment & Dependencies
```bash
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```
Optional: copy `.env.example` to `.env` to change the RPC URL, weights or threshold.

### 2. Optional: Starting Ganache RPC
To test live EVM execution against Ganache:
```bash
npx ganache --port 7545 --wallet.deterministic true
```
The CLI defaults to `http://127.0.0.1:7545`.

---

## 6. CLI Usage & Commands

Run all commands using `python -m astra`:

### 1. System Information & Formulas
Displays loaded weights, threshold $TV$, and mathematical specifications:
```bash
python -m astra info
```

### 2. Narrated Research Demonstration
Runs an end-to-end walkthrough demonstrating Pre-Admission, Observation Window sleeper interception, and Post-Admission consensus surveillance:
```bash
# Pure-Python ledger (zero setup):
python -m astra demo --backend sim

# Live Ganache Web3 node:
python -m astra demo --backend ganache
```

### 3. Candidate Node Admission
Evaluates an individual candidate node profile:
```bash
# Evaluate an honest candidate:
python -m astra admit --candidate honest --backend sim

# Evaluate a Sybil attacker:
python -m astra admit --candidate sybil --backend sim

# Interactive human administrator prompt:
python -m astra admit --candidate finney --backend sim --interactive
```

Supported candidate profiles:
`honest`, `honest_power_user`, `honest_single_cloud`, `honest_fee_bumper`, `sybil`, `stealthy_sybil`, `malicious_wallet`, `finney`, `eclipse`, `partial_eclipse`, `sleeper`.

### 4. Observation Window Probation
Watches a sleeper candidate over its first 10 transactions and intercepts it when it turns rogue:
```bash
python -m astra observe --backend sim --window 10
```

### 5. Post-Admission Consensus Surveillance
Simulates PoW consensus attacks and demonstrates real-time alert emission:
```bash
# Selfish mining simulation:
python -m astra monitor --scenario selfish --blocks 30

# 51% coalition private fork:
python -m astra monitor --scenario coalition_51 --blocks 30

# Block withholding:
python -m astra monitor --scenario block_withholding --blocks 30

# Race double-spend:
python -m astra monitor --scenario race_double_spend --blocks 30
```

### 6. Attack Lab (Attack -> Agent Graph -> Saved Record)
Launches one attack on the chain, runs the LangGraph agent graph on it (`collect -> Sybil | Wallet | Finney | Eclipse -> aggregate -> human_review`), and saves the run as JSON + Markdown under `results/attack_runs/`:
```bash
# One attack on the live Ganache chain:
python -m astra attack --type sybil --backend ganache

# All four pre-admission attacks, with a summary table:
python -m astra attack --type all --backend ganache

# You make the administrator decision yourself at the human_review pause:
python -m astra attack --type finney --backend ganache --interactive
```
Attack types: `sybil`, `malicious_wallet`, `finney`, `eclipse`, `all`. On Ganache the attacker's transactions are real signed transactions; the mempool sighting, block-withholding delay and peer table remain simulated (see Section 3).

### 7. Full Evaluation Benchmark
Executes the empirical benchmark suite across $n$ candidates and consensus scenarios, generating `results/eval_results.json` and `results/eval_report.md`:
```bash
python -m astra eval --backend sim --n 120
```

### 8. Decision-Rule Calibration (unseen-seed protocol)
Learns the threshold $TV$ and the $TF$ weight split on a population generated from one seed, then scores the learned rule on populations from seeds it never saw. Writes `results/calibration.json` and `results/calibration.md`:
```bash
python -m astra calibrate --train-seed 7 --test-seeds 42 1 2 3 4
```

### 9. Learned-Classifier Baseline
Trains logistic regression, random forest and an (unsupervised) isolation forest on the agents' evidence and compares them with the hand-written $TF$ rule, both by stratified 5-fold cross-validation and by training on one seed and testing on another. Also prints the learned agent-level coefficients next to the hand weights. Writes `results/ml_baseline.json` and `results/ml_baseline.md`:
```bash
python -m astra ml --seed 42 --train-seed 7
```

### 10. Dashboard
```bash
python -m astra dashboard
```

---

## 7. Interactive Streamlit Dashboard

ASTRA includes a research dashboard structured into 5 tabs:

```bash
python -m astra dashboard
# or: streamlit run astra/dashboard.py
```

### Dashboard Tabs:
1. **Attack Lab:** Pick an attack and a backend (SimChain or live Ganache), launch it, and watch the LangGraph agent graph light up node by node. The graph pauses at `human_review`; you decide with Accept / Reject / Investigate, the graph resumes, and the run is saved as JSON + Markdown with download buttons and a browser of earlier runs.
2. **Pre-Admission Node Admission:** Select any of the 11 candidate profiles, inspect each agent's risk, evidence and indicator table, and record an administrator decision.
3. **Observation Window (Probation):** Step-by-step transaction simulator showing $H$, $B$ and $TF$ per transaction as a sleeper node turns rogue.
4. **Post-Admission Consensus Monitor:** Multi-miner PoW simulator with the block timeline, orphan counts and the continuous agents' alert feed.
5. **Research Evaluation:** Runs the 120-candidate benchmark, the per-profile breakdown, the calibration and the learned-classifier baseline, and shows their tables side by side.

---

## 8. Empirical Evaluation Results

All evaluation figures are **derived empirically from simulation runs** (no pre-baked or invented numbers).

Summary from `python -m astra eval --backend sim --n 120` (57 honest incl. 38 hard negatives, 63 attackers):

| Metric | Policy A: Formula Only ($TF \ge TV$) | Policy B: Formula + Escalation Flag |
| :--- | :---: | :---: |
| **Accuracy** | **65.8%** | **100.0%** |
| **Precision** | **100.0%** | **100.0%** |
| **Recall (Detection Rate)** | **34.9%** | **100.0%** |
| **False Positive Rate (FPR)** | **0.0%** | **0.0%** |
| **False Negative Rate (FNR)** | **65.1%** | **0.0%** |

### Per-Attack Detection Rates (Policy B)
- **Sybil Attack:** 100.0% (14/14 intercepted)
- **Stealthy Sybil (layered funding):** 100.0% (10/10 intercepted)
- **Malicious Wallet Attack:** 100.0% (14/14 intercepted)
- **Finney Attack:** 100.0% (10/10 intercepted)
- **Eclipse Attack:** 100.0% (10/10 intercepted)
- **Partial Eclipse:** 100.0% (5/5 intercepted)

### Calibration and Learned Baseline (`python -m astra calibrate`, `python -m astra ml`)
- **Calibrated rule** (fitted on seed 7, scored on seeds 42, 1, 2, 3, 4): $TV = 0.80$, $TF = 0.30\,PT + 0.70\,(1-AR)$. The formula alone then reaches 100% accuracy on every unseen seed, against 65.8% with the default $TV = 0.70$ / $0.60$–$0.40$ split. The learned rule weights $1-AR$ far more heavily than $PT$: a strong finding by one agent should not be diluted by positive trust.
- **Logistic regression and random forest** reach 100% on the same population, under both 5-fold cross-validation and the cross-seed protocol; the **unsupervised isolation forest** reaches 85–95% without ever seeing a label. The logistic-regression coefficients rank the Eclipse and Sybil risks and Identity trust highest, in the same order as the hand weights.
- **Read these numbers with their limits.** The candidates come from a templated generator written by the same authors as the detectors, the profiles differ across seeds only in random amounts and timings, and the stealthy-Sybil detector was built knowing how the generator layers funding. The honest result is that the pipeline separates these synthetic profiles cleanly, not that it would do so against live adversaries.

### What changed since the October progress report
The earlier benchmark (61.7% / 64.2% accuracy, 57.9% FPR) was dominated by a generator defect: the two exchange hubs held 15 ETH each while 120 candidates needed about 130 ETH, so later honest candidates were funded by *reverted* transactions, all of their own transfers then reverted, and the Wallet agent flagged them as attackers. A second artifact froze every peer's reported block height at candidate creation, so every honest node showed "100% of peers lagging" at evaluation time. Both are fixed (`exchange_balance_eth`, `PeerProfile.sampled_at_tip`), and the detectors gained: layered (multi-hop) funding detection and 24-hour sibling windows in the Sybil agent; a true "fresh destination" test and a ledger-derived velocity baseline in the Wallet agent; corroborated concentration (known-provider discount, fresh-peer ratio, routing-table takeover) in the Eclipse agent; and known exchange hubs passed to the agents.

### Observation Window (Sleeper Interception)
- **Candidate:** `SLEEPER_TEST_01` (Clean at admission, turns malicious at Transaction 5)
- **Interception Step:** Transaction #5
- **Detection Latency:** **1 transaction** after attack initiation
- **Graduation Status:** Clean graduation blocked; escalated for administrative removal.

### Post-Admission Consensus Surveillance
- **Honest Baseline:** Clean execution (0 false alarms across 36 blocks).
- **Selfish Mining:** Intercepted within 54.1s (elevated orphan rate + burst release).
- **51% Coalition:** Intercepted immediately on private fork reorg invalidating 4 blocks.
- **Block Withholding:** Intercepted within 54.1s (propagation delay $> 50\times$ network median).
- **Race Double-Spend:** Intercepted upon conflicting on-chain vs. mempool recipient sighting.

---

## 9. Configuration & Tuning Guide

All weights, thresholds, and simulation parameters live in `astra/config.py` and can be customized via `.env`:

```env
# Trust Factor Threshold
ASTRA_THRESHOLD_TV=0.70

# Attack Risk Agent Weights (must sum to 1.0)
ASTRA_WEIGHT_SYBIL=0.30
ASTRA_WEIGHT_WALLET=0.20
ASTRA_WEIGHT_FINNEY=0.20
ASTRA_WEIGHT_ECLIPSE=0.30

# Positive Trust Weights (must sum to 1.0)
ASTRA_WEIGHT_PT_I=0.25
ASTRA_WEIGHT_PT_T=0.20
ASTRA_WEIGHT_PT_N=0.20
ASTRA_WEIGHT_PT_H=0.20
ASTRA_WEIGHT_PT_B=0.15

# Trust Factor Formula Weights
ASTRA_WEIGHT_TF_PT=0.60
ASTRA_WEIGHT_TF_AR=0.40

# Observation Window & Escalation
ASTRA_OBSERVATION_WINDOW_SIZE=10
ASTRA_ESCALATION_THRESHOLD=0.75

# Blockchain RPC
BLOCKCHAIN_RPC_URL=http://127.0.0.1:7545
```

---

## 10. Verification & Test Suite

Run the complete automated unit and integration test suite:
```bash
pytest -v tests/
```

Test coverage includes:
- `test_formulas.py`: Strict validation of $AR$, $PT$, and $TF$ formulas.
- `test_agents.py`: Clean vs. attack contrast testing for Sybil, Wallet, Finney, and Eclipse agents.
- `test_observation_window.py`: Honest node graduation vs. sleeper node interception.
- `test_post_admission.py`: Consensus simulations across all 5 miner scenarios (Honest, Selfish, 51%, Withholding, Race).
- `test_e2e.py`: Orchestrator workflows, JSON/markdown evaluation outputs, and LangGraph human-in-the-loop interruption/resumption.
