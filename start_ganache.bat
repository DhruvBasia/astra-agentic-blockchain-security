@echo off
title Ganache Local Blockchain Node
echo =====================================================================
echo  Starting Local Ganache Ethereum Blockchain on port 7545...
echo =====================================================================
cmd /c "npx ganache --port 7545 --wallet.deterministic true"
pause
