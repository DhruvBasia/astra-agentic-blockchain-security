# Legacy prototypes

Earlier iterations of ASTRA, kept for the project's history. They are **not** used by the
`astra/` package, the tests or the reported results; the maintained implementation is
[`../astra/`](../astra/). Run every launcher from this folder (double-click the `.bat`, or
`cd legacy` first); they use the virtual environment at the repository root.

| Path | What it is | Launcher |
| :--- | :--- | :--- |
| `agentic_blockchain_security/` | First modular prototype: Web3.py client, Monitor/Sybil/Wallet/Finney/Eclipse agents, trust calculator, a 7-node simulated benchmark and a simple admission state graph. Needs Ganache on port 7545. | `run_agentic_pipeline.bat` |
| `app.py`, `astra_*.py` | First Streamlit research dashboard and an in-memory attack simulator. | `run_dashboard.bat`, `test_simulation.bat` |
| `demo.py` | Terminal demo that evaluates live Ganache accounts with the first prototype's agents. | `run_demo.bat` |
| `web_server.py` | Standalone HTML "admission arena" with canvas animation. | `run_standalone_web.bat` |
| `AgenticAI_Minor_v2/` | Teammate's Ganache scenario simulator: mines a normal and a coordinated Sybil scenario on-chain and scores them with a multi-factor Sybil agent. | `run_partner_app.bat` |

The 7-node "100% accuracy" table produced by `agentic_blockchain_security/tests/test_trust.py`
is a hand-built sanity check, not an evaluation. Use the 120-candidate benchmark of the main
package (`python -m astra eval`) for any reported figure.
