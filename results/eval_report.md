# ASTRA: RESEARCH EVALUATION BENCHMARK REPORT
**System:** ASTRA: Autonomous Security and Threat Response using Agentic AI  
**Evaluation Date:** 2026-10-23 18:41:41 UTC  
**Backend:** SimChain  
**Dataset Nature:** *SYNTHETIC SIMULATION BENCHMARK (All numbers derived empirically from simulation execution)*

---

## 1. PRE-ADMISSION LAYER PERFORMANCE

Evaluated on **120** diverse candidates (including honest users, power users, single-cloud nodes, Replace-By-Fee bouncers, Sybil clusters, bot wallets, Finney attackers, and Eclipse networks).

| Evaluation Metric | Policy A: Formula Only (TF >= TV) | Policy B: Formula + Escalation Flag |
| :--- | :---: | :---: |
| **Accuracy** | **65.8%** | **100.0%** |
| **Precision** | **100.0%** | **100.0%** |
| **Recall (Detection Rate)** | **34.9%** | **100.0%** |
| **False Positive Rate (FPR)** | **0.0%** | **0.0%** |
| **False Negative Rate (FNR)** | **65.1%** | **0.0%** |

### Confusion Matrix Breakdown
* **Formula Only:** TP=22, FP=0, TN=57, FN=41
* **Formula + Escalation:** TP=63, FP=0, TN=57, FN=0

### Per-Attack Detection Rates (Policy B)
- **SYBIL**: 100.0% (14/14 intercepted)
- **STEALTHY_SYBIL**: 100.0% (10/10 intercepted)
- **MALICIOUS_WALLET**: 100.0% (14/14 intercepted)
- **FINNEY**: 100.0% (10/10 intercepted)
- **ECLIPSE**: 100.0% (10/10 intercepted)
- **PARTIAL_ECLIPSE**: 100.0% (5/5 intercepted)

---

## 2. OBSERVATION WINDOW BENCHMARK (SLEEPER NODE DETECTION)

* **Candidate:** `SLEEPER_TEST_01` (Honest at admission, turns malicious at Transaction 5)
* **Window Size:** 10 transactions
* **Detection Status:** **DETECTED**
* **Intercepted at Transaction #:** **5**
* **Detection Latency:** **1 transaction(s)** after attack activation
* **Graduation Status:** Clean Graduation Blocked (Replaced with Administrator Investigation)

---

## 3. POST-ADMISSION CONTINUOUS MONITORING PERFORMANCE

Evaluated against discrete-event multi-miner PoW consensus scenarios:

| Consensus Scenario | Strategy Description | Blocks / Orphans | Alerts Emitted | Detection Latency | Intercepted? |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Honest Baseline** | HONEST | 36 / 0 | 0 | N/A | **YES (Clean)** |
| **Selfish Mining** | SELFISH | 24 / 12 | 4 | 54.1s | **YES** |
| **51% Hashpower Coalition** | COALITION_51 | 22 / 13 | 14 | N/A | **YES** |
| **Block Withholding** | BLOCK_WITHHOLDING | 36 / 0 | 3 | 54.1s | **YES** |
| **Race Double-Spend** | RACE_DOUBLE_SPEND | 36 / 0 | 2 | 973.1s | **YES** |

---

## 4. METHODOLOGY & REPRODUCIBILITY NOTES
* All evaluations are conducted without pre-baked results.
* All calculations conform strictly to the progress report mathematical formulations:
  $$AR = 0.30S + 0.20W + 0.20F + 0.30E$$
  $$PT = 0.25I + 0.20T + 0.20N + 0.20H + 0.15B$$
  $$TF = 0.60PT + 0.40(1 - AR)$$
* Results reflect synthetic discrete-event simulations and local testnet execution.
