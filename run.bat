@echo off
rem ---------------------------------------------------------------------------
rem  Maze Chase AI - double-click this file to start.
rem  Options are passed on, for example:   run.bat --demo     run.bat --lab
rem ---------------------------------------------------------------------------
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py %*
    goto done
)
where uv >nul 2>nul
if not errorlevel 1 (
    uv run main.py %*
    goto done
)
where py >nul 2>nul
if not errorlevel 1 (
    py main.py %*
    goto done
)
python main.py %*

:done
if errorlevel 1 (
    echo.
    echo The program stopped with an error - see the message above.
    pause
)
