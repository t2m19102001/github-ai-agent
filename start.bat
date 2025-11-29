@echo off
REM GitHub Copilot Alternative - Windows Startup Script
REM This script starts the web server on Windows

setlocal enabledelayedexpansion

set "PROJECT_DIR=%~dp0"
set "VENV_DIR=%PROJECT_DIR%.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

echo.
echo 🚀 GitHub Copilot Alternative - Starting...
echo.

REM Check if venv exists
if not exist "%VENV_DIR%" (
    echo ❌ Virtual environment not found at %VENV_DIR%
    echo Please create it with: python -m venv .venv
    pause
    exit /b 1
)

REM Check Python in venv
if not exist "%PYTHON_EXE%" (
    echo ❌ Python not found in virtual environment
    pause
    exit /b 1
)

echo ✅ Virtual environment found

REM Get Python version
for /f "tokens=*" %%i in ('"%PYTHON_EXE%" --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python version: %PYTHON_VERSION%
echo.

REM Kill any existing process on port 5000
echo 🔍 Checking port 5000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000') do (
    echo ⚠️  Port 5000 is in use. Killing existing process...
    taskkill /PID %%a /F >nul 2>&1
    timeout /t 1 /nobreak >nul
)
echo ✅ Port cleared
echo.

echo 📂 Project directory: %PROJECT_DIR%
echo 🌐 Starting web server on http://localhost:5000
echo 📊 Dashboard: http://localhost:5000/dashboard
echo.
echo Press Ctrl+C to stop the server
echo.
echo ════════════════════════════════════════════════════════════════
echo.

REM Start the server
cd /d "%PROJECT_DIR%"
call "%PYTHON_EXE%" run_web.py

pause
