@echo off
title ASTRA - Interactive Scenario Simulator (Port 8502, legacy prototype)
echo ===================================================
echo Launching Interactive Scenario Simulator...
echo URL: http://localhost:8502
echo ===================================================
cd /d "%~dp0\AgenticAI_Minor_v2"
..\..\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
pause
