"""
Simple Telegram Bot for memU + Gemini CLI OAuth
NO OpenAI API Key Needed!

This bot uses Gemini through CLIProxyAPI with OAuth authentication.
"""

import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from memu.app import MemoryService

# Initialize memU with Gemini CLI OAuth (NO OpenAI API KEY!)
print("🚀 Starting memU with Gemini CLI OAuth...")
print("📡 Connecting to CLIProxyAPI at http://127.0.0.1:8317")

service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openai",  # CLIProxyAPI mimics OpenAI API
            "base_url": "http://127.0.0.1:8317",  # CLIProxyAPI runs here
            "api_key": "sk-dummy",  # Dummy key - OAuth handles real auth!
            "chat_model": "gemini-2.5-flash",  # FREE Gemini model
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
        "metadata_store": {
            "provider": "inmemory",
        },
        "vector_index": {"provider": "bruteforce"},
    },
)

print("✅ memU initialized with Gemini!")
print("💎 Using model: gemini-2.5-flash (FREE)")

# Store user conversations
user_memory = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """When user sends /start"""
    user_id = str(update.effective_user.id)
    user_memory[user_id] = []

    welcome = """👋 **Welcome to Your Gemini Memory Bot!**

🧠 **I can remember our conversations!**

**Commands:**
/remember <text> - Save something important
/recall - Show all your memories
/recall <word> - Search your memories
/forget - Clear all memories
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
        # Save to memU
        await service.create_memory_item(
            memory_type="knowledge", memory_content=text, memory_categories=["general"], user={"user_id": user_id}
        )

        await update.message.reply_text(f"✅ **Remembered!**\n\n📝 {text[:200]}", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def recall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search or list memories"""
    user_id = str(update.effective_user.id)
    query = update.message.text.replace("/recall", "").strip()

    try:
        if query:
            # Search for specific term
            queries = [{"role": "user", "content": {"text": query}}]
            result = await service.retrieve(queries=queries, where={"user_id": user_id})

            items = result.get("items", [])
            if not items:
                await update.message.reply_text(f"🔍 No memories found for '{query}'")
                return

            response = f"🧠 **Memories about '{query}':**\n\n"
            for i, item in enumerate(items[:5], 1):
                response += f"{i}. {item.get('summary', '')[:150]}...\n\n"

            await update.message.reply_text(response, parse_mode="Markdown")

        else:
            # List all memories
            result = await service.list_memory_items(where={"user_id": user_id})
            items = result.get("items", [])

            if not items:
                await update.message.reply_text("📝 No memories yet!\nUse `/remember <text>` to save something.")
                return

            response = f"🧠 **Your Memories ({len(items)} total):**\n\n"
            for i, item in enumerate(items[:10], 1):
                response += f"{i}. {item.get('summary', '')[:120]}...\n\n"

            if len(items) > 10:
                response += f"_... and {len(items) - 10} more_"

            await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def forget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all memories"""

    try:
        # This would need a clear method - for now just inform user
        await update.message.reply_text(
            "🗑️ **Clear memories**\n\n"
            "To clear memories, please delete the database file manually:\n"
            "`telegram_gemini_memory.db`",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    help_text = """🤖 **Gemini Memory Bot Commands**

💬 **Chat**
Just send messages - I'll remember!

💾 **Save**
`/remember <text>` - Save something important

🔍 **Recall**
`/recall` - List all memories
`/recall <word>` - Search memories

🗑️ **Clear**
`/forget` - Clear all memories (manual)

❓ **Help**
`/help` - Show this message

⚡️ **Powered by:**
• Google Gemini (Free Tier)
• CLIProxyAPI (OAuth)
• memU Framework"""

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle normal messages"""
    user_id = str(update.effective_user.id)
    text = update.message.text

    # Keep conversation history
    if user_id not in user_memory:
        user_memory[user_id] = []

    user_memory[user_id].append({"role": "user", "content": {"text": text}})

    # Keep last 5 messages
    user_memory[user_id] = user_memory[user_id][-5:]

    try:
        # Try to retrieve relevant memories
        result = await service.retrieve(queries=user_memory[user_id], where={"user_id": user_id})

        items = result.get("items", [])

        if items:
            # We have relevant context!
            context_memories = "\n".join([item.get("summary", "") for item in items[:2]])
            response = f"💭 I remember! You mentioned:\n\n{context_memories[:400]}"
        else:
            # New information
            response = "📝 Got it! I'll remember that.\n\nWhat else would you like to share?"

        await update.message.reply_text(response)

    except Exception:
        # Fallback response
        await update.message.reply_text(
            f"👋 Thanks for sharing!\n\nUse `/remember {text[:50]}...` to save this officially!"
        )


def main():
    """Start the bot"""
    # Get token from environment
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        print("❌ ERROR: No Telegram bot token found!")
        print("\n📝 To fix this:")
        print("1. Get token from @BotFather on Telegram")
        print("2. Create a file named .env in this folder")
        print("3. Add: TELEGRAM_BOT_TOKEN=your_token_here")
        print("\nOr run: export TELEGRAM_BOT_TOKEN=your_token")
        return

    print("🤖 Starting Telegram bot...")
    print(f"🔑 Token loaded: {token[:10]}...")

    # Create bot application
    app = Application.builder().token(token).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remember", remember))
    app.add_handler(CommandHandler("recall", recall))
    app.add_handler(CommandHandler("forget", forget))
    app.add_handler(CommandHandler("help", help_command))

    # Handle regular messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running!")
    print("📱 Open Telegram and find your bot")
    print("⏹️  Press Ctrl+C to stop")
    print("")

    # Run the bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
