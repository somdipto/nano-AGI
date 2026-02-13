#!/bin/bash
# Run both voice capture and Telegram bot together
# This script uses tmux to manage multiple processes

set -e

cd "$(dirname "$0")/.."

echo "============================================"
echo "🎤 Voice Memory System - Full Stack"
echo "============================================"
echo ""

# Check for .env
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check dependencies
if ! command -v tmux &> /dev/null; then
    echo "📦 Installing tmux..."
    brew install tmux
fi

# Check token
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "⚠️  WARNING: TELEGRAM_BOT_TOKEN not set"
    echo "   The Telegram bot won't start without it."
    echo "   Get token from @BotFather"
    echo ""
fi

# Check CLIProxyAPI
echo "🔍 Checking CLIProxyAPI..."
if ! curl -s http://127.0.0.1:8317/v1/models > /dev/null 2>&1; then
    echo "❌ CLIProxyAPI is not running!"
    echo ""
    echo "📝 Please start it first:"
    echo "   cli-proxy-api"
    echo ""
    exit 1
fi
echo "✅ CLIProxyAPI is running"
echo ""

# Create tmux session
SESSION="voice_memory"

echo "🚀 Starting full stack in tmux session: $SESSION"
echo ""
echo "📝 Commands:"
echo "   tmux attach -t $SESSION  - Attach to session"
echo "   Ctrl+B then D            - Detach from session"
echo "   tmux kill-session -t $SESSION - Stop all"
echo ""

# Kill existing session if it exists
tmux kill-session -t $SESSION 2>/dev/null || true

# Create new session
tmux new-session -d -s $SESSION -n voice

# Window 1: Voice capture
tmux send-keys -t $SESSION:voice "cd /Users/sodan/Desktop/x/memU" C-m
tmux send-keys -t $SESSION:voice "./.venv/bin/python3 examples/voice_memory_gemini.py" C-m

# Window 2: Telegram bot (only if token exists)
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    tmux new-window -t $SESSION -n telegram
    tmux send-keys -t $SESSION:telegram "cd /Users/sodan/Desktop/x/memU" C-m
    tmux send-keys -t $SESSION:telegram "export TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN" C-m
    tmux send-keys -t $SESSION:telegram "./.venv/bin/python3 examples/telegram_voice_bot.py" C-m
fi

echo "✅ Started!"
echo ""
echo "🎤 Voice capture running (Window 1)"
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    echo "🤖 Telegram bot running (Window 2)"
else
    echo "⚠️  Telegram bot not started (no token)"
fi
echo ""
echo "📱 To view: tmux attach -t $SESSION"
echo "⏹️  To stop: tmux kill-session -t $SESSION"
echo ""

# Auto-attach to session
tmux attach -t $SESSION
