@echo off
title Instagram Multi-Page AI Hub
cd /d "%~dp0"
echo ========================================================
echo   🚀 STARTING INSTAGRAM MULTI-PAGE AI HUB & AGENT
echo ========================================================
python -m pip install -r requirements.txt
python server.py
pause
