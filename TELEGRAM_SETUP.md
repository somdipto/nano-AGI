# 🎤 Voice Memory + Telegram Bot — Quick Start

## What You Get

```
┌──────────────────────────────────┐
│  YOUR MAC (runs 24/7)            │
│  ┌────────────┐  ┌─────────────┐ │
│  │ Whisper.cpp│  │ Telegram Bot│ │
│  │ (captures) │  │ (responds)  │ │
│  └──────┬─────┘  └──────┬──────┘ │
│         │                │        │
│         ▼                ▼        │
│    ┌────────────────────────┐    │
│    │ Shared SQLite Database │    │
│    └────────────────────────┘    │
└──────────────────────────────────┘
                ▲
                │ Telegram API
                │
        ┌───────┴────────┐
        │ YOU (anywhere) │
        │  Telegram App  │
        └────────────────┘
```

**Features:**
- 🎤 **24/7 voice capture** via Whisper.cpp
- 💬 **Query from anywhere** via Telegram
- 🧠 **Smart memory** using memU + Gemini
- 🔒 **100% local processing** (no API keys)

## Setup (5 minutes)

### 1. Get Telegram Bot Token

```bash
# Open Telegram and search for @BotFather
# Send: /newbot
# Follow instructions and copy the token
```

### 2. Set Environment Variable

```bash
# Option A: Export (temporary)
export TELEGRAM_BOT_TOKEN=your_token_here

# Option B: Add to .env (persistent)
echo "TELEGRAM_BOT_TOKEN=your_token_here" >> .env
```

### 3. Start CLIProxyAPI

```bash
# In a separate terminal
cli-proxy-api

# Or use EasyCLI app
```

## Running

### Option 1: Run Everything Together (Recommended)

```bash
bash scripts/run_all.sh
```

This starts:
- Voice capture (Window 1)
- Telegram bot (Window 2)

**Tmux shortcuts:**
- `Ctrl+B` then `D` - Detach (keeps running)
- `tmux attach -t voice_memory` - Re-attach
- `Ctrl+B` then `0` or `1` - Switch windows
- `tmux kill-session -t voice_memory` - Stop all

### Option 2: Run Separately

**Terminal 1: Voice Capture**
```bash
./.venv/bin/python3 examples/voice_memory_gemini.py
```

**Terminal 2: Telegram Bot**
```bash
bash scripts/run_telegram_bot.sh
```

## Using the Bot

**Commands:**
- `/start` - Welcome message
- `/transcripts` - Show recent voice transcripts
- `/search <keyword>` - Search all memories
- `/ask <question>` - Query your memories
- `/stats` - Memory statistics
- `/help` - Show help

**Example conversation:**

```
You: /transcripts
Bot: 🎤 Recent Transcripts (5 total):
     1. [2026-02-13 07:30] I need to finish the project by Friday...

You: /search deadline
Bot: 🔍 Search results for 'deadline':
     1. 🎤 I need to finish the project by Friday

You: When did I mention the project?
Bot: 💭 Found 2 related memories:
     I need to finish the project by Friday...
```

## Files Created

| File | Purpose |
|------|---------|
| [telegram_voice_bot.py](file:///Users/sodan/Desktop/x/memU/examples/telegram_voice_bot.py) | Telegram bot with voice-specific commands |
| [run_telegram_bot.sh](file:///Users/sodan/Desktop/x/memU/scripts/run_telegram_bot.sh) | Launch script for bot only |
| [run_all.sh](file:///Users/sodan/Desktop/x/memU/scripts/run_all.sh) | Launch script for both systems |

## Troubleshooting

**Bot not responding?**
```bash
# Check if CLIProxyAPI is running
curl http://127.0.0.1:8317/v1/models

# Check if bot is running
ps aux | grep telegram
```

**No transcripts?**
```bash
# Make sure voice capture is running
ps aux | grep voice_memory

# Check database
ls -lh ~/shadow-memory/memory.db
```

**Grant microphone permission:**
- System Preferences → Privacy & Security → Microphone
- Enable for Terminal/iTerm

## Tech Stack

- **Whisper.cpp** - Local speech-to-text
- **Gemini 2.5 Flash** - Free LLM (via CLIProxyAPI)
- **memU** - Memory framework
- **SQLite** - Local database
- **python-telegram-bot** - Bot framework
