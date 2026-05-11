@echo off
setlocal
cd /d "%~dp0"

echo Checking virtual environment...
if not exist ".venv\Scripts\python.exe" (
    echo Error: Virtual environment not found at .venv\
    echo Please make sure you have installed dependencies.
    pause
    exit /b 1
)

echo Starting Story Review App (GUI)...
.venv\Scripts\python.exe -m app.main

if %ERRORLEVEL% neq 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%.
    pause
)
