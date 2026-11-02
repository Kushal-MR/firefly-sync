@echo off
rem Double-click: the live demo with the REAL ESP32.
rem Laptop must be on the same 2.4 GHz hotspot as the ESP32.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Double-click run_sim.bat once first to set things up & pause & exit /b 1)
set /p IP=ESP32 IP address (from Serial Monitor): 
set ONEWAY=0
set /p ONEWAY=One-way delay in ms from the Phase 0 test (Enter = 0): 
.venv\Scripts\python.exe scripts\run_live.py --peer %IP% --oneway-ms %ONEWAY% %*
if errorlevel 1 pause
