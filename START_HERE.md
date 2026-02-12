# 🤖 Telegram Bot + Gemini OAuth - SUPER SIMPLE SETUP

## ⚡️ WHAT YOU GET
A Telegram bot that remembers conversations using **Google Gemini** (FREE) - **NO OpenAI API KEY NEEDED!**

## 🎯 IN 3 SIMPLE STEPS

### STEP 1: Get Bot Token (5 min) 📱
1. Open **Telegram**
2. Search: `@BotFather`
3. Click **Start**
4. Send: `/newbot`
5. Give it a name
6. **COPY THE TOKEN** (save it!)

---

### STEP 2: Setup GUI App (5 min) 🖥️

**Download EasyCLI (Desktop GUI):**
- Go to: https://github.com/router-for-me/EasyCLI/releases
- Download for your Mac/Windows
- Open it
- Click **"Login with Google"**
- Login in browser
- **Done!** ✅ (Keep it running)

**Alternative (if EasyCLI doesn't work):**
```bash
brew install cliproxyapi
cli-proxy-api --login
```

---

### STEP 3: Run Your Bot (2 min) 🚀

**Open Terminal** and run:

```bash
cd /Users/sodan/Desktop/x/memU
./run_bot.sh
```

**First time only:**
- It will ask for your Telegram token
- Edit the `.env` file:
  ```
  TELEGRAM_BOT_TOKEN=your_token_here
  ```
- Run `./run_bot.sh` again

**That's it!** Your bot is running! 🎉

---

## 💬 HOW TO USE

Open Telegram, find your bot, then:

| Command | What it does |
|---------|-------------|
| **Just type** | Bot remembers everything |
| `/remember I love pizza` | Saves "I love pizza" |
| `/recall` | Shows all memories |
| `/recall pizza` | Searches for "pizza" |
| `/forget` | Clears memories |
| `/help` | Shows commands |

---

## 🔧 TROUBLESHOOTING

### ❌ "Token not found"
**Fix:** Edit `.env` file and add your real token from @BotFather

### ❌ "CLIProxyAPI not running"
**Fix:** Make sure EasyCLI app is open, or run `cli-proxy-api` in another terminal

### ❌ "uv not found"
**Fix:** Run: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### ❌ Bot not responding
**Fix:**
1. Check EasyCLI is running
2. Stop bot (Ctrl+C) and run `./run_bot.sh` again

---

## 📁 FILES IN THIS FOLDER

- `telegram_bot_simple.py` - The bot code
- `run_bot.sh` - Launch script (just double-click or run in terminal)
- `.env` - Your token file (keep secret!)
- `UI_SETUP_GUIDE.md` - Detailed guide

---

## ✨ WHAT MAKES THIS SPECIAL

✅ **FREE** - Uses Gemini free tier (60 req/min)
✅ **NO API KEY** - Uses OAuth (login with Google)
✅ **PRIVATE** - Runs on your computer
✅ **SMART** - Remembers everything you say

---

## 🚀 QUICK START CHECKLIST

- [ ] Got Telegram bot token from @BotFather
- [ ] Downloaded & opened EasyCLI
- [ ] Logged in with Google
- [ ] Edited `.env` with your token
- [ ] Ran `./run_bot.sh`
- [ ] Tested in Telegram!

**Total time: ~15 minutes**

---

## 📞 NEED HELP?

**Bot not working?**
1. Is EasyCLI running? (check menu bar)
2. Did you save the token correctly in `.env`?
3. Try stopping and starting again

**Still stuck?**
- Read `UI_SETUP_GUIDE.md` for detailed steps
- Check that you're in `/Users/sodan/Desktop/x/memU` folder

---

## 🎉 YOU'RE DONE!

Your Telegram bot now:
- Uses Google Gemini AI (free!)
- Remembers all your conversations
- Needs no OpenAI API key
- Runs on your own computer

**Enjoy your AI memory bot!** 🤖✨
