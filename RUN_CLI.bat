@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Error: Virtual environment not found at .venv\
    pause
    exit /b 1
)

echo Starting Story Review CLI...
.venv\Scripts\python.exe -m app %*

if %ERRORLEVEL% neq 0 (
    if "%~1"=="" (
        echo.
        echo Hint: Use "RUN_CLI.bat [command]" to run specific CLI actions.
        pause
    )
)
