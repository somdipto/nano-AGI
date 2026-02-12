#!/bin/bash
# Simple Launcher for Telegram Bot with Gemini OAuth
# No OpenAI API Key Needed!

clear
echo "============================================"
echo "🤖 Telegram Bot + Gemini OAuth Launcher"
echo "============================================"
echo ""

# Check if running from correct directory
if [ ! -f "telegram_bot_simple.py" ]; then
    echo "❌ Error: Please run this script from the memU folder"
    echo "   cd /Users/sodan/Desktop/x/memU"
    exit 1
fi

# Setup PATH
export PATH="/Users/sodan/.local/bin:$PATH"

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="/Users/sodan/.local/bin:$PATH"
fi

# Check if python-telegram-bot is installed
echo "📦 Checking dependencies..."
uv add python-telegram-bot 2>/dev/null || true

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  No .env file found!"
    echo ""
    echo "📝 Creating .env file..."
    echo "TELEGRAM_BOT_TOKEN=YOUR_TOKEN_HERE" > .env
    echo ""
    echo "✅ .env file created!"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Open .env file in any text editor"
    echo "   2. Replace YOUR_TOKEN_HERE with your actual token"
    echo "   3. Save the file"
    echo "   4. Run this script again"
    echo ""
    echo "💡 Get your token from @BotFather on Telegram"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Check if token is set
if [ "$TELEGRAM_BOT_TOKEN" = "YOUR_TOKEN_HERE" ] || [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Error: Telegram bot token not set!"
    echo ""
    echo "📝 Please edit .env file and add your token:"
    echo "   1. Open .env in a text editor"
    echo "   2. Change: TELEGRAM_BOT_TOKEN=your_actual_token"
    echo "   3. Save and run this script again"
    echo ""
    echo "💡 Get token from @BotFather on Telegram"
    exit 1
fi

echo "✅ Telegram bot token found"
echo ""

# Check if CLIProxyAPI is running
echo "🔍 Checking if CLIProxyAPI is running..."
if curl -s http://127.0.0.1:8317/v1/models > /dev/null 2>&1; then
    echo "✅ CLIProxyAPI is running!"
else
    echo "⚠️  CLIProxyAPI not detected!"
    echo ""
    echo "📝 Please start CLIProxyAPI first:"
    echo "   Option 1: Open EasyCLI app (GUI)"
    echo "   Option 2: Run in another terminal: cli-proxy-api"
    echo ""
    echo "⚠️  The bot may not work without CLIProxyAPI running!"
    echo ""
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "============================================"
echo "🚀 Starting Telegram Bot..."
echo "============================================"
echo ""
echo "📱 Open Telegram and find your bot"
echo "💬 Send /start to begin"
echo "⏹️  Press Ctrl+C to stop"
echo ""

# Run the bot
uv run python telegram_bot_simple.py
