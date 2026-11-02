@echo off
rem Double-click: the virtual swarm on its own. Extra options pass through,
rem e.g.  run_sim.bat --drones 40
cd /d "%~dp0"
call :setup || exit /b 1
.venv\Scripts\python.exe scripts\run_sim.py %*
exit /b

:setup
if exist .venv\Scripts\python.exe exit /b 0
echo First run: creating .venv and installing packages (one time, ~1 min)...
python -m venv .venv || (echo Python not found. Install Python 3.10+ & pause & exit /b 1)
.venv\Scripts\python.exe -m pip install -r requirements.txt || (pause & exit /b 1)
exit /b 0
