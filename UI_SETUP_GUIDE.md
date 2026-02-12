# Gemini OAuth + Telegram - UI Setup Guide (No OpenAI API Key!)

## 🎯 What You're Building
A Telegram bot that uses Google's Gemini AI (free!) with NO OpenAI API key needed.

## 📱 Step 1: Get Telegram Bot Token (5 minutes)

1. **Open Telegram** on your phone or computer
2. **Search for**: `@BotFather`
3. **Click** "Start" or send `/start`
4. **Send**: `/newbot`
5. **Follow prompts**:
   - Name your bot (e.g., "My Gemini Bot")
   - Create username (e.g., `mygeminibot` - must end in 'bot')
6. **Copy the token** BotFather gives you (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
7. **Save it** somewhere safe!

## 🖥️ Step 2: Install CLIProxyAPI GUI App (5 minutes)

### **Option A: EasyCLI (Recommended - Has Desktop GUI)**

1. **Download EasyCLI** from: https://github.com/router-for-me/EasyCLI/releases
2. **Open the downloaded file** (.dmg for Mac, .exe for Windows)
3. **Drag to Applications** (Mac) or install (Windows)
4. **Open EasyCLI app**

### **What You'll See:**
- A nice window with buttons
- Click "Login with Google"
- Your browser opens
- Login with your Google account
- Click "Allow" for Gemini permissions
- Done! ✅

## 🚀 Step 3: Run the Telegram Bot

### **For Mac Users:**

1. **Open Terminal** (press `Cmd + Space`, type "Terminal", press Enter)
2. **Copy and paste these commands ONE BY ONE:**

```bash
# Go to the memU folder
cd /Users/sodan/Desktop/x/memU

# Add telegram library
export PATH="/Users/sodan/.local/bin:$PATH"
uv add python-telegram-bot

# Create your bot config (replace YOUR_TOKEN with actual token from Step 1)
echo "TELEGRAM_BOT_TOKEN=YOUR_TOKEN" > .env
```

3. **Edit the .env file** to add your real token:
   - Type: `nano .env`
   - Replace `YOUR_TOKEN` with your actual token from Step 1
   - Press `Ctrl+O` then Enter to save
   - Press `Ctrl+X` to exit

4. **Run the bot:**
```bash
export PATH="/Users/sodan/.local/bin:$PATH"
uv run python telegram_bot_simple.py
```

5. **Open Telegram**, find your bot, click "Start"!

## 💬 How to Use Your Bot

Once running, you can:

- **Type anything** → Bot remembers it
- **`/remember I love pizza`** → Saves to memory
- **`/recall`** → Shows all memories
- **`/recall pizza`** → Searches for "pizza"
- **`/forget`** → Clears all memories
- **`/help`** → Shows all commands

## 🔧 If Something Goes Wrong

### **Problem: "cli-proxy-api not found"**
**Solution**:
1. Make sure EasyCLI is running (check menu bar)
2. Or install via terminal: `brew install cliproxyapi`

### **Problem: "uv not found"**
**Solution**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/Users/sodan/.local/bin:$PATH"
```

### **Problem: Bot doesn't respond**
**Solution**:
1. Check that CLIProxyAPI/EasyCLI is running
2. Check that you put the correct token in `.env` file
3. Stop and restart the bot: Press `Ctrl+C` then run again

## 🎉 That's It!

You now have:
- ✅ A Telegram bot using Gemini AI (free!)
- ✅ No OpenAI API key needed
- ✅ All conversations remembered
- ✅ Works on your phone/computer

## 📞 Need Help?

If stuck, check:
1. Is EasyCLI running? (Look for icon in menu bar)
2. Did you copy the right bot token?
3. Are you in the right folder? (`/Users/sodan/Desktop/x/memU`)

**Remember**:
- EasyCLI must be running while using the bot
- The bot runs in Terminal - don't close it!
