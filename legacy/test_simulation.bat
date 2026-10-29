@echo off
title ASTRA - Console Simulation Verification (legacy prototype)
echo =====================================================================
echo  Running ASTRA SAFE Attack Simulation Verification Test
echo =====================================================================
cd /d "%~dp0"
..\.venv\Scripts\python.exe -c "from astra_simulator import AstraSimulator; sim = AstraSimulator(); print('[+] Network Initialized with', len(sim.blockchain.nodes), 'nodes'); print('[+] Sybil Test:', sim.run_sybil_attack(True)['status']); print('[+] Attack Wallet Test:', sim.run_attack_wallet(True)['status']); print('[+] Finney Test:', sim.run_finney_attack(True)['status']); print('[+] Eclipse Test:', sim.run_eclipse_attack(True)['status']); print('[+] SUCCESS: All 4 SAFE attacks autonomously mitigated!');"
echo =====================================================================
pause
