# ASTRA Attack Run: Malicious Wallet (Spam / DoS) Attack

- **Run started:** 2026-10-23 18:38:21 UTC
- **Blockchain backend:** GanacheChain
- **Candidate:** NODE_MALICIOUS_WALLET (`0x05f9ba53a1e33678b8015764a88c28b114b96e86`)
- **Ground truth:** ATTACK

## 1. Attack executed

1. A fresh wallet is funded with 1.0 ETH.
2. It fires 8 transactions less than 5 seconds apart (bot burst).
3. Every transfer is a 0.0001 ETH dust payment to a small set of fresh addresses.
4. Half of the transactions are sent so that they revert on-chain.

### On-chain transactions (10)

| Block | Tx hash | From | To | Value (ETH) | Nonce | Status |
| ---: | :--- | :--- | :--- | ---: | ---: | :--- |
| 123 | `a4b3fb5af3f3f1...` | 0x90f8bf6a... | 0x360da896... | 1.5000 | 5 | SUCCESS |
| 124 | `f6306b2bfe117e...` | 0x360da896... | 0x05f9ba53... (CANDIDATE) | 1.0000 | 0 | SUCCESS |
| 126 | `6413991cdebbfc...` | 0x05f9ba53... (CANDIDATE) | 0xab7a9516... | 0.0001 | 0 | SUCCESS |
| 128 | `8c219428ce3d08...` | 0x05f9ba53... (CANDIDATE) | 0xc89ce473... | 0.0001 | 1 | REVERTED |
| 130 | `f04020acfcdd04...` | 0x05f9ba53... (CANDIDATE) | 0x00fab265... | 0.0001 | 2 | SUCCESS |
| 132 | `1605bbf0905904...` | 0x05f9ba53... (CANDIDATE) | 0xc89ce473... | 0.0001 | 3 | REVERTED |
| 134 | `5b6802e075b10e...` | 0x05f9ba53... (CANDIDATE) | 0xab7a9516... | 0.0001 | 4 | SUCCESS |
| 136 | `0b6bd86158e642...` | 0x05f9ba53... (CANDIDATE) | 0xc89ce473... | 0.0001 | 5 | REVERTED |
| 138 | `d01ef6cf7c2da7...` | 0x05f9ba53... (CANDIDATE) | 0xf2fca807... | 0.0001 | 6 | SUCCESS |
| 140 | `dc1a25771de2d1...` | 0x05f9ba53... (CANDIDATE) | 0xc89ce473... | 0.0001 | 7 | REVERTED |

### Peer table (6 peers)

| Peer | IP | ASN | Connection age (days) | Reported height | Backbone |
| :--- | :--- | :--- | ---: | ---: | :--- |
| BACKBONE_000 | 100.0.164.29 | AS15169 | 26.1 | 122 | True |
| BACKBONE_004 | 104.28.109.9 | AS701 | 156.8 | 122 | True |
| BACKBONE_045 | 145.65.40.161 | AS3356 | 99.8 | 122 | True |
| BACKBONE_040 | 140.30.144.138 | AS15169 | 125.4 | 122 | True |
| BACKBONE_003 | 103.21.229.140 | AS8075 | 104.0 | 121 | True |
| BACKBONE_014 | 114.98.217.89 | AS701 | 55.1 | 121 | True |

## 2. Agentic AI analysis

Orchestration: LangGraph StateGraph (collect -> 4 agents -> aggregate -> human_review)

Node execution order: collect -> finney_agent -> eclipse_agent -> sybil_agent -> wallet_agent -> aggregate -> human_review

### Sybil Agent - risk 0.43

- Funded by 0x360da896...; no other accounts funded by this source within 24h.
- Layered funding: 0x360da896... received its funds from 0x90f8bf6a... within 24h and forwarded them on (pass-through hop).
- Candidate account is newborn (0.0 days old).

### Wallet Agent - risk 0.92

- Abnormal burst execution: 100.0% of transactions sent <10s apart.
- Dusting pattern detected: 100.0% of transactions <0.001 ETH.
- High failure rate: 50.0% of transactions reverted on-chain.
- Automated pattern: 8 transactions with exact identical values.
- Velocity anomaly: 32.0 tx/min is 367.7 robust standard deviations above the network median.

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
- **Reason:** Trust Factor (0.66) strictly below threshold TV (0.70)
- **Decided by:** AutoAdminPolicy

**Outcome:** candidate NOT ADMITTED to the network.
