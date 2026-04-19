@echo off
REM PiCar-X Quick Start Script for Windows/Development using uv

setlocal enabledelayedexpansion

echo ==========================================
echo PiCar-X Setup ^& Launch Script (uv)
echo ==========================================
echo.

REM Get project directory
set PROJECT_DIR=%~dp0

echo Project directory: %PROJECT_DIR%
echo.

REM Check if uv is installed
uv --version >nul 2>&1
if errorlevel 1 (
    echo uv not found. Installing uv...
    powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
    REM Update PATH for current session
    set "PATH=%APPDATA%\Python\Scripts;%PATH%"
    echo uv installed. Please restart this script if uv commands fail.
)

REM Sync dependencies using uv
echo Syncing dependencies with uv...
call uv sync --python 3.9
if errorlevel 1 (
    echo ERROR: Failed to sync dependencies. Please check your Python 3.9 installation.
    pause
    exit /b 1
)

REM Navigate to backend and start server
echo.
echo Starting PiCar-X server...
echo Access the web interface at: http://localhost:5000
echo.

cd /d "%PROJECT_DIR%backend"
call uv run python app.py
if errorlevel 1 (
    echo ERROR: Failed to start the server. Please check the error messages above.
    pause
    exit /b 1
)

pause
