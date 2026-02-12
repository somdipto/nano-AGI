# Using memU with Gemini CLI OAuth via CLIProxyAPI

This guide explains how to use **Gemini CLI's OAuth authentication** with memU through **CLIProxyAPI** as a proxy.

## Overview

Instead of using API keys directly in your code, you can use Gemini CLI's OAuth authentication through a proxy. This approach:

- ✅ **No API keys in code** - OAuth handled by CLIProxyAPI
- ✅ **Free tier available** - 60 req/min, 1000 req/day with Google account
- ✅ **Team-friendly** - Each developer uses their own OAuth
- ✅ **Secure** - Tokens managed by CLIProxyAPI

## Architecture

```
┌─────────────┐      OpenAI API      ┌──────────────┐      OAuth      ┌─────────────┐
│    memU     │ ────────────────────→ │ CLIProxyAPI  │ ────────────────→ │ Gemini CLI  │
│  (Python)   │    /v1/chat/completions│  (Proxy)    │    (Browser)    │  (OAuth)    │
└─────────────┘                       └──────────────┘                  └─────────────┘
                                             │
                                             ↓
                                       ┌──────────────┐
                                       │ Gemini API   │
                                       │ (Google)     │
                                       └──────────────┘
```

## Prerequisites

1. **Google Account** - For OAuth authentication
2. **Node.js 20+** - Required for Gemini CLI
3. **CLIProxyAPI** - The proxy server (we'll install this)

## Installation & Setup

### Step 1: Install CLIProxyAPI

**Option A: Homebrew (macOS/Linux)**
```bash
brew install cliproxyapi
```

**Option B: Manual Download**
```bash
# For macOS ARM (M1/M2/M3)
curl -L -o cli-proxy-api.tar.gz \
  https://github.com/router-for-me/CLIProxyAPI/releases/latest/download/cli-proxy-api_Darwin_arm64.tar.gz

# For macOS Intel
curl -L -o cli-proxy-api.tar.gz \
  https://github.com/router-for-me/CLIProxyAPI/releases/latest/download/cli-proxy-api_Darwin_x86_64.tar.gz

# Extract and install
tar -xzf cli-proxy-api.tar.gz
sudo mv cli-proxy-api /usr/local/bin/
```

**Option C: Run Setup Script**
```bash
chmod +x setup_gemini_oauth.sh
./setup_gemini_oauth.sh
```

### Step 2: Create Configuration

Create the config directory and file:

```bash
mkdir -p ~/.cli-proxy-api
```

Create `~/.cli-proxy-api/config.yaml`:

```yaml
# CLIProxyAPI Configuration

# Gemini CLI Provider (OAuth authentication)
gemini-cli:
  enabled: true

# Server configuration
server:
  port: 8317
  host: "127.0.0.1"

# OpenAI API compatibility mode
openai-compatibility:
  enabled: true
```

### Step 3: Start CLIProxyAPI & Authenticate

**Start the server:**
```bash
cli-proxy-api
```

**Authenticate with Google (OAuth):**
```bash
# In a new terminal window
cli-proxy-api --login
```

This will:
1. Open your browser
2. Ask you to login with your Google account
3. Request permissions for Gemini CLI
4. Save the OAuth token locally

**Verify it's working:**
```bash
curl http://127.0.0.1:8317/v1/models
```

You should see a list of available Gemini models.

## Using memU with Gemini CLI OAuth

### Configuration

Configure memU to use CLIProxyAPI:

```python
from memu.app import MemoryService

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openai",           # CLIProxyAPI mimics OpenAI API
            "base_url": "http://127.0.0.1:8317",  # CLIProxyAPI endpoint
            "api_key": "sk-dummy",          # Dummy key (OAuth handles auth)
            "chat_model": "gemini-2.5-flash",   # Choose your model
            "client_backend": "httpx",      # Use HTTP backend
        },
        "embedding": {
            "provider": "openai",
            "base_url": "http://127.0.0.1:8317",
            "api_key": "sk-dummy",
            "embed_model": "text-embedding-004",
            "client_backend": "httpx",
        }
    },
    database_config={
        "metadata_store": {
            "provider": "sqlite",
            "dsn": "sqlite:///memory.db",
        },
        "vector_index": {"provider": "bruteforce"},
    }
)
```

### Available Models

CLIProxyAPI supports these Gemini models:

- `gemini-2.5-pro` - Best quality, higher cost
- `gemini-2.5-flash` - Fast, good balance ⚡ Recommended
- `gemini-2.5-flash-lite` - Fastest, lowest cost
- `gemini-pro-latest` - Latest stable
- `gemini-flash-latest` - Latest flash

### Complete Example

See `examples/example_gemini_cli_oauth.py` for a complete working example.

**Run the example:**
```bash
cd /Users/sodan/Desktop/x/memU
export PATH="/Users/sodan/.local/bin:$PATH"
uv run python examples/example_gemini_cli_oauth.py
```

## How It Works

### Authentication Flow

1. **First Time Setup:**
   ```
   You → cli-proxy-api --login → Browser OAuth → Google Account
   ```

2. **Using memU:**
   ```
   memU → CLIProxyAPI (localhost:8317) → Gemini CLI (cached OAuth) → Gemini API
   ```

### OAuth Token Storage

- CLIProxyAPI stores OAuth tokens securely in `~/.cli-proxy-api/`
- Tokens are refreshed automatically
- No need to re-authenticate unless tokens expire

## Troubleshooting

### Issue: "Connection refused" error

**Solution:** Make sure CLIProxyAPI is running:
```bash
cli-proxy-api
```

### Issue: "Authentication required" error

**Solution:** Authenticate first:
```bash
cli-proxy-api --login
```

### Issue: "Model not found" error

**Solution:** Check available models:
```bash
curl http://127.0.0.1:8317/v1/models
```

Use one of the model names from the list.

### Issue: Rate limit exceeded

**Free tier limits:**
- 60 requests per minute
- 1000 requests per day

**Solutions:**
1. Wait a minute and retry
2. Use multiple Google accounts (CLIProxyAPI supports multi-account)
3. Upgrade to paid tier

## Advanced Configuration

### Multi-Account Setup (for higher quotas)

CLIProxyAPI supports multiple Gemini accounts for load balancing:

```yaml
# ~/.cli-proxy-api/config.yaml
gemini-cli:
  enabled: true
  accounts:
    - name: "account1"
      auth_dir: "~/.cli-proxy-api/auth1"
    - name: "account2"
      auth_dir: "~/.cli-proxy-api/auth2"
```

Login to each account:
```bash
cli-proxy-api --login --account account1
cli-proxy-api --login --account account2
```

### Using with Docker

```bash
docker run -d \
  --name cliproxyapi \
  -p 8317:8317 \
  -v ~/.cli-proxy-api:/root/.cli-proxy-api \
  eceasy/cli-proxy-api:latest
```

### Environment Variables

You can also configure via environment:

```bash
export CLIPROXYAPI_PORT=8317
export CLIPROXYAPI_GEMINI_ENABLED=true
export CLIPROXYAPI_OPENAI_COMPATIBILITY=true
```

## Benefits of This Approach

### 1. **Security**
- No API keys in code or environment variables
- OAuth tokens stored securely by CLIProxyAPI
- Automatic token refresh

### 2. **Team-Friendly**
- Each developer uses their own Google account
- No shared API keys
- Individual quota tracking

### 3. **Cost-Effective**
- Free tier: 60 req/min, 1000 req/day
- No credit card required
- Multi-account support for higher quotas

### 4. **Easy Management**
- One-time OAuth setup
- CLIProxyAPI handles all authentication
- Works with existing OpenAI-compatible code

## Comparison: API Key vs OAuth

| Feature | API Key | OAuth (CLIProxyAPI) |
|---------|---------|---------------------|
| Setup | Get key from AI Studio | Login with Google |
| Security | Key in code/env | Token managed by proxy |
| Free Tier | 1000 req/day | 1000 req/day |
| Team Use | Shared key | Individual accounts |
| Multi-account | Manual switching | Built-in load balancing |

## Next Steps

1. ✅ Install CLIProxyAPI
2. ✅ Run `cli-proxy-api --login` to authenticate
3. ✅ Test with the example: `examples/example_gemini_cli_oauth.py`
4. ✅ Integrate into your memU application

## Resources

- **CLIProxyAPI Docs**: https://help.router-for.me/
- **CLIProxyAPI GitHub**: https://github.com/router-for-me/CLIProxyAPI
- **Gemini CLI Docs**: https://geminicli.com/docs/
- **memU Docs**: See README.md in this repository

## Support

If you encounter issues:

1. Check CLIProxyAPI is running: `curl http://127.0.0.1:8317/v1/models`
2. Verify authentication: `cli-proxy-api --status`
3. Check CLIProxyAPI logs for errors
4. Open an issue in the CLIProxyAPI GitHub repo

---

**🎉 You now have memU working with Gemini CLI OAuth! No API keys needed!**
