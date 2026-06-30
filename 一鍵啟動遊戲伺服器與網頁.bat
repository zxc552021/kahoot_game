@echo off
title 寶礦力遊戲一鍵啟動器
echo ===================================================
echo   正在啟動寶礦力遊戲本地伺服器並開啟主持人端網頁...
echo ===================================================
cd /d "%~dp0"
start "寶礦力遊戲伺服器" cmd /k "python server.py"
timeout /t 2 /nobreak >nul
start http://localhost:8000/host
exit
