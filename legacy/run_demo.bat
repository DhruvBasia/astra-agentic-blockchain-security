@echo off
title ASTRA - Minor Project Terminal Demo (legacy prototype)
echo ======================================================================
echo   ASTRA: Blockchain Node Admission Security Demo
echo   Researchers: Dhruv Basia ^& Amisha Rawat
echo   Supervisor: Prof. Rahul Johari ^| USAR, GGSIPU
echo ======================================================================
echo.
cd /d "%~dp0"
..\.venv\Scripts\python.exe demo.py
echo.
pause
