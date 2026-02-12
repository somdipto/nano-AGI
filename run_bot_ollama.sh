#!/bin/bash
# Launcher for Telegram Bot with Gemini CLI Proxy

set -e

echo "=================================================="
echo "🤖 Telegram Bot + Gemini CLI Proxy"
echo "=================================================="
echo ""

# Check if we're in the right directory
if [ ! -f "telegram_bot_ollama.py" ]; then
    echo "❌ Error: telegram_bot_ollama.py not found!"
    echo "📁 Please run this script from the memU directory"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found!"
    echo ""
    echo "📝 Creating .env file..."
    echo "TELEGRAM_BOT_TOKEN=" > .env
    echo ""
    echo "✅ Created .env file"
    echo ""
    echo "🔑 Please edit .env and add your Telegram bot token:"
    echo "   1. Get token from @BotFather on Telegram"
    echo "   2. Edit .env file"
    echo "   3. Add: TELEGRAM_BOT_TOKEN=your_token_here"
    echo ""
    exit 1
fi

# Check if TELEGRAM_BOT_TOKEN is set
source .env
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN not set in .env file!"
    echo ""
    echo "📝 Please edit .env and add your token:"
    echo "   TELEGRAM_BOT_TOKEN=your_token_here"
    echo ""
    echo "🤖 Get token from @BotFather on Telegram"
    exit 1
fi

echo "✅ Telegram bot token found"
echo ""

# Check Python environment
if ! command -v uv &> /dev/null; then
    echo "❌ uv not found!"
    echo ""
    echo "📝 Please install uv:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    exit 1
fi

echo "✅ uv is installed"
echo ""

# Check if CLIProxyAPI is installed
if ! command -v cli-proxy-api &> /dev/null; then
    echo "⚠️  CLIProxyAPI not found!"
    echo ""
    echo "📝 Please install CLIProxyAPI first:"
    echo "   brew install cliproxyapi"
    echo ""
    echo "Or download from:"
    echo "   https://github.com/router-for-me/CLIProxyAPI/releases"
    echo ""
    exit 1
fi

echo "✅ CLIProxyAPI is installed"

# Check if CLIProxyAPI is running
echo "🔍 Checking if CLIProxyAPI is running..."
if curl -s http://127.0.0.1:8317/v1/models > /dev/null 2>&1; then
    echo "✅ CLIProxyAPI is running!"
    echo ""
else
    echo "⚠️  CLIProxyAPI is not running!"
    echo ""
    echo "📝 Please start CLIProxyAPI in a separate terminal:"
    echo "   cli-proxy-api"
    echo ""
    echo "🔐 If not authenticated yet, run:"
    echo "   cli-proxy-api --login"
    echo ""
    echo "This will open your browser for Google OAuth authentication."
    echo ""
    exit 1
fi

# All checks passed!
echo ""
echo "🚀 Starting Telegram Bot with Gemini..."
echo ""
echo "📡 Proxy: http://127.0.0.1:8317"
echo "🤖 Model: gemini-2.0-flash"
echo "🔐 Auth: OAuth (via CLIProxyAPI)"
echo ""
echo "⏹️  Press Ctrl+C to stop"
echo ""

# Set PATH to include local bin
export PATH="/Users/sodan/.local/bin:$PATH"

# Run the bot
uv run python telegram_bot_ollama.py
