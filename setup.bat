@echo off
REM HeaNg[Black-Cyber] Bot Setup Script for Windows

echo.
echo ============================================
echo    HeaNg[Black-Cyber] Bot Setup
echo ============================================
echo.

REM Check if .env file exists
if exist ".env" (
    echo [OK] .env file found
) else (
    echo [WARNING] .env file not found. Creating from .env.example...
    if exist ".env.example" (
        copy .env.example .env
        echo [OK] .env file created. Please edit it with your credentials.
    ) else (
        echo [ERROR] .env.example not found
        exit /b 1
    )
)

echo.
echo Checking dependencies...

REM Check Python version
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] Python !PYTHON_VERSION! found
) else (
    echo [ERROR] Python not found. Please install Python 3.8+
    exit /b 1
)

echo.
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo [OK] Setup complete!
echo.
echo Next steps:
echo 1. Edit .env file with your credentials
echo    - TELEGRAM_TOKEN: Your Telegram bot token
echo    - OPENROUTER_KEY: Your OpenRouter API key
echo.
echo 2. Run the bot:
echo    python main.py
echo.
echo 3. Use /history command to view conversation history
echo.
echo For more information, see SECURITY.md
echo.
pause
