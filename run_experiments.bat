@echo off
rem Double-click: rerun EVERY experiment from scratch and show the results.
rem 50 runs per setting, about 3 minutes. Proves the graphs come from
rem real simulation runs, not typed-in numbers.
rem Quick check instead:  run_experiments.bat --repeats 5
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Double-click run_sim.bat once first to set things up & pause & exit /b 1)
echo Running all experiments (size, loss, drift, speed, rogues, walls)...
echo.
.venv\Scripts\python.exe scripts\run_sweep.py %* || (pause & exit /b 1)
echo.
echo Drawing the graphs...
.venv\Scripts\python.exe scripts\plot_results.py || (pause & exit /b 1)
echo.
echo Done. Opening the overview graph and the results table.
echo Every single run is in data\sweep_*.csv (open them in Excel).
start "" "data\figures\fig_overview.png"
start "" "data\figures\summary.md"
pause
