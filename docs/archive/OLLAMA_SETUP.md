# Using memU with Ollama (Local AI Models)

This guide shows how to use memU with **Ollama** - running AI models locally on your computer.

## 🎯 Benefits

- ✅ **100% Local** - No internet required
- ✅ **Free Forever** - No API costs
- ✅ **Private** - Your data never leaves your computer
- ✅ **Fast** - No network latency

## 📋 Prerequisites

1. **Mac with Apple Silicon (M1/M2/M3)** or Intel Mac with 16GB+ RAM
2. **Ollama** installed
3. **At least 8GB free disk space** for models

## 🚀 Step 1: Install Ollama

### **Option A: Download GUI App (Easiest)**
1. Go to: https://ollama.com/download
2. Download for Mac
3. Open the `.dmg` file
4. Drag Ollama to Applications
5. **Open Ollama app** (runs in menu bar)

### **Option B: Command Line**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

## 🚀 Step 2: Download Models

**Open Terminal** and run:

```bash
# Good for most use cases (4GB)
ollama pull llama3.2

# Or for better quality (8GB)
ollama pull llama3.1:8b

# Or for best quality (requires 16GB+ RAM)
ollama pull llama3.1:70b
```

**Wait for download to complete!** ☕

## 🚀 Step 3: Test Ollama

```bash
# Run a test
ollama run llama3.2

# Type: "Hello!" and press Enter
# You should see a response

# Exit with: /bye
```

## 🚀 Step 4: Configure memU for Ollama

Ollama runs a local API server at `http://localhost:11434`

### **Configuration for memU:**

```python
from memu.app import MemoryService

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openai",  # Ollama uses OpenAI-compatible API
            "base_url": "http://localhost:11434/v1",  # Ollama API endpoint
            "api_key": "ollama",  # Any value works for local Ollama
            "chat_model": "llama3.2",  # Model you downloaded
            "client_backend": "httpx",  # HTTP client
        },
        "embedding": {
            "provider": "openai",
            "base_url": "http://localhost:11434/v1",
            "api_key": "ollama",
            "embed_model": "nomic-embed-text",  # Embedding model
            "client_backend": "httpx",
        }
    },
    database_config={
        "metadata_store": {
            "provider": "inmemory",  # Or "sqlite"
        },
        "vector_index": {"provider": "bruteforce"},
    }
)
```

## 🚀 Step 5: Run Example

Create file `example_ollama.py`:

```python
"""
Example: Using memU with Ollama (Local AI)
"""

import asyncio
from memu.app import MemoryService

async def main():
    # Configure for Ollama
    service = MemoryService(
        llm_profiles={
            "default": {
                "provider": "openai",
                "base_url": "http://localhost:11434/v1",
                "api_key": "ollama",
                "chat_model": "llama3.2",
                "client_backend": "httpx",
            },
            "embedding": {
                "provider": "openai",
                "base_url": "http://localhost:11434/v1",
                "api_key": "ollama",
                "embed_model": "nomic-embed-text",
                "client_backend": "httpx",
            }
        },
        database_config={
            "metadata_store": {"provider": "inmemory"},
            "vector_index": {"provider": "bruteforce"},
        }
    )

    print("✅ memU + Ollama initialized!")
    print("🤖 Model: llama3.2 (local)")

    # Create a memory
    memory = await service.create_memory_item(
        memory_type="knowledge",
        memory_content="I love working with local AI models",
        user={"user_id": "local_user"}
    )

    print(f"✅ Memory created: {memory}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**
```bash
export PATH="/Users/sodan/.local/bin:$PATH"
uv run python example_ollama.py
```

## 📱 Telegram Bot with Ollama

### **Create `telegram_bot_ollama.py`:**

```python
"""
Telegram Bot using Ollama (Local AI) - NO API KEYS NEEDED!
"""

import asyncio
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from memu.app import MemoryService

# Initialize memU with Ollama (LOCAL AI!)
print("🚀 Starting memU with Ollama (Local AI)...")
print("🤖 Using local model: llama3.2")
print("💻 Everything runs on your computer!")

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openai",
            "base_url": "http://localhost:11434/v1",
            "api_key": "ollama",
            "chat_model": "llama3.2",
            "client_backend": "httpx",
        },
        "embedding": {
            "provider": "openai",
            "base_url": "http://localhost:11434/v1",
            "api_key": "ollama",
            "embed_model": "nomic-embed-text",
            "client_backend": "httpx",
        }
    },
    database_config={
        "metadata_store": {"provider": "inmemory"},
        "vector_index": {"provider": "bruteforce"},
    }
)

print("✅ memU + Ollama ready!")

