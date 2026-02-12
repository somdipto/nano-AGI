"""
Telegram Bot using Gemini via CLI Proxy API - NO API KEYS NEEDED!
Uses OAuth authentication through CLIProxyAPI - secure and free!
"""

import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from memu.app import MemoryService

# Initialize memU with Gemini CLI OAuth (NO OpenAI API KEY!)
print("🚀 Starting memU with Gemini CLI OAuth...")
print("📡 Connecting to CLIProxyAPI at http://127.0.0.1:8317")
print("🤖 Using model: gemini-2.0-flash")
print("🔒 OAuth authentication - No API keys needed")
print("")

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openai",  # CLIProxyAPI mimics OpenAI API
            "base_url": "http://127.0.0.1:8317",  # CLIProxyAPI runs here
            "api_key": "sk-dummy",  # Dummy key - OAuth handles real auth!
            "chat_model": "gemini-2.0-flash",  # FREE Gemini model
            "client_backend": "httpx",  # HTTP backend for proxy
        },
        "embedding": {
            "provider": "openai",
            "base_url": "http://127.0.0.1:8317",
            "api_key": "sk-dummy",
            "embed_model": "text-embedding-004",  # Gemini embeddings
            "client_backend": "httpx",
        },
    },
    database_config={
        "metadata_store": {"provider": "inmemory"},
        "vector_index": {"provider": "bruteforce"},
    },
)

print("✅ memU initialized with Gemini!")
print("💎 Using model: gemini-2.0-flash (FREE)")
print("")

user_memory = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = str(update.effective_user.id)
    user_memory[user_id] = []

    welcome = """👋 **Welcome to Your Gemini Memory Bot!**

� **I can remember our conversations!**

**Commands:**
/remember <text> - Save something important
/recall - Show all your memories
/recall <word> - Search your memories
/help - Show this help

**Just chat with me** and I'll remember everything!

⚡️ Powered by Google Gemini (Free Tier)"""

    await update.message.reply_text(welcome, parse_mode="Markdown")


async def remember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save something to memory"""
    user_id = str(update.effective_user.id)
    text = update.message.text.replace("/remember", "").strip()

    if not text:
        await update.message.reply_text(
            "❓ What should I remember?\nExample: `/remember I love pizza`", parse_mode="Markdown"
        )
        return

    try:
        await service.create_memory_item(memory_type="knowledge", memory_content=text, user={"user_id": user_id})
        await update.message.reply_text(f"✅ **Remembered!**\n📝 {text[:200]}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def recall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search or list memories"""
    user_id = str(update.effective_user.id)
    query = update.message.text.replace("/recall", "").strip()

    try:
        if query:
            # Search with query
            queries = [{"role": "user", "content": {"text": query}}]
            result = await service.retrieve(queries=queries, where={"user_id": user_id})
            items = result.get("items", [])

            if not items:
                await update.message.reply_text(f"🔍 No memories for '{query}'")
                return

            response = f"🧠 **Memories about '{query}':**\n\n"
            for item in items[:5]:
                response += f"• {item.get('summary', '')[:150]}...\n\n"

            await update.message.reply_text(response, parse_mode="Markdown")
        else:
            # List all memories
            result = await service.list_memory_items(where={"user_id": user_id})
            items = result.get("items", [])

            if not items:
                await update.message.reply_text("📝 No memories yet! Use `/remember` to save something.")
                return

            response = f"🧠 **Your Memories ({len(items)} total):**\n\n"
            for item in items[:10]:
                response += f"• {item.get('summary', '')[:120]}...\n\n"

            await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    help_text = """🤖 **Gemini Memory Bot Commands**

� **Chat**
Just send messages - I'll remember!

�💾 **Save**
`/remember <text>` - Save something important

🔍 **Recall**
`/recall` - List all memories
`/recall <word>` - Search memories

❓ **Help**
`/help` - Show this message

⚡️ **Powered by:**
• Google Gemini (Free Tier)
• CLIProxyAPI (OAuth)
• memU Framework"""

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages"""
    user_id = str(update.effective_user.id)
    text = update.message.text

    # Keep conversation history
    if user_id not in user_memory:
        user_memory[user_id] = []

    user_memory[user_id].append({"role": "user", "content": {"text": text}})
    user_memory[user_id] = user_memory[user_id][-5:]

    try:
        # Try to retrieve relevant memories
        result = await service.retrieve(queries=user_memory[user_id], where={"user_id": user_id})

        items = result.get("items", [])

        if items:
            # We have context!
            context_memories = "\n".join([item.get("summary", "") for item in items[:2]])
            response = f"💭 I remember! You mentioned:\n\n{context_memories[:400]}"
        else:
            # New information
            response = "📝 Got it! I'll remember that.\n\nWhat else would you like to share?"

        await update.message.reply_text(response)
    except Exception:
        await update.message.reply_text("👋 Thanks for sharing!\n\nUse `/remember` to save important info!")


def main():
    """Start the bot"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        print("❌ ERROR: No Telegram bot token found!")
        print("")
        print("📝 To fix this:")
        print("1. Get token from @BotFather on Telegram")
        print("2. Create file .env with: TELEGRAM_BOT_TOKEN=your_token")
        print("")
        return

    print("🤖 Starting Telegram bot...")
    print(f"🔑 Token loaded: {token[:10]}...")
    print("")

    # Create bot application
    app = Application.builder().token(token).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remember", remember))
    app.add_handler(CommandHandler("recall", recall))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running!")
    print("📱 Open Telegram and find your bot")
    print("⏹️  Press Ctrl+C to stop")
    print("")

    # Run the bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
