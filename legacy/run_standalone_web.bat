@echo off
title ASTRA - Live Visual Node Admission Arena (legacy prototype)
echo =====================================================================
echo  ASTRA: Live Visual Node Admission Arena (With Canvas Animation)
echo  Researchers: Dhruv Basia ^& Amisha Rawat
echo  Supervisor: Prof. Rahul Johari ^| USAR, GGSIPU
echo =====================================================================
echo Starting Live Visual Arena on port 8503...
cd /d "%~dp0"
echo Opening browser at http://localhost:8503
start http://localhost:8503
echo.
..\.venv\Scripts\python.exe web_server.py 8503
pause
