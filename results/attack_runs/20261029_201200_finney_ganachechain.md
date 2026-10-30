# ASTRA Attack Run: Finney Double-Spend Attack

- **Run started:** 2026-10-29 20:11:33 UTC
- **Blockchain backend:** GanacheChain
- **Candidate:** NODE_FINNEY (`0x442bca4c11c6b40be2a4805c555d97a5e37cc868`)
- **Ground truth:** ATTACK

## 1. Attack executed

1. The attacker mines a transfer of 0.4 ETH to its own stash wallet and keeps the block private.
2. It pays a merchant the same 0.4 ETH using the SAME nonce (seen only in the mempool).
3. The withheld block is then published, so the merchant payment can never confirm.

### On-chain transactions (3)

| Block | Tx hash | From | To | Value (ETH) | Nonce | Status |
| ---: | :--- | :--- | :--- | ---: | ---: | :--- |
| 123 | `8ed3a40c02d15e...` | 0x90f8bf6a... | 0x04a6dd36... | 2.0000 | 5 | SUCCESS |
| 125 | `71c3318ea86681...` | 0x04a6dd36... | 0x442bca4c... (CANDIDATE) | 1.5000 | 0 | SUCCESS |
| 126 | `ef038271c5a035...` | 0x442bca4c... (CANDIDATE) | 0x7befd68a... | 0.4000 | 0 | SUCCESS |

### Unconfirmed mempool transactions

- `23d20a2759aa00...` from 0x442bca4c... to 0x43ecf35f...: 0.4 ETH at nonce 0 (mined: False)

### Peer table (7 peers)

| Peer | IP | ASN | Connection age (days) | Reported height | Backbone |
| :--- | :--- | :--- | ---: | ---: | :--- |
| BACKBONE_000 | 100.0.164.29 | AS15169 | 164.4 | 122 | True |
| BACKBONE_004 | 104.28.109.9 | AS701 | 26.7 | 122 | True |
| BACKBONE_045 | 145.65.40.161 | AS3356 | 60.9 | 121 | True |
| BACKBONE_040 | 140.30.144.138 | AS15169 | 50.3 | 122 | True |
| BACKBONE_003 | 103.21.229.140 | AS8075 | 134.4 | 121 | True |
| BACKBONE_014 | 114.98.217.89 | AS701 | 55.1 | 121 | True |
| BACKBONE_048 | 148.86.120.136 | AS32934 | 148.2 | 122 | True |

## 2. Agentic AI analysis

Orchestration: LangGraph StateGraph (collect -> 4 agents -> aggregate -> human_review)

Node execution order: collect -> sybil_agent -> eclipse_agent -> finney_agent -> wallet_agent -> aggregate -> human_review

### Sybil Agent - risk 0.41

- Funded by 0x04a6dd36...; no other accounts funded by this source within 5m.
- High closed-loop circular transfer ratio: 50.0% of transactions are internal.
- Candidate account is newborn (0.0 days old).

### Wallet Agent - risk 0.27

- Velocity anomaly: 1.0 tx/min is 10.6 robust standard deviations above the network median.

### Finney Agent - risk 0.87 (CRITICAL)

- Conflicting nonce 0: Mempool payment to 0x43ecf35f... vs on-chain spend to 0x7befd68a...
- CRITICAL: Conflicting transaction detected with divergent destination address.
- Secret mining pattern: Block mined by candidate held private for 26.0s before broadcast, matching Finney attack profile.

### Eclipse Agent - risk 0.10

- Peer connectivity exhibits healthy topological dispersion across multiple ASNs and core backbone.

### Trust computation

- Attack Risk **AR = 0.381** (0.30*S + 0.20*W + 0.20*F + 0.30*E)
- Positive Trust **PT = 0.572** (I=0.35, T=0.64, N=0.96, H=0.30, B=0.70)
- Trust Factor **TF = 0.591** against threshold TV = 0.70
- AI recommendation: **REJECT**
- Escalation flag: **TRIGGERED**
  - Finney risk 0.87 exceeds escalation threshold (0.75)
  - Finney agent flagged critical double-spend / withholding

## 3. Administrator decision

- **Action:** REJECT
- **Reason:** Administrator rejected the candidate on the agents' evidence.
- **Decided by:** DashboardAdministrator

**Outcome:** candidate NOT ADMITTED to the network.
