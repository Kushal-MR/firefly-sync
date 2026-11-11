@echo off
rem Double-click: the live demo with the REAL ESP32.
rem Laptop must be on the same 2.4 GHz hotspot as the ESP32.
rem Nothing to type: the ESP32 is found automatically and the delay is measured.
rem If your hotspot blocks broadcast, run:  demo_esp32.bat --peer <ESP32 IP>
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Double-click run_sim.bat once first to set things up & pause & exit /b 1)
.venv\Scripts\python.exe scripts\run_live.py %*
if errorlevel 1 pause
