@echo off
echo ====================================
echo  SHREE LIVE TRADING TERMINAL SETUP
echo ====================================
echo Installing required packages...
pip install websockets requests
echo.
echo Starting SHREE Live Terminal...
python shree_live_terminal.py
pause
