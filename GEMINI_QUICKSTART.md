# 🚀 Quick Start: memU + Gemini CLI Proxy

## ⚡️ What You Get
A Telegram bot powered by **Google Gemini** via OAuth:
- ✅ No API keys in code
- ✅ Free tier: 60 req/min, 1000 req/day
- ✅ OAuth authentication
- ✅ Cloud-powered AI

## 📦 Prerequisites
- Mac or Linux
- Node.js 20+ (for Gemini CLI)
- Telegram bot token

## 🎯 3-Step Setup

### Step 1: Install CLIProxyAPI
**Option A: Homebrew (Recommended)**
```bash
brew install cliproxyapi
```

**Option B: Manual Download**
```bash
# For macOS ARM (M1/M2/M3)
curl -L -o cli-proxy-api.tar.gz \
  https://github.com/router-for-me/CLIProxyAPI/releases/latest/download/cli-proxy-api_Darwin_arm64.tar.gz

# Extract and install
tar -xzf cli-proxy-api.tar.gz
sudo mv cli-proxy-api /usr/local/bin/
```

### Step 2: Authenticate with Google
**Start CLIProxyAPI:**
```bash
cli-proxy-api
```

**In a new terminal, login:**
```bash
cli-proxy-api --login
```

This will:
- Open your browser
- Ask for Google account login
- Request Gemini CLI permissions
- Save OAuth token locally

**Verify it's working:**
```bash
curl http://127.0.0.1:8317/v1/models
```
You should see a list of available Gemini models.

### Step 3: Run Bot
```bash
cd /Users/sodan/Desktop/x/memU
./run_bot_ollama.sh
```

**First time only:**
- The script will create `.env` file
- Edit it and add your Telegram bot token
- Run the script again

---

## 💬 Using Your Bot

| Command | What it does |
|---------|--------------|
| `/start` | Welcome message |
| `/remember I love pizza` | Saves memory |
| `/recall` | Shows all memories |
| `/recall pizza` | Searches memories |
| `/help` | Show commands |
| **Just chat** | Bot remembers everything |

---

## 🔧 Configuration

The bot uses these settings (in `.env`):

```env
TELEGRAM_BOT_TOKEN=your_token_here
GEMINI_PROXY_BASE_URL=http://127.0.0.1:8317
GEMINI_MODEL=gemini-2.0-flash
GEMINI_EMBED_MODEL=text-embedding-004
```

---

## 📊 Available Models

| Model | Speed | Quality | Use Case |
|-------|-------|---------|----------|
| gemini-2.0-flash | ⚡⚡⚡ | Good | Recommended for most |
| gemini-2.5-pro | ⚡ | Best | Complex reasoning |
| gemini-2.5-flash-lite | ⚡⚡⚡ | Fast | Quick responses |

---

## 🛠️ Troubleshooting

### **"Connection refused" error**
```bash
# Make sure CLIProxyAPI is running
cli-proxy-api
```

### **"Authentication required" error**
```bash
# Authenticate with Google
cli-proxy-api --login
```

### **Rate limit exceeded**
Free tier limits:
- 60 requests per minute
- 1000 requests per day

**Solutions:**
1. Wait a minute and retry
2. Use multiple Google accounts
3. Upgrade to paid tier

---

## 🎉 Done!

Your bot now:
- ✅ Uses Google Gemini AI
- ✅ Authenticates with OAuth
- ✅ Remembers conversations
- ✅ Free to use (within limits)!

**Test it:** Open Telegram → Find your bot → Send `/start`

---

## 📚 More Information

- **Full Setup Guide:** [docs/GEMINI_CLI_OAUTH_GUIDE.md](docs/GEMINI_CLI_OAUTH_GUIDE.md)
- **CLIProxyAPI Docs:** https://help.router-for.me/
- **memU Documentation:** See [README.md](README.md)
