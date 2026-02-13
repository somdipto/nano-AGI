#!/bin/bash
# Launcher for Telegram Voice Bot

set -e

cd "$(dirname "$0")/.."

echo "============================================"
echo "🤖 Telegram Voice Bot Launcher"
echo "============================================"
echo ""

# Check for .env
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check token
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ ERROR: TELEGRAM_BOT_TOKEN not set!"
    echo ""
    echo "📝 Get your token:"
    echo "   1. Open Telegram and search for @BotFather"
    echo "   2. Send /newbot and follow instructions"
    echo "   3. Copy the token"
    echo "   4. Run: export TELEGRAM_BOT_TOKEN=your_token_here"
    echo ""
    exit 1
fi

echo "✅ Telegram token found"

# Check CLIProxyAPI
echo "🔍 Checking CLIProxyAPI..."
if curl -s http://127.0.0.1:8317/v1/models > /dev/null 2>&1; then
    echo "✅ CLIProxyAPI is running"
else
    echo "⚠️  CLIProxyAPI not running!"
    echo ""
    echo "📝 Start it in another terminal:"
    echo "   cli-proxy-api"
    echo ""
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "============================================"
echo "🚀 Starting Bot..."
echo "============================================"
echo ""

# Run bot
./.venv/bin/python3 examples/telegram_voice_bot.py
