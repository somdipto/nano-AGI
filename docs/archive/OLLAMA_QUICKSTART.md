# 🚀 Quick Start: memU + Ollama (Local AI)

## ⚡️ What You Get
A Telegram bot that runs **100% locally** on your Mac:
- ✅ No cloud APIs
- ✅ No internet required
- ✅ No costs ever
- ✅ 100% private

## 📦 Prerequisites
- Mac with 8GB+ RAM
- Ollama installed
- Telegram bot token

## 🎯 3-Step Setup

### Step 1: Install Ollama
**Download:** https://ollama.com/download
- Open the downloaded file
- Drag to Applications
- Open Ollama app (stays in menu bar)

### Step 2: Download AI Model
**Open Terminal and run:**
```bash
ollama pull llama3.2
```
Wait for download (about 2GB)

### Step 3: Run Bot
```bash
cd /Users/sodan/Desktop/x/memU
./run_bot_ollama.sh
```

**First time only:**
- Edit `.env` file
- Add your Telegram bot token
- Run again

---

## 💬 Using Your Bot

| Command | What it does |
|---------|-------------|
| `/start` | Welcome message |
| `/remember I love pizza` | Saves memory |
| `/recall` | Shows all memories |
| `/recall pizza` | Searches memories |
| `/help` | Show commands |
| **Just chat** | Bot remembers everything |

---

## 🔧 Files Created

- `telegram_bot_ollama.py` - Bot code
- `run_bot_ollama.sh` - Launcher script
- `docs/OLLAMA_SETUP.md` - Full guide

---

## 🎉 Done!

Your bot now:
- Runs completely offline
- Uses local AI (llama3.2)
- Remembers everything
- Costs $0 forever!

**Test it:** Open Telegram → Find your bot → Send `/start`
