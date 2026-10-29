"""
ASTRA: Autonomous Security and Threat Response using Agentic AI for Blockchain
Module: web_server.py
Interactive Live Visual Arena & Simulation Testbed
Provides full visual step-by-step animation of Node Admission, SAFE Attacks,
Agent Scanners, Trust Factor Calculation, and Autonomous Prevention.
"""

import http.server
import socketserver
import json
import urllib.parse
import os
import sys

# Ensure agentic_blockchain_security submodules are discoverable
current_dir = os.path.dirname(os.path.abspath(__file__))
sub_dir = os.path.join(current_dir, "agentic_blockchain_security")
if sub_dir not in sys.path:
    sys.path.insert(0, sub_dir)

# Import core modules
from astra_simulator import AstraSimulator
from workflow.graph import AdmissionWorkflowGraph
from node_join import get_sample_join_requests

PORT = 8501
sim = AstraSimulator()
admission_graph = AdmissionWorkflowGraph(tv_threshold=0.70)

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ASTRA - Live Visual Node Admission Security</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background-color: #080c14; color: #f3f4f6; font-family: 'Segoe UI', system-ui, sans-serif; }
        .cyber-card { background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; }
        .gate-pulse { animation: gateGlow 2s infinite alternate; }
        @keyframes gateGlow {
            from { box-shadow: 0 0 10px rgba(0, 210, 255, 0.2); border-color: #0284c7; }
            to { box-shadow: 0 0 25px rgba(0, 230, 118, 0.4); border-color: #10b981; }
        }
        .step-active { border-color: #38bdf8 !important; background: rgba(14, 165, 233, 0.15) !important; color: #38bdf8 !important; }
        .gauge-bar { transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1); }
    </style>
</head>
<body class="min-h-screen p-4 md:p-6 select-none">

    <!-- Top Academic Header -->
    <header class="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-start md:items-center pb-5 border-b border-gray-800 gap-4">
        <div class="flex items-center gap-3">
            <div class="w-11 h-11 bg-cyan-950 text-cyan-400 rounded-xl flex items-center justify-center text-2xl border border-cyan-800 shadow-lg shadow-cyan-950/50">
                <i class="fa-solid fa-shield-halved"></i>
            </div>
            <div>
                <h1 class="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 via-teal-300 to-emerald-400 bg-clip-text text-transparent">
                    ASTRA: Node Admission Security Arena
                </h1>
                <p class="text-xs text-gray-400 font-medium">
                    Autonomous Multi-Agent Pre-Admission Trust Verification | Minor Project Evaluation Prototype
                </p>
            </div>
        </div>
        <div class="flex flex-col md:items-end text-xs text-gray-300 bg-gray-900/90 px-4 py-2.5 rounded-xl border border-gray-800">
            <div><span class="text-gray-500">Student Team:</span> <strong class="text-white">Dhruv Basia</strong> & <strong class="text-white">Amisha Rawat</strong></div>
            <div><span class="text-gray-500">Supervisor:</span> <span class="text-emerald-400 font-semibold">Prof. Rahul Johari</span> | USAR, GGSIPU</div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto mt-6 space-y-6">

        <!-- Controls: Pick Scenario & Watch Live Simulation -->
        <div class="cyber-card p-5 border-cyan-900/50">
            <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
                <div>
                    <h2 class="text-base font-bold text-white flex items-center gap-2">
                        <i class="fa-solid fa-play text-cyan-400"></i>
                        Live Visual Simulation: Select Node to Attempt Admission
                    </h2>
                    <p class="text-xs text-gray-400 mt-0.5">
                        Watch how prospective nodes are intercepted at the gateway, scanned by the 4 agents, and evaluated before ever touching the blockchain.
                    </p>
                </div>
                <div class="flex items-center gap-2 bg-gray-950 px-3 py-1.5 rounded-lg border border-gray-800">
                    <span class="text-xs font-semibold text-gray-400">Mode:</span>
                    <label class="flex items-center gap-1.5 cursor-pointer text-xs">
                        <input type="checkbox" id="defenseToggle" checked class="w-4 h-4 text-emerald-500 rounded bg-gray-800 border-gray-700 focus:ring-0">
                        <span id="defenseToggleText" class="font-bold text-emerald-400">ASTRA Protected (With AI)</span>
                    </label>
                </div>
            </div>

            <!-- Action Buttons for the 5 scenarios -->
            <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                <button onclick="startSimulation('HONEST')" class="p-3 bg-gray-900 hover:bg-emerald-950/60 border border-emerald-900/50 hover:border-emerald-500 rounded-xl text-left transition group">
                    <div class="flex justify-between items-center">
                        <span class="text-xs font-bold text-emerald-400 group-hover:text-emerald-300">1. Honest Node</span>
                        <i class="fa-solid fa-check-circle text-emerald-500 text-sm"></i>
                    </div>
                    <div class="text-[11px] text-gray-400 mt-1">High stake (25 ETH), 60d age, diverse peers</div>
                </button>

                <button onclick="startSimulation('SYBIL')" class="p-3 bg-gray-900 hover:bg-red-950/60 border border-red-900/50 hover:border-red-500 rounded-xl text-left transition group">
                    <div class="flex justify-between items-center">
                        <span class="text-xs font-bold text-red-400 group-hover:text-red-300">2. Sybil Attack (S)</span>
                        <i class="fa-solid fa-users text-red-500 text-sm"></i>
                    </div>
                    <div class="text-[11px] text-gray-400 mt-1">1-day newborn identity, 0.1 ETH stake, subnet clone</div>
                </button>

                <button onclick="startSimulation('ATTACK_WALLET')" class="p-3 bg-gray-900 hover:bg-amber-950/60 border border-amber-900/50 hover:border-amber-500 rounded-xl text-left transition group">
                    <div class="flex justify-between items-center">
                        <span class="text-xs font-bold text-amber-400 group-hover:text-amber-300">3. Attack Wallet (A)</span>
                        <i class="fa-solid fa-wallet text-amber-500 text-sm"></i>
                    </div>
                    <div class="text-[11px] text-gray-400 mt-1">Burst spam (85 tx/min, 45% fail rate, DoS)</div>
                </button>

                <button onclick="startSimulation('FINNEY')" class="p-3 bg-gray-900 hover:bg-purple-950/60 border border-purple-900/50 hover:border-purple-500 rounded-xl text-left transition group">
                    <div class="flex justify-between items-center">
                        <span class="text-xs font-bold text-purple-400 group-hover:text-purple-300">4. Finney Attack (F)</span>
                        <i class="fa-solid fa-cubes text-purple-500 text-sm"></i>
                    </div>
                    <div class="text-[11px] text-gray-400 mt-1">Secret block withholding + conflicting double-spend</div>
                </button>

                <button onclick="startSimulation('ECLIPSE')" class="p-3 bg-gray-900 hover:bg-sky-950/60 border border-sky-900/50 hover:border-sky-500 rounded-xl text-left transition group">
                    <div class="flex justify-between items-center">
                        <span class="text-xs font-bold text-sky-400 group-hover:text-sky-300">5. Eclipse Attack (E)</span>
                        <i class="fa-solid fa-circle-nodes text-sky-500 text-sm"></i>
                    </div>
            <!-- Live Web3 / Ganache Telemetry Inspector Bar -->
            <div class="mt-4 p-3 bg-gray-950 rounded-xl border border-cyan-900/60 flex flex-col md:flex-row justify-between items-start md:items-center gap-3 text-xs">
                <div class="flex items-center gap-2">
                    <span class="w-3 h-3 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span class="font-bold text-gray-200">Web3.py Connection:</span>
                    <span id="rpcStatusText" class="font-mono text-emerald-400 font-semibold">Ganache RPC (http://127.0.0.1:7545) • Block #1</span>
                </div>
                <div class="flex flex-wrap items-center gap-4 text-gray-400 text-[11px]">
                    <div>Wallet: <span id="onchainAddress" class="font-mono text-cyan-300 font-bold">Select a node above</span></div>
                    <div>On-Chain Balance: <span id="onchainBalance" class="font-mono text-emerald-400 font-bold">-- ETH</span></div>
                    <div>On-Chain Nonce: <span id="onchainNonce" class="font-mono text-amber-300 font-bold">-- txs</span></div>
                </div>
            </div>
        </div>

        <!-- VISUAL ARENA CANVAS & PIPELINE TRACKER -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            <!-- Left 8 Cols: Graphic Stage (Outside -> Gate -> Inside Network) -->
            <div class="lg:col-span-8 space-y-4">
                <div class="cyber-card p-4 relative overflow-hidden">
                    <div class="flex justify-between items-center mb-3">
                        <span class="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-2">
                            <i class="fa-solid fa-network-wired text-cyan-400"></i> P2P Topology & Admission Gateway
                        </span>
                        <span id="simulationStatus" class="text-xs px-2.5 py-1 rounded-full font-semibold bg-gray-800 text-gray-300">
                            Ready • Click an attack scenario above
                        </span>
                    </div>

                    <!-- Canvas Stage -->
                    <div class="relative bg-gray-950 rounded-xl border border-gray-800 p-2 overflow-hidden h-[330px]">
                        <canvas id="arenaCanvas" width="750" height="320" class="w-full h-full"></canvas>
                        
                        <!-- Overlay Gate Indicator -->
                        <div class="absolute top-3 left-1/2 -translate-x-1/2 flex items-center gap-1.5 bg-gray-900/80 backdrop-blur px-3 py-1 rounded-full border border-cyan-800 text-[11px] text-cyan-300">
                            <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
                            ASTRA Multi-Agent Perimeter Gate
                        </div>

                        <!-- Result Stamp Overlay -->
                        <div id="stampBanner" class="hidden absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 px-6 py-3 rounded-xl font-black text-xl border-2 shadow-2xl backdrop-blur-md transform scale-110 transition duration-300">
                        </div>
                    </div>

                    <!-- Visual Legend -->
                    <div class="flex flex-wrap justify-between items-center mt-3 pt-3 border-t border-gray-800/80 text-xs text-gray-400">
                        <div class="flex items-center gap-4">
                            <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-emerald-400"></span> Honest Consensus Node</span>
                            <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-cyan-400"></span> Joining Candidate</span>
                            <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-red-500"></span> Blocked / Attacker</span>
                        </div>
                        <span class="text-gray-500 text-[11px]">Real-Time P2P Packet Telemetry</span>
                    </div>
                </div>

                <!-- 5-Stage Step-by-Step Execution Pipeline Tracker -->
                <div class="cyber-card p-4">
                    <div class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
                        <i class="fa-solid fa-timeline text-cyan-400 mr-1.5"></i> Step-by-Step Autonomous Workflow (What happens under the hood)
                    </div>
                    <div class="grid grid-cols-5 gap-2 text-center text-xs">
                        <div id="step1" class="p-2.5 bg-gray-900 rounded-lg border border-gray-800 transition">
                            <div class="font-bold text-[11px]">1. Ingestion</div>
                            <div class="text-[10px] text-gray-400 mt-0.5">Monitor Agent</div>
                        </div>
                        <div id="step2" class="p-2.5 bg-gray-900 rounded-lg border border-gray-800 transition">
                            <div class="font-bold text-[11px]">2. SAFE Audit</div>
                            <div class="text-[10px] text-gray-400 mt-0.5">4 Risk Agents</div>
                        </div>
                        <div id="step3" class="p-2.5 bg-gray-900 rounded-lg border border-gray-800 transition">
                            <div class="font-bold text-[11px]">3. Positive Trust</div>
                            <div class="text-[10px] text-gray-400 mt-0.5">I, T, N, H, B</div>
                        </div>
                        <div id="step4" class="p-2.5 bg-gray-900 rounded-lg border border-gray-800 transition">
                            <div class="font-bold text-[11px]">4. Trust Factor</div>
                            <div class="text-[10px] text-gray-400 mt-0.5">TF vs TV (0.70)</div>
                        </div>
                        <div id="step5" class="p-2.5 bg-gray-900 rounded-lg border border-gray-800 transition">
                            <div class="font-bold text-[11px]">5. Enforcement</div>
                            <div class="text-[10px] text-gray-400 mt-0.5">ADMIT / REJECT</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Right 4 Cols: Live Diagnostics & Agent Risk Gauges -->
            <div class="lg:col-span-4 space-y-4">
                
                <!-- Live Trust Factor & Decision Box -->
                <div class="cyber-card p-5">
                    <div class="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2 flex justify-between items-center">
                        <span>Final Admission Decision</span>
                        <span id="decisionBadge" class="px-2 py-0.5 rounded text-[11px] font-black bg-gray-800 text-gray-400">PENDING</span>
                    </div>

                    <!-- Trust Factor Big Score Display -->
                    <div class="mt-4 p-4 bg-gray-950 rounded-xl border border-gray-800 text-center">
                        <div class="text-xs text-gray-400">Computed Trust Factor (TF)</div>
                        <div id="scoreTF" class="text-4xl font-black text-white mt-1">--</div>
                        <div class="text-xs text-gray-500 mt-1">Threshold: <b class="text-cyan-400">TV = 0.70</b></div>
                        
                        <!-- Comparison Bar -->
                        <div class="w-full bg-gray-800 h-2.5 rounded-full mt-3 overflow-hidden relative">
                            <div id="barTF" class="bg-gradient-to-r from-red-500 via-amber-400 to-emerald-400 h-full w-0 transition-all duration-700"></div>
                            <!-- Threshold Marker at 70% -->
                            <div class="absolute top-0 bottom-0 left-[70%] w-0.5 bg-white shadow-lg"></div>
                        </div>
                    </div>

                    <!-- Individual Attack Risk Gauges (The 4 Agents) -->
                    <div class="mt-4 space-y-2.5">
                        <div class="text-xs font-semibold text-gray-400 uppercase">Specialized Attack Risk Scores:</div>
                        
                        <!-- Sybil -->
                        <div>
                            <div class="flex justify-between text-xs mb-1">
                                <span class="text-gray-300">Sybil Risk (SR)</span>
                                <span id="valSR" class="font-mono font-bold text-gray-400">--</span>
                            </div>
                            <div class="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                                <div id="barSR" class="bg-red-500 h-full w-0 gauge-bar"></div>
                            </div>
                        </div>

                        <!-- Wallet -->
                        <div>
                            <div class="flex justify-between text-xs mb-1">
                                <span class="text-gray-300">Attack Wallet Risk (WR)</span>
                                <span id="valWR" class="font-mono font-bold text-gray-400">--</span>
                            </div>
                            <div class="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                                <div id="barWR" class="bg-amber-500 h-full w-0 gauge-bar"></div>
                            </div>
                        </div>

                        <!-- Finney -->
                        <div>
                            <div class="flex justify-between text-xs mb-1">
                                <span class="text-gray-300">Finney Double-Spend (FR)</span>
                                <span id="valFR" class="font-mono font-bold text-gray-400">--</span>
                            </div>
                            <div class="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                                <div id="barFR" class="bg-purple-500 h-full w-0 gauge-bar"></div>
                            </div>
                        </div>

                        <!-- Eclipse -->
                        <div>
                            <div class="flex justify-between text-xs mb-1">
                                <span class="text-gray-300">Eclipse Isolation Risk (ER)</span>
                                <span id="valER" class="font-mono font-bold text-gray-400">--</span>
                            </div>
                            <div class="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                                <div id="barER" class="bg-sky-500 h-full w-0 gauge-bar"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Critical Override Indicator -->
                    <div id="overrideBox" class="hidden mt-3 p-2 bg-red-950/70 border border-red-700/60 rounded-lg text-xs text-red-300 font-semibold flex items-center gap-1.5">
                        <i class="fa-solid fa-triangle-exclamation text-red-400"></i>
                        <span>CRITICAL ATTACK OVERRIDE ACTIVATED (&ge; 0.90)</span>
                    </div>

                </div>

                <!-- Explainable Agent Log Box -->
                <div class="cyber-card p-4">
                    <div class="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2 flex items-center gap-1.5">
                        <i class="fa-solid fa-brain text-purple-400"></i> Agent Explanation
                    </div>
                    <div id="explanationText" class="text-xs text-gray-300 bg-gray-950 p-3 rounded-lg border border-gray-800 leading-relaxed min-h-[90px]">
                        Select a node scenario above to begin the multi-agent diagnostic run.
                    </div>
                </div>

            </div>

        </div>

    </main>

    <script>
        // Sample Node Telemetry matching Section 33 Benchmark
        const scenarios = {
            "HONEST": {
                node_id: "NODE_HONEST_01",
                wallet_address: "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1",
                identity_age_days: 65,
                transaction_count: 140,
                peer_count: 8,
                stake_eth: 30.0,
                ip_subnet: "192.168.10.0/24",
                asn: "AS15169",
                recent_tx_frequency_per_min: 1.2,
                failed_tx_ratio: 0.01,
                has_conflicting_spends: false,
                withholding_block_flag: false,
                peer_diversity_score: 0.90,
                suspicious_peer_ratio: 0.0
            },
            "SYBIL": {
                node_id: "NODE_SYBIL_01",
                wallet_address: "0x1111111111111111111111111111111111111111",
                identity_age_days: 1,
                transaction_count: 2,
                peer_count: 2,
                stake_eth: 0.1,
                ip_subnet: "198.51.100.0/24",
                asn: "AS9999_HOSTING",
                recent_tx_frequency_per_min: 0.5,
                failed_tx_ratio: 0.0,
                has_conflicting_spends: false,
                withholding_block_flag: false,
                peer_diversity_score: 0.25,
                suspicious_peer_ratio: 0.1
            },
            "ATTACK_WALLET": {
                node_id: "NODE_WALLET_RISK_01",
                wallet_address: "0x2222222222222222222222222222222222222222",
                identity_age_days: 50,
                transaction_count: 8000,
                peer_count: 6,
                stake_eth: 12.0,
                ip_subnet: "172.16.20.0/24",
                asn: "AS16509",
                recent_tx_frequency_per_min: 95.0,
                failed_tx_ratio: 0.50,
                has_conflicting_spends: false,
                withholding_block_flag: false,
                peer_diversity_score: 0.80,
                suspicious_peer_ratio: 0.0
            },
            "FINNEY": {
                node_id: "NODE_FINNEY_RISK_01",
                wallet_address: "0x3333333333333333333333333333333333333333",
                identity_age_days: 35,
                transaction_count: 75,
                peer_count: 5,
                stake_eth: 20.0,
                ip_subnet: "198.51.100.22/24",
                asn: "AS396982",
                recent_tx_frequency_per_min: 1.5,
                failed_tx_ratio: 0.01,
                has_conflicting_spends: true,
                withholding_block_flag: true,
                peer_diversity_score: 0.85,
                suspicious_peer_ratio: 0.0
            },
            "ECLIPSE": {
                node_id: "NODE_ECLIPSE_RISK_01",
                wallet_address: "0x4444444444444444444444444444444444444444",
                identity_age_days: 28,
                transaction_count: 55,
                peer_count: 4,
                stake_eth: 10.0,
                ip_subnet: "104.244.42.0/24",
                asn: "AS_ATTACK_NET",
                recent_tx_frequency_per_min: 1.0,
                failed_tx_ratio: 0.02,
                has_conflicting_spends: false,
                withholding_block_flag: false,
                peer_diversity_score: 0.12,
                suspicious_peer_ratio: 0.88
            }
        };

        // Canvas Graphic State
        const canvas = document.getElementById('arenaCanvas');
        const ctx = canvas.getContext('2d');
        let animId = null;

        let candidateNode = { x: 70, y: 160, status: 'candidate', targetX: 70, targetY: 160, color: '#38bdf8' };
        let honestMesh = [
            { id: 'N01', x: 500, y: 80, color: '#10b981' },
            { id: 'N02', x: 620, y: 110, color: '#10b981' },
            { id: 'N03', x: 670, y: 210, color: '#10b981' },
            { id: 'N04', x: 580, y: 260, color: '#10b981' },
            { id: 'N05', x: 480, y: 190, color: '#10b981' }
        ];

        let scanRays = false;
        let scanRayColor = '#38bdf8';
        let packetParticles = [];

        function initPackets() {
            packetParticles = [];
            for (let i = 0; i < 6; i++) {
                packetParticles.push({
                    src: Math.floor(Math.random() * honestMesh.length),
                    dst: Math.floor(Math.random() * honestMesh.length),
                    progress: Math.random()
                });
            }
        }
        initPackets();

        function renderCanvas() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Draw Dividing Perimeter Wall (Gate in Middle)
            const gateX = 320;
            ctx.strokeStyle = '#1e293b';
            ctx.lineWidth = 2;
            ctx.setLineDash([6, 4]);
            ctx.beginPath();
            ctx.moveTo(gateX, 0);
            ctx.lineTo(gateX, canvas.height);
            ctx.stroke();
            ctx.setLineDash([]);

            // Gate Portcullis Box
            ctx.fillStyle = '#0f172a';
            ctx.strokeStyle = scanRays ? scanRayColor : '#0284c7';
            ctx.lineWidth = 2.5;
            ctx.strokeRect(gateX - 25, 110, 50, 100);
            ctx.fillRect(gateX - 25, 110, 50, 100);

            // Gate Icon / Text
            ctx.fillStyle = scanRays ? scanRayColor : '#38bdf8';
            ctx.font = 'bold 10px monospace';
            ctx.fillText('GATE', gateX - 12, 160);

            // Scan Rays Animation if active
            if (scanRays) {
                ctx.strokeStyle = scanRayColor;
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.moveTo(candidateNode.x, candidateNode.y);
                ctx.lineTo(gateX, 120);
                ctx.moveTo(candidateNode.x, candidateNode.y);
                ctx.lineTo(gateX, 200);
                ctx.stroke();
            }

            // Draw P2P Mesh Connections
            ctx.lineWidth = 1;
            ctx.strokeStyle = '#1e293b';
            for (let i = 0; i < honestMesh.length; i++) {
                for (let j = i + 1; j < honestMesh.length; j++) {
                    ctx.beginPath();
                    ctx.moveTo(honestMesh[i].x, honestMesh[i].y);
                    ctx.lineTo(honestMesh[j].x, honestMesh[j].y);
                    ctx.stroke();
                }
            }

            // Draw Moving Packets inside Honest Mesh
            ctx.fillStyle = '#34d399';
            packetParticles.forEach(p => {
                p.progress += 0.015;
                if (p.progress > 1) {
                    p.progress = 0;
                    p.src = Math.floor(Math.random() * honestMesh.length);
                    p.dst = Math.floor(Math.random() * honestMesh.length);
                }
                const p1 = honestMesh[p.src];
                const p2 = honestMesh[p.dst];
                if (p1 && p2) {
                    const px = p1.x + (p2.x - p1.x) * p.progress;
                    const py = p1.y + (p2.y - p1.y) * p.progress;
                    ctx.beginPath();
                    ctx.arc(px, py, 2.5, 0, Math.PI * 2);
                    ctx.fill();
                }
            });

            // Draw Honest Mesh Nodes
            honestMesh.forEach(n => {
                ctx.beginPath();
                ctx.arc(n.x, n.y, 11, 0, Math.PI * 2);
                ctx.fillStyle = n.color;
                ctx.fill();
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 1.5;
                ctx.stroke();

                ctx.fillStyle = '#94a3b8';
                ctx.font = '9px monospace';
                ctx.fillText(n.id, n.x - 9, n.y - 14);
            });

            // Smooth Movement of Candidate Node towards Gate
            candidateNode.x += (candidateNode.targetX - candidateNode.x) * 0.1;
            candidateNode.y += (candidateNode.targetY - candidateNode.y) * 0.1;

            // Draw Candidate Node
            ctx.beginPath();
            ctx.arc(candidateNode.x, candidateNode.y, 13, 0, Math.PI * 2);
            ctx.fillStyle = candidateNode.color;
            ctx.fill();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.stroke();

            ctx.fillStyle = '#e2e8f0';
            ctx.font = 'bold 9px monospace';
            ctx.fillText('JOIN', candidateNode.x - 11, candidateNode.y + 3);

            animId = requestAnimationFrame(renderCanvas);
        }
        renderCanvas();

        // 5-Stage Step-by-Step Simulation Logic
        async function startSimulation(scenarioKey) {
            const isProtected = document.getElementById('defenseToggle').checked;

            // 1. Fetch REAL Live Node Data from Web3.py / Ganache
            document.getElementById('simulationStatus').innerText = `Querying live Ganache blockchain via Web3.py...`;
            const liveNodeRes = await fetch(`/api/get_live_node?scenario=${scenarioKey}`);
            const data = await liveNodeRes.json();

            // Update Live On-Chain Bar
            document.getElementById('onchainAddress').innerText = data.wallet_address;
            const bal = data.on_chain_data && data.on_chain_data.real_balance_eth !== undefined ? data.on_chain_data.real_balance_eth : data.stake_eth;
            const nonce = data.on_chain_data && data.on_chain_data.real_on_chain_nonce !== undefined ? data.on_chain_data.real_on_chain_nonce : data.transaction_count;
            const blockNum = data.on_chain_data && data.on_chain_data.latest_block_number !== undefined ? data.on_chain_data.latest_block_number : 1;
            
            document.getElementById('onchainBalance').innerText = `${Number(bal).toFixed(2)} ETH`;
            document.getElementById('onchainNonce').innerText = `${nonce} txs`;
            document.getElementById('rpcStatusText').innerText = `Ganache RPC (http://127.0.0.1:7545) • Block #${blockNum} • LIVE`;

            // Reset UI
            document.querySelectorAll('[id^="step"]').forEach(el => el.classList.remove('step-active'));
            document.getElementById('stampBanner').classList.add('hidden');
            document.getElementById('overrideBox').classList.add('hidden');
            document.getElementById('decisionBadge').className = 'px-2 py-0.5 rounded text-[11px] font-black bg-gray-800 text-gray-400';
            document.getElementById('decisionBadge').innerText = 'EVALUATING...';

            candidateNode.x = 70;
            candidateNode.y = 160;
            candidateNode.color = '#38bdf8';
            candidateNode.targetX = 260; // Approaches Gate
            candidateNode.targetY = 160;
            scanRays = false;

            document.getElementById('simulationStatus').innerText = `Real Node ${data.node_id} (${data.wallet_address.substring(0, 10)}...) knocking on Gateway...`;

            // STAGE 1: Monitor Agent Ingestion (0.6s)
            setPipelineStep(1);
            await wait(600);
            scanRays = true;
            scanRayColor = '#38bdf8';
            document.getElementById('simulationStatus').innerText = `Stage 1: Monitor Agent compiling structured telemetry from Ganache...`;

            // Call Backend REST API
            const response = await fetch('/api/evaluate_node', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const res = await response.json();

            // STAGE 2: 4 Attack Risk Agents Run Diagnostics (0.9s)
            setPipelineStep(2);
            await wait(900);
            document.getElementById('simulationStatus').innerText = `Stage 2: Sybil, Wallet, Finney & Eclipse Agents scanning...`;
            
            // Animate Risk Gauges
            updateGauges(res.risk_scores);

            // STAGE 3: Positive Trust Verification (0.7s)
            setPipelineStep(3);
            await wait(700);
            document.getElementById('simulationStatus').innerText = `Stage 3: Verifying Positive Trust (I, T, N, H, B)...`;

            // STAGE 4: Trust Factor & Threshold Comparison (0.8s)
            setPipelineStep(4);
            await wait(800);
            document.getElementById('simulationStatus').innerText = `Stage 4: Computing TF = 0.60(PT) + 0.40(1-AL)...`;
            
            document.getElementById('scoreTF').innerText = res.tf.toFixed(2);
            document.getElementById('barTF').style.width = `${Math.min(100, res.tf * 100)}%`;

            if (res.critical_override) {
                document.getElementById('overrideBox').classList.remove('hidden');
            }

            // STAGE 5: Autonomous Enforcement Decision
            setPipelineStep(5);
            await wait(500);

            // Handle Protected vs Unprotected visual outcome
            if (isProtected) {
                // ASTRA Autonomous Prevention
                if (res.decision === 'ACCEPT') {
                    // Node Passes into Network Mesh
                    candidateNode.targetX = 420;
                    candidateNode.targetY = 140;
                    candidateNode.color = '#10b981';
                    scanRayColor = '#10b981';
                    
                    showStamp('ADMISSION GRANTED', 'bg-emerald-950/90 text-emerald-400 border-emerald-500');
                    document.getElementById('decisionBadge').className = 'px-2 py-0.5 rounded text-[11px] font-black bg-emerald-950 text-emerald-400 border border-emerald-700';
                    document.getElementById('decisionBadge').innerText = 'ACCEPT';
                    document.getElementById('simulationStatus').innerText = `Result: Node verified and integrated into P2P topology.`;
                } else {
                    // Node Intercepted & Blocked at Perimeter Gate
                    candidateNode.targetX = 140; // Pushed back
                    candidateNode.targetY = 240;
                    candidateNode.color = '#ef4444';
                    scanRayColor = '#ef4444';

                    showStamp('ACCESS DENIED', 'bg-red-950/90 text-red-400 border-red-500');
                    document.getElementById('decisionBadge').className = 'px-2 py-0.5 rounded text-[11px] font-black bg-red-950 text-red-400 border border-red-700';
                    document.getElementById('decisionBadge').innerText = 'REJECTED';
                    document.getElementById('simulationStatus').innerText = `Result: BLOCKED PRE-ADMISSION! Network completely protected.`;
                }
            } else {
                // UNPROTECTED (Shows the vulnerability!)
                candidateNode.targetX = 540;
                candidateNode.targetY = 160;
                candidateNode.color = '#ef4444';
                
                showStamp('BREACHED (UNPROTECTED)', 'bg-red-950/90 text-red-400 border-red-500');
                document.getElementById('decisionBadge').className = 'px-2 py-0.5 rounded text-[11px] font-black bg-red-950 text-red-400 border border-red-700';
                document.getElementById('decisionBadge').innerText = 'EXPLOITED';
                document.getElementById('simulationStatus').innerText = `VULNERABILITY: Malicious node entered freely without verification!`;
            }

            // Update Explanation Box
            document.getElementById('explanationText').innerHTML = `
                <div class="font-bold ${res.decision === 'ACCEPT' ? 'text-emerald-400' : 'text-red-400'} mb-1">
                    Decision: ${res.decision} (${res.reason})
                </div>
                <div>${res.summary}</div>
            `;
        }

        function setPipelineStep(stepNum) {
            document.querySelectorAll('[id^="step"]').forEach(el => el.classList.remove('step-active'));
            const activeEl = document.getElementById(`step${stepNum}`);
            if (activeEl) activeEl.classList.add('step-active');
        }

        function updateGauges(risk) {
            document.getElementById('valSR').innerText = risk.SR.toFixed(2);
            document.getElementById('barSR').style.width = `${risk.SR * 100}%`;

            document.getElementById('valWR').innerText = risk.WR.toFixed(2);
            document.getElementById('barWR').style.width = `${risk.WR * 100}%`;

            document.getElementById('valFR').innerText = risk.FR.toFixed(2);
            document.getElementById('barFR').style.width = `${risk.FR * 100}%`;

            document.getElementById('valER').innerText = risk.ER.toFixed(2);
            document.getElementById('barER').style.width = `${risk.ER * 100}%`;
        }

        function showStamp(text, classes) {
            const b = document.getElementById('stampBanner');
            b.innerText = text;
            b.className = `absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 px-6 py-3 rounded-xl font-black text-xl border-2 shadow-2xl backdrop-blur-md transform scale-100 transition duration-300 ${classes}`;
            b.classList.remove('hidden');
        }

        document.getElementById('defenseToggle').addEventListener('change', (e) => {
            const label = document.getElementById('defenseToggleText');
            if (e.target.checked) {
                label.innerText = 'ASTRA Protected (With AI)';
                label.className = 'font-bold text-emerald-400';
            } else {
                label.innerText = 'Classic Blockchain (Unprotected)';
                label.className = 'font-bold text-red-400';
            }
        });

        function wait(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }
    </script>
</body>
</html>
"""


class AstraVisualHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif parsed.path.startswith("/api/get_live_node"):
            query = urllib.parse.parse_qs(parsed.query)
            scenario = query.get("scenario", ["HONEST"])[0]
            from node_join import get_live_blockchain_nodes
            live_nodes = get_live_blockchain_nodes()
            node_req = live_nodes.get(scenario, live_nodes["HONEST"])
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(node_req.to_dict()).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len).decode('utf-8') if content_len > 0 else "{}"

        if parsed.path == "/api/evaluate_node":
            node_dict = json.loads(post_body)
            result = admission_graph.run(node_dict)
            result["on_chain_data"] = node_dict.get("on_chain_data", {})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def run_visual_server(port=PORT):
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), AstraVisualHandler) as httpd:
        print("=" * 65)
        print("[ASTRA] Live Visual Arena Server Running")
        print(f"[ASTRA] Open in Browser: http://localhost:{port}")
        print("=" * 65)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server gracefully...")


if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_visual_server(p)
