"""Per-profile breakdown of the ASTRA pre-admission benchmark (seed 42, n = 120).

Reproduces Table 7 of the chapter. It mirrors EvaluationRunner.run_pre_admission_benchmark
but keeps every record, and it writes nothing to results/.

Run from the project root:
    python paper/eval_breakdown.py              # benchmark protocol: evaluate after all candidates exist
    python paper/eval_breakdown.py --immediate  # sensitivity check: evaluate each candidate on creation
"""
import sys
import statistics
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # project root

from astra.config import DEFAULT_CONFIG
from astra.blockchain.sim_chain import SimChain
from astra.network.peer_registry import PeerRegistry
from astra.network.mempool import MempoolLog
from astra.network.propagation import BlockPropagationLog
from astra.scenarios.generator import ScenarioGenerator
from astra.pre_admission.monitor_agent import MonitorAgent
from astra.pre_admission.types import AdminAction
from astra.admin.policies import AutoAdmin

SEED, N = 42, 120
IMMEDIATE = "--immediate" in sys.argv

TYPES = [("honest", 20), ("honest_power_user", 15), ("honest_single_cloud", 15), ("honest_fee_bumper", 10),
         ("sybil", 15), ("stealthy_sybil", 10), ("malicious_wallet", 15), ("finney", 10),
         ("eclipse", 10), ("partial_eclipse", 5)]

chain = SimChain(seed=SEED)
peer_registry = PeerRegistry(seed=SEED)
mempool_log = MempoolLog()
propagation_log = BlockPropagationLog()
generator = ScenarioGenerator(seed=SEED)
monitor = MonitorAgent(DEFAULT_CONFIG)
generator.populate_background(chain, peer_registry, mempool_log, propagation_log)

admin_formula, admin_escalation = AutoAdmin(use_escalation=False), AutoAdmin(use_escalation=True)
rows = defaultdict(list)


def evaluate(c_type, c):
    ev = monitor.evaluate_candidate(
        candidate_id=c.candidate_id, wallet_address=c.wallet_address, chain=chain,
        peer_profile=c.peer_profile, peer_registry=peer_registry, mempool_log=mempool_log,
        propagation_log=propagation_log, candidate_mined_blocks=c.mined_blocks,
        known_exchanges=generator.exchanges)
    rows[c_type].append(dict(
        label=c.label, tf=ev.tf, ar=ev.ar, pt=ev.pt,
        risks={k: v.risk for k, v in ev.agent_outputs.items()},
        formula=admin_formula.decide(ev).action, escalation=admin_escalation.decide(ev).action))


scale = N / 125.0
candidates, idx = [], 1
for c_type, count in TYPES:
    for _ in range(max(1, int(round(count * scale)))):
        c = generator.create_candidate(c_type, f"CAND_{idx:03d}", chain, peer_registry, mempool_log, propagation_log)
        idx += 1
        if IMMEDIATE:
            evaluate(c_type, c)
        else:
            candidates.append((c_type, c))
for c_type, c in candidates:
    evaluate(c_type, c)

flagged = (AdminAction.REJECT, AdminAction.INVESTIGATE)
totals = {"formula_only": dict(TP=0, FP=0, TN=0, FN=0), "formula_escalation": dict(TP=0, FP=0, TN=0, FN=0)}
print(f"protocol: {'evaluate on creation' if IMMEDIATE else 'evaluate after all candidates exist'}")
print(f"{'profile':22}{'truth':7}{'n':>3} {'TF mean':>8} {'TF min':>7} {'TF max':>7} {'AR':>6} {'PT':>6} "
      f"{'S':>5} {'W':>5} {'F':>5} {'E':>5} | {'A:rej':>5} | {'B:acc':>5} {'B:inv':>5} {'B:rej':>5}")
for c_type, _ in TYPES:
    rs = rows[c_type]
    n = len(rs)
    mean = lambda k: statistics.mean(r[k] for r in rs)
    risk = lambda k: statistics.mean(r["risks"][k] for r in rs)
    a_rej = sum(r["formula"] in flagged for r in rs)
    b_rej = sum(r["escalation"] == AdminAction.REJECT for r in rs)
    b_inv = sum(r["escalation"] == AdminAction.INVESTIGATE for r in rs)
    is_attack = rs[0]["label"] == "ATTACK"
    for key, hit in (("formula_only", a_rej), ("formula_escalation", b_rej + b_inv)):
        totals[key]["TP" if is_attack else "FP"] += hit
        totals[key]["FN" if is_attack else "TN"] += n - hit
    print(f"{c_type:22}{rs[0]['label']:7}{n:>3} {mean('tf'):>8.3f} {min(r['tf'] for r in rs):>7.3f} "
          f"{max(r['tf'] for r in rs):>7.3f} {mean('ar'):>6.3f} {mean('pt'):>6.3f} "
          f"{risk('Sybil'):>5.2f} {risk('Wallet'):>5.2f} {risk('Finney'):>5.2f} {risk('Eclipse'):>5.2f} | "
          f"{a_rej:>5} | {n - b_rej - b_inv:>5} {b_inv:>5} {b_rej:>5}")
for key, m in totals.items():
    print(key, m)
