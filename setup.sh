#!/bin/bash

# HeaNg[Black-Cyber] Bot Setup Script
# This script helps set up the bot with proper environment configuration

echo "🚀 HeaNg[Black-Cyber] Bot Setup"
echo "===================="
echo ""

# Check if .env file exists
if [ -f ".env" ]; then
    echo "✅ .env file found"
else
    echo "⚠️ .env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ .env file created. Please edit it with your credentials."
    else
        echo "❌ .env.example not found"
        exit 1
    fi
fi

echo ""
echo "Checking dependencies..."

# Check Python version
if command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    echo "✅ Python $PYTHON_VERSION found"
else
    echo "❌ Python not found. Please install Python 3.8+"
    exit 1
fi

echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file with your credentials"
echo "   - TELEGRAM_TOKEN: Your Telegram bot token"
echo "   - OPENROUTER_KEY: Your OpenRouter API key"
echo ""
echo "2. Run the bot:"
echo "   python main.py"
echo ""
echo "3. Use /history command to view conversation history"
echo ""
echo "📚 For more information, see SECURITY.md"
