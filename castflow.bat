@echo off
setlocal EnableExtensions
title CastFlow
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

set "CASTFLOW_HOME=%~dp0"
if "%CASTFLOW_HOME:~-1%"=="\" set "CASTFLOW_HOME=%CASTFLOW_HOME:~0,-1%"
set "MANAGER=%CASTFLOW_HOME%\.castflow\manager.py"

if not exist "%MANAGER%" (
    echo CastFlow manager not found:
    echo   %MANAGER%
    echo Place this bat next to the .castflow folder.
    pause
    exit /b 1
)

set "SKIPPAUSE="
set "PROJECT="
if /I "%~1"=="-y" (
    set "SKIPPAUSE=1"
    if not "%~2"=="" set "PROJECT=%~2"
) else (
    if not "%~1"=="" set "PROJECT=%~1"
)

echo.
echo CastFlow launcher
if defined PROJECT (
    echo Project: %PROJECT%
) else (
    echo A folder picker will open. Choose your game/app folder.
    echo CastFlow does not need to live inside that folder.
)
echo Close this window to stop the console.
echo.

where py >nul 2>&1
if not errorlevel 1 goto run_py
where python >nul 2>&1
if not errorlevel 1 goto run_python
where python3 >nul 2>&1
if not errorlevel 1 goto run_python3

echo Python 3 not found. Install Python 3 and add it to PATH, or use py -3.
pause
exit /b 1

:run_py
if defined PROJECT (
    py -3 "%MANAGER%" --project-root "%PROJECT%" launch --from-harness "%CASTFLOW_HOME%"
) else (
    py -3 "%MANAGER%" launch --from-harness "%CASTFLOW_HOME%"
)
goto after

:run_python
if defined PROJECT (
    python "%MANAGER%" --project-root "%PROJECT%" launch --from-harness "%CASTFLOW_HOME%"
) else (
    python "%MANAGER%" launch --from-harness "%CASTFLOW_HOME%"
)
goto after

:run_python3
if defined PROJECT (
    python3 "%MANAGER%" --project-root "%PROJECT%" launch --from-harness "%CASTFLOW_HOME%"
) else (
    python3 "%MANAGER%" launch --from-harness "%CASTFLOW_HOME%"
)
goto after

:after
if errorlevel 1 (
    echo.
    echo CastFlow exited with an error.
    pause
    exit /b 1
)
endlocal
