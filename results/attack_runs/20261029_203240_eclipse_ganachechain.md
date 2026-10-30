# ASTRA Attack Run: Eclipse Attack

- **Run started:** 2026-10-29 20:32:06 UTC
- **Blockchain backend:** GanacheChain
- **Candidate:** NODE_ECLIPSE (`0x34600c5b3b387f5516cb123711db68cf940eac30`)
- **Ground truth:** ATTACK

## 1. Attack executed

1. The candidate's wallet history is ordinary (funded by an exchange).
2. All 8 of its peer connections sit in one attacker-controlled ASN (AS99999_BOTNET).
3. Those peers are freshly connected and report a chain tip 12 blocks behind.

### On-chain transactions (1)

| Block | Tx hash | From | To | Value (ETH) | Nonce | Status |
| ---: | :--- | :--- | :--- | ---: | ---: | :--- |
| 253 | `b4d2f02f8b716d...` | 0xf44fb582... (exchange) | 0x34600c5b... (CANDIDATE) | 1.0000 | 6 | SUCCESS |

### Peer table (8 peers)

| Peer | IP | ASN | Connection age (days) | Reported height | Backbone |
| :--- | :--- | :--- | ---: | ---: | :--- |
| ATTACKER_PEER_00 | 198.51.100.10 | AS99999_BOTNET | 0.0 | 239 | False |
| ATTACKER_PEER_01 | 198.51.100.11 | AS99999_BOTNET | 1.1 | 239 | False |
| ATTACKER_PEER_02 | 198.51.100.12 | AS99999_BOTNET | 0.1 | 239 | False |
| ATTACKER_PEER_03 | 198.51.100.13 | AS99999_BOTNET | 0.1 | 239 | False |
| ATTACKER_PEER_04 | 198.51.100.14 | AS99999_BOTNET | 0.1 | 239 | False |
| ATTACKER_PEER_05 | 198.51.100.15 | AS99999_BOTNET | 0.5 | 239 | False |
| ATTACKER_PEER_06 | 198.51.100.16 | AS99999_BOTNET | 0.8 | 239 | False |
| ATTACKER_PEER_07 | 198.51.100.17 | AS99999_BOTNET | 0.4 | 239 | False |

## 2. Agentic AI analysis

Orchestration: LangGraph StateGraph (collect -> 4 agents -> aggregate -> human_review)

Node execution order: collect -> finney_agent -> eclipse_agent -> sybil_agent -> wallet_agent -> aggregate -> human_review

### Sybil Agent - risk 0.20

- Funded by known exchange hub 0xf44fb582...; funding-graph clustering not applicable.
- Candidate account is newborn (0.0 days old).

### Wallet Agent - risk 0.04

- Account has no abnormal transaction history.

### Finney Agent - risk 0.07

- No conflicting mempool sightings or withheld block propagation anomalies.

### Eclipse Agent - risk 0.92 (CRITICAL)

- Severe peer ASN concentration: HHI=1.00 across only 1 autonomous system(s).
- Routing table takeover: 100% of peers sit in unverified ASN AS99999_BOTNET and 100% of connections are under 2 days old.
- Critical backbone isolation: only 0.0% of peers connect to honest core.
- NetworkX routing vulnerability: only 0 node-disjoint path(s) to honest backbone.
- Coordinated peer churn: 8 of 8 connections established within the past 2 days.
- Partitioned view: 100.0% of peers report stale block heights lagging consensus tip.

### Trust computation

- Attack Risk **AR = 0.359** (0.30*S + 0.20*W + 0.20*F + 0.30*E)
- Positive Trust **PT = 0.547** (I=0.47, T=0.91, N=0.44, H=0.28, B=0.70)
- Trust Factor **TF = 0.585** against threshold TV = 0.70
- AI recommendation: **REJECT**
- Escalation flag: **TRIGGERED**
  - Eclipse risk 0.92 exceeds escalation threshold (0.75)
  - Eclipse agent flagged critical routing table monopoly

## 3. Administrator decision

- **Action:** REJECT
- **Reason:** Administrator rejected the candidate on the agents' evidence.
- **Decided by:** DashboardAdministrator

**Outcome:** candidate NOT ADMITTED to the network.
