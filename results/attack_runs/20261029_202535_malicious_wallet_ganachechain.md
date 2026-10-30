# ASTRA Attack Run: Malicious Wallet (Spam / DoS) Attack

- **Run started:** 2026-10-29 20:23:52 UTC
- **Blockchain backend:** GanacheChain
- **Candidate:** NODE_MALICIOUS_WALLET (`0xc2b88b6e7fa0a99d36fe5a395715cd15874d142e`)
- **Ground truth:** ATTACK

## 1. Attack executed

1. A fresh wallet is funded with 1.0 ETH.
2. It fires 8 transactions less than 5 seconds apart (bot burst).
3. Every transfer is a 0.0001 ETH dust payment to a small set of fresh addresses.
4. Half of the transactions are sent so that they revert on-chain.

### On-chain transactions (10)

| Block | Tx hash | From | To | Value (ETH) | Nonce | Status |
| ---: | :--- | :--- | :--- | ---: | ---: | :--- |
| 181 | `264c074e1f7ced...` | 0x90f8bf6a... | 0xded2959f... | 1.5000 | 7 | SUCCESS |
| 182 | `0e3cca27fc0218...` | 0xded2959f... | 0xc2b88b6e... (CANDIDATE) | 1.0000 | 0 | SUCCESS |
| 184 | `6f6d64a0688d17...` | 0xc2b88b6e... (CANDIDATE) | 0x92f0627c... | 0.0001 | 0 | SUCCESS |
| 186 | `ddeb56b25805c5...` | 0xc2b88b6e... (CANDIDATE) | 0x9561c133... | 0.0001 | 1 | REVERTED |
| 188 | `16aabe6eaf8002...` | 0xc2b88b6e... (CANDIDATE) | 0x208594e4... | 0.0001 | 2 | SUCCESS |
| 190 | `aa8f6d7184b62f...` | 0xc2b88b6e... (CANDIDATE) | 0x9561c133... | 0.0001 | 3 | REVERTED |
| 192 | `03c05c8c215a6f...` | 0xc2b88b6e... (CANDIDATE) | 0x92f0627c... | 0.0001 | 4 | SUCCESS |
| 194 | `009c45aa47fc50...` | 0xc2b88b6e... (CANDIDATE) | 0x9561c133... | 0.0001 | 5 | REVERTED |
| 196 | `8cf7a2109bbe9d...` | 0xc2b88b6e... (CANDIDATE) | 0x95e2bdc7... | 0.0001 | 6 | SUCCESS |
| 198 | `53fc73038f95dd...` | 0xc2b88b6e... (CANDIDATE) | 0x9561c133... | 0.0001 | 7 | REVERTED |

### Peer table (6 peers)

| Peer | IP | ASN | Connection age (days) | Reported height | Backbone |
| :--- | :--- | :--- | ---: | ---: | :--- |
| BACKBONE_000 | 100.0.164.29 | AS15169 | 26.1 | 180 | True |
| BACKBONE_004 | 104.28.109.9 | AS701 | 156.8 | 180 | True |
| BACKBONE_045 | 145.65.40.161 | AS3356 | 99.8 | 180 | True |
| BACKBONE_040 | 140.30.144.138 | AS15169 | 125.4 | 180 | True |
| BACKBONE_003 | 103.21.229.140 | AS8075 | 104.0 | 179 | True |
| BACKBONE_014 | 114.98.217.89 | AS701 | 55.1 | 179 | True |

## 2. Agentic AI analysis

Orchestration: LangGraph StateGraph (collect -> 4 agents -> aggregate -> human_review)

Node execution order: collect -> finney_agent -> sybil_agent -> eclipse_agent -> wallet_agent -> aggregate -> human_review

### Sybil Agent - risk 0.43

- Funded by 0xded2959f...; no other accounts funded by this source within 24h.
- Layered funding: 0xded2959f... received its funds from 0x90f8bf6a... within 24h and forwarded them on (pass-through hop).
- Candidate account is newborn (0.0 days old).

### Wallet Agent - risk 0.92

- Abnormal burst execution: 100.0% of transactions sent <10s apart.
- Dusting pattern detected: 100.0% of transactions <0.001 ETH.
- High failure rate: 50.0% of transactions reverted on-chain.
- Automated pattern: 8 transactions with exact identical values.
- Velocity anomaly: 19.2 tx/min is 220.3 robust standard deviations above the network median.

### Finney Agent - risk 0.07

- No conflicting mempool sightings or withheld block propagation anomalies.

### Eclipse Agent - risk 0.10

- Peer connectivity exhibits healthy topological dispersion across multiple ASNs and core backbone.

### Trust computation

- Attack Risk **AR = 0.356** (0.30*S + 0.20*W + 0.20*F + 0.30*E)
- Positive Trust **PT = 0.670** (I=0.35, T=0.60, N=0.91, H=0.65, B=1.00)
- Trust Factor **TF = 0.660** against threshold TV = 0.70
- AI recommendation: **REJECT**
- Escalation flag: **TRIGGERED**
  - Wallet risk 0.92 exceeds escalation threshold (0.75)

## 3. Administrator decision

- **Action:** REJECT
- **Reason:** Administrator rejected the candidate on the agents' evidence.
- **Decided by:** DashboardAdministrator

**Outcome:** candidate NOT ADMITTED to the network.
