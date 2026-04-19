@echo off
REM PiCar-X Quick Start Script for Windows/Development

setlocal enabledelayedexpansion

echo ==========================================
echo PiCar-X Setup ^& Launch Script
echo ==========================================
echo.

REM Get project directory
set PROJECT_DIR=%~dp0

echo Project directory: %PROJECT_DIR%
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python 3 from https://www.python.org/
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "%PROJECT_DIR%venv\" (
    echo Creating virtual environment...
    python -m venv "%PROJECT_DIR%venv"
)

REM Activate virtual environment
echo Activating virtual environment...
call "%PROJECT_DIR%venv\Scripts\activate.bat"

REM Install requirements
if exist "%PROJECT_DIR%requirements.txt" (
    echo Installing dependencies...
    python -m pip install --upgrade pip setuptools wheel
    pip install -r "%PROJECT_DIR%requirements.txt"
)

REM Navigate to backend and start server
echo.
echo Starting PiCar-X server...
echo Access the web interface at: http://localhost:5000
echo.

cd /d "%PROJECT_DIR%backend"
python app.py

pause
