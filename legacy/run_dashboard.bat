@echo off
title ASTRA - Research Evaluation Dashboard (legacy prototype)
echo =====================================================================
echo  ASTRA: Agentic AI for Blockchain Node Admission Security
echo  Researchers: Dhruv Basia ^& Amisha Rawat
echo  Supervisor: Prof. Rahul Johari ^| USAR, GGSIPU
echo =====================================================================
echo Starting Dashboard on http://localhost:8501 ...
cd /d "%~dp0"
start http://localhost:8501
echo.
..\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.headless true
pause
