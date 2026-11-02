@echo off
rem Double-click: the full live demo with a PRETEND ESP32 (no hardware).
rem Opens the fake ESP32 in its own window, then the swarm window.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Double-click run_sim.bat once first to set things up & pause & exit /b 1)
start "Fake ESP32" .venv\Scripts\python.exe scripts\fake_esp32.py
timeout /t 1 /nobreak >nul
.venv\Scripts\python.exe scripts\run_live.py --peer 127.0.0.1 %*
taskkill /fi "WINDOWTITLE eq Fake ESP32*" >nul 2>&1
