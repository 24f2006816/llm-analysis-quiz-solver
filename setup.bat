@echo off
REM Setup script for LLM Quiz Solver (Windows)

echo === LLM Quiz Solver Setup ===
echo.

REM Check Python version
echo Checking Python version...
python --version
if errorlevel 1 (
    echo Python not found. Please install Python 3.8+
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Failed to create virtual environment
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies
    exit /b 1
)

REM Install Playwright browsers
echo Installing Playwright browsers (this may take a moment)...
playwright install chromium
if errorlevel 1 (
    echo Failed to install Playwright browsers
    exit /b 1
)

REM Create .env if it doesn't exist
if not exist .env (
    echo Creating .env file from .env.example...
    copy .env.example .env
    echo WARNING: Please edit .env and set your SECRET and EMAIL
)

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Edit .env and set SECRET and EMAIL
echo 2. Activate virtual environment: venv\Scripts\activate
echo 3. Run the server: python run.py
echo 4. Test the API: python example_usage.py

pause

