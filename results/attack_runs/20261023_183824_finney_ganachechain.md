# ASTRA Attack Run: Finney Double-Spend Attack

- **Run started:** 2026-10-23 18:38:23 UTC
- **Blockchain backend:** GanacheChain
- **Candidate:** NODE_FINNEY (`0x27ed6119588a590c10d6e7b7abc519842ae9dc99`)
- **Ground truth:** ATTACK

## 1. Attack executed

1. The attacker mines a transfer of 0.4 ETH to its own stash wallet and keeps the block private.
2. It pays a merchant the same 0.4 ETH using the SAME nonce (seen only in the mempool).
3. The withheld block is then published, so the merchant payment can never confirm.

### On-chain transactions (3)

| Block | Tx hash | From | To | Value (ETH) | Nonce | Status |
| ---: | :--- | :--- | :--- | ---: | ---: | :--- |
| 194 | `8b1e258e8145aa...` | 0x90f8bf6a... | 0xd119bdb7... | 2.0000 | 7 | SUCCESS |
| 196 | `9ea79aa6fa5996...` | 0xd119bdb7... | 0x27ed6119... (CANDIDATE) | 1.5000 | 0 | SUCCESS |
| 197 | `04ac985ba85a5f...` | 0x27ed6119... (CANDIDATE) | 0xeec6c5b2... | 0.4000 | 0 | SUCCESS |

### Unconfirmed mempool transactions

- `0f324ac922d0f3...` from 0x27ed6119... to 0x813c8cd9...: 0.4 ETH at nonce 0 (mined: False)

### Peer table (7 peers)

| Peer | IP | ASN | Connection age (days) | Reported height | Backbone |
| :--- | :--- | :--- | ---: | ---: | :--- |
| BACKBONE_000 | 100.0.164.29 | AS15169 | 164.4 | 193 | True |
| BACKBONE_004 | 104.28.109.9 | AS701 | 26.7 | 193 | True |
| BACKBONE_045 | 145.65.40.161 | AS3356 | 60.9 | 192 | True |
| BACKBONE_040 | 140.30.144.138 | AS15169 | 50.3 | 193 | True |
| BACKBONE_003 | 103.21.229.140 | AS8075 | 134.4 | 192 | True |
| BACKBONE_014 | 114.98.217.89 | AS701 | 55.1 | 192 | True |
| BACKBONE_048 | 148.86.120.136 | AS32934 | 148.2 | 193 | True |

## 2. Agentic AI analysis

Orchestration: LangGraph StateGraph (collect -> 4 agents -> aggregate -> human_review)

Node execution order: collect -> finney_agent -> eclipse_agent -> sybil_agent -> wallet_agent -> aggregate -> human_review

### Sybil Agent - risk 0.41

- Funded by 0xd119bdb7...; no other accounts funded by this source within 5m.
- High closed-loop circular transfer ratio: 50.0% of transactions are internal.
- Candidate account is newborn (0.0 days old).

### Wallet Agent - risk 0.27

- Velocity anomaly: 1.0 tx/min is 8.5 robust standard deviations above the network median.

### Finney Agent - risk 0.87 (CRITICAL)

- Conflicting nonce 0: Mempool payment to 0x813c8cd9... vs on-chain spend to 0xeec6c5b2...
- CRITICAL: Conflicting transaction detected with divergent destination address.
- Secret mining pattern: Block mined by candidate held private for 25.0s before broadcast, matching Finney attack profile.

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
- **Reason:** Trust Factor (0.59) strictly below threshold TV (0.70)
- **Decided by:** AutoAdminPolicy

**Outcome:** candidate NOT ADMITTED to the network.
