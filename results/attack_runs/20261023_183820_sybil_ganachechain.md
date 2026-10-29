# ASTRA Attack Run: Sybil Attack

- **Run started:** 2026-10-23 18:38:19 UTC
- **Blockchain backend:** GanacheChain
- **Candidate:** NODE_SYBIL (`0xdf77fca53a725bbebdae372fe9b8420b4f4ff203`)
- **Ground truth:** ATTACK

## 1. Attack executed

1. One funder wallet creates the candidate plus 3 sibling identities.
2. All 4 identities are funded with an identical 0.2 ETH within about a minute.
3. The identities pass 0.01 ETH around in a closed ring to fake activity.
4. The candidate then requests admission as if it were an independent node.

### On-chain transactions (9)

| Block | Tx hash | From | To | Value (ETH) | Nonce | Status |
| ---: | :--- | :--- | :--- | ---: | ---: | :--- |
| 54 | `5d1b1182025df1...` | 0x90f8bf6a... | 0xdab689aa... | 2.0000 | 3 | SUCCESS |
| 55 | `0906117d034c01...` | 0xdab689aa... | 0xdf77fca5... (CANDIDATE) | 0.2000 | 0 | SUCCESS |
| 57 | `26a72691e6e492...` | 0xdab689aa... | 0xcb19ca94... (cluster) | 0.2000 | 1 | SUCCESS |
| 59 | `7ef1108fd2d94c...` | 0xdab689aa... | 0xc9079a48... (cluster) | 0.2000 | 2 | SUCCESS |
| 61 | `fa2a80ae730f58...` | 0xdab689aa... | 0x451b27f8... (cluster) | 0.2000 | 3 | SUCCESS |
| 63 | `96974aa883673a...` | 0xdf77fca5... (CANDIDATE) | 0xcb19ca94... (cluster) | 0.0100 | 0 | SUCCESS |
| 65 | `1ea932a58d3449...` | 0xcb19ca94... (cluster) | 0xc9079a48... (cluster) | 0.0100 | 0 | SUCCESS |
| 67 | `514cbaf0c45ba0...` | 0xc9079a48... (cluster) | 0x451b27f8... (cluster) | 0.0100 | 0 | SUCCESS |
| 69 | `193a763dca30d1...` | 0x451b27f8... (cluster) | 0xdf77fca5... (CANDIDATE) | 0.0100 | 0 | SUCCESS |

### Peer table (4 peers)

| Peer | IP | ASN | Connection age (days) | Reported height | Backbone |
| :--- | :--- | :--- | ---: | ---: | :--- |
| BACKBONE_000 | 100.0.164.29 | AS15169 | 24.7 | 53 | True |
| BACKBONE_004 | 104.28.109.9 | AS701 | 164.4 | 53 | True |
| BACKBONE_045 | 145.65.40.161 | AS3356 | 26.7 | 53 | True |
| BACKBONE_040 | 140.30.144.138 | AS15169 | 60.9 | 52 | True |

## 2. Agentic AI analysis

Orchestration: LangGraph StateGraph (collect -> 4 agents -> aggregate -> human_review)

Node execution order: collect -> finney_agent -> eclipse_agent -> sybil_agent -> wallet_agent -> aggregate -> human_review

### Sybil Agent - risk 0.89 (CRITICAL)

- Common funder identified: 0xdab689aa... (funded 4 accounts within 24h)
- Layered funding: 0xdab689aa... received its funds from 0x90f8bf6a... within 24h and forwarded them on (pass-through hop).
- Detected 3 sibling account(s) funded with near-identical value (CV=0.00).
- High closed-loop circular transfer ratio: 100.0% of transactions are internal.
- Candidate account is newborn (0.0 days old).

### Wallet Agent - risk 0.15

- Velocity anomaly: 1.0 tx/min is 10.6 robust standard deviations above the network median.

### Finney Agent - risk 0.07

- No conflicting mempool sightings or withheld block propagation anomalies.

### Eclipse Agent - risk 0.18

- Peer connectivity exhibits healthy topological dispersion across multiple ASNs and core backbone.

### Trust computation

- Attack Risk **AR = 0.367** (0.30*S + 0.20*W + 0.20*F + 0.30*E)
- Positive Trust **PT = 0.615** (I=0.39, T=1.00, N=0.74, H=0.33, B=0.70)
- Trust Factor **TF = 0.622** against threshold TV = 0.70
- AI recommendation: **REJECT**
- Escalation flag: **TRIGGERED**
  - Sybil risk 0.89 exceeds escalation threshold (0.75)
  - Sybil agent flagged critical cluster creation

## 3. Administrator decision

- **Action:** REJECT
- **Reason:** Trust Factor (0.62) strictly below threshold TV (0.70)
- **Decided by:** AutoAdminPolicy

**Outcome:** candidate NOT ADMITTED to the network.