user_memory = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_memory[user_id] = []

    welcome = """👋 **Welcome to Local AI Bot!**

🤖 **Powered by Ollama (Local AI)**
💻 **Everything runs on your computer**
🔒 **100% Private - No cloud**

**Commands:**
/remember <text> - Save to memory
/recall - Show memories
/recall <word> - Search memories
/help - Show commands

Just chat with me!"""

    await update.message.reply_text(welcome, parse_mode='Markdown')

async def remember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.replace("/remember", "").strip()

    if not text:
        await update.message.reply_text("❓ What should I remember?\nExample: `/remember I love pizza`")
        return

    try:
        memory = await service.create_memory_item(
            memory_type="knowledge",
            memory_content=text,
            user={"user_id": user_id}
        )
        await update.message.reply_text(f"✅ **Remembered!**\n📝 {text[:200]}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")

async def recall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    query = update.message.text.replace("/recall", "").strip()

    try:
        if query:
            queries = [{"role": "user", "content": {"text": query}}]
            result = await service.retrieve(queries=queries, where={"user_id": user_id})
            items = result.get("items", [])

            if not items:
                await update.message.reply_text(f"🔍 No memories for '{query}'")
                return

            response = f"🧠 **Memories about '{query}':**\n\n"
            for item in items[:5]:
                response += f"• {item.get('summary', '')[:150]}...\n\n"

            await update.message.reply_text(response)
        else:
            result = await service.list_memory_items(where={"user_id": user_id})
            items = result.get("items", [])

            if not items:
                await update.message.reply_text("📝 No memories yet!")
                return

            response = f"🧠 **Your Memories ({len(items)} total):**\n\n"
            for item in items[:10]:
                response += f"• {item.get('summary', '')[:120]}...\n\n"

            await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """🤖 **Local AI Bot Commands**

💾 **/remember <text>** - Save memory
🔍 **/recall** - List all memories
🔍 **/recall <word>** - Search memories
❓ **/help** - Show this help

💻 **Powered by:**
• Ollama (Local AI)
• llama3.2 model
• 100% Private & Free

🚀 **No internet needed!**"""

    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    if user_id not in user_memory:
        user_memory[user_id] = []

    user_memory[user_id].append({
        "role": "user",
        "content": {"text": text}
    })
    user_memory[user_id] = user_memory[user_id][-5:]

    try:
        result = await service.retrieve(
            queries=user_memory[user_id],
            where={"user_id": user_id}
        )

        items = result.get("items", [])

        if items:
            context_memories = "\n".join([item.get('summary', '') for item in items[:2]])
            response = f"💭 I remember! You mentioned:\n\n{context_memories[:400]}"
        else:
            response = "📝 Got it! I'll remember that.\n\nWhat else would you like to share?"

        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"👋 Thanks for sharing!\n\nUse `/remember` to save important info!")

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        print("❌ ERROR: Set TELEGRAM_BOT_TOKEN in .env file")
        return

    print(f"🤖 Starting Telegram bot...")
    print(f"🔑 Token loaded")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remember", remember))
    app.add_handler(CommandHandler("recall", recall))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running!")
    print("📱 Open Telegram and find your bot")
    print("💻 Everything is running locally!")

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
```

## 🚀 Run Telegram Bot with Ollama

### **Step 1: Start Ollama**
Make sure Ollama app is running in your menu bar.

### **Step 2: Run Bot**
```bash
export PATH="/Users/sodan/.local/bin:$PATH"
export TELEGRAM_BOT_TOKEN="your-token-here"
cd /Users/sodan/Desktop/x/memU
uv run python telegram_bot_ollama.py
```

## 📊 Model Recommendations

| Model | Size | Use Case | Speed |
|-------|------|----------|-------|
| llama3.2 | 2GB | Fast responses, basic tasks | ⚡⚡⚡ |
| llama3.1:8b | 5GB | Good balance | ⚡⚡ |
| llama3.1:70b | 40GB | Best quality | ⚡ |
| nomic-embed-text | 300MB | Embeddings only | ⚡⚡⚡ |

## 🛠️ Troubleshooting

### **"Connection refused" error**
```bash
# Make sure Ollama is running
ollama serve
```

### **"Model not found" error**
```bash
# Download the model first
ollama pull llama3.2
```

### **Slow responses**
- Use smaller model (llama3.2 instead of llama3.1:70b)
- Close other apps
- Use "inmemory" database instead of SQLite

### **Out of memory**
```bash
# Use smaller model
ollama pull llama3.2:1b
```

## 🎯 Quick Commands

```bash
# List downloaded models
ollama list

# Pull new model
ollama pull llama3.2

# Run model interactively
ollama run llama3.2

# Delete model
ollama rm llama3.2

# Check Ollama status
curl http://localhost:11434/api/tags
```

## 🎉 You're All Set!

You now have:
- ✅ Local AI running on your Mac
- ✅ Telegram bot with memory
- ✅ No cloud dependencies
- ✅ 100% private
- ✅ Free forever!

**Enjoy your local AI bot!** 🤖💻
