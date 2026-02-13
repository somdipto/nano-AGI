"""
Telegram Bot for Voice Capture + memU + Gemini CLI
Query your voice transcripts from anywhere via Telegram!

All processing runs on your Mac:
- Whisper.cpp for transcription
- memU for memory storage
- Gemini CLI for AI responses
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Add src to path so we can import memu
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from memu.app import MemoryService

# Database path - same as voice capture
DB_PATH = Path.home() / "shadow-memory" / "memory.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

print("🚀 Starting Telegram Voice Bot...")
print(f"📂 Database: {DB_PATH}")
print("📡 Connecting to CLIProxyAPI at http://127.0.0.1:8317")

# Initialize memU with SQLite (same DB as voice capture)
service = MemoryService(
    llm_profiles={
        "default": {
            "provider": "openai",
            "base_url": "http://127.0.0.1:8317",
            "api_key": "sk-dummy",
            "chat_model": "gemini-2.5-flash",
            "client_backend": "httpx",
        },
        "embedding": {
            "provider": "openai",
            "base_url": "http://127.0.0.1:8317",
            "api_key": "sk-dummy",
            "embed_model": "text-embedding-004",
            "client_backend": "httpx",
        },
    },
    database_config={
        "metadata_store": {
            "provider": "sqlite",
            "dsn": f"sqlite:///{DB_PATH}",
        },
        "vector_index": {"provider": "bruteforce"},
    },
    retrieve_config={"method": "rag"},
)

print("✅ memU initialized!")
print("💎 Using: gemini-2.5-flash + Whisper.cpp")
print()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    user_id = str(update.effective_user.id)

    welcome = """👋 **Welcome to Voice Memory Bot!**

🎤 **I remember everything you say** (via Whisper.cpp running on your Mac)

**Commands:**
/transcripts - Recent voice transcripts
/search <keyword> - Search voice + text memories
/stats - Memory statistics
/ask <question> - Ask about your memories
/help - Show this help

**Just chat with me** and I'll search your memories!

⚡️ **100% Local Processing:**
• Whisper.cpp (transcription)
• Gemini (via CLIProxyAPI)
• memU (memory storage)"""

    await update.message.reply_text(welcome, parse_mode="Markdown")


async def transcripts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent voice transcripts"""
    user_id = str(update.effective_user.id)

    try:
        # Get recent transcripts - filter by transcript memory type
        result = await service.list_memory_items(
            where={"user_id": user_id, "memory_type": "transcript"}
        )
        items = result.get("items", [])

        if not items:
            await update.message.reply_text(
                "📝 No transcripts yet!\n\n"
                "Make sure voice capture is running:\n"
                "`./venv/bin/python3 examples/voice_memory_gemini.py`",
                parse_mode="Markdown",
            )
            return

        # Sort by created_at, most recent first
        items_sorted = sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)

        response = f"🎤 **Recent Transcripts ({len(items)} total):**\n\n"
        for i, item in enumerate(items_sorted[:10], 1):
            summary = item.get("summary", "")
            timestamp = item.get("created_at", "")
            response += f"{i}. [{timestamp[:16]}] {summary[:150]}...\n\n"

        if len(items) > 10:
            response += f"_... and {len(items) - 10} more_"

        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search memories"""
    user_id = str(update.effective_user.id)
    query = update.message.text.replace("/search", "").strip()

    if not query:
        await update.message.reply_text(
            "❓ What should I search for?\nExample: `/search project deadline`",
            parse_mode="Markdown",
        )
        return

    try:
        # Search using RAG
        queries = [{"role": "user", "content": {"text": query}}]
        result = await service.retrieve(queries=queries, where={"user_id": user_id})

        items = result.get("items", [])
        if not items:
            await update.message.reply_text(f"🔍 No memories found for '{query}'")
            return

        response = f"🔍 **Search results for '{query}':**\n\n"
        for i, item in enumerate(items[:5], 1):
            summary = item.get("summary", "")
            mem_type = item.get("memory_type", "unknown")
            emoji = "🎤" if mem_type == "transcript" else "💬"
            response += f"{i}. {emoji} {summary[:200]}...\n\n"

        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show memory statistics"""
    user_id = str(update.effective_user.id)

    try:
        result = await service.list_memory_items(where={"user_id": user_id})
        items = result.get("items", [])

        # Count by type
        transcripts = [i for i in items if i.get("memory_type") == "transcript"]
        other = [i for i in items if i.get("memory_type") != "transcript"]

        response = f"""📊 **Your Memory Stats:**

🎤 Voice Transcripts: {len(transcripts)}
💬 Other Memories: {len(other)}
📝 Total Items: {len(items)}

🗄️ Database: `~/shadow-memory/memory.db`
"""

        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask a question about memories"""
    user_id = str(update.effective_user.id)
    question = update.message.text.replace("/ask", "").strip()

    if not question:
        await update.message.reply_text(
            "❓ What's your question?\nExample: `/ask What did I say about the deadline?`",
            parse_mode="Markdown",
        )
        return

    try:
        # Retrieve relevant memories
        queries = [{"role": "user", "content": {"text": question}}]
        result = await service.retrieve(queries=queries, where={"user_id": user_id})

        items = result.get("items", [])
        if not items:
            await update.message.reply_text(
                "🤔 I don't have any memories that match your question."
            )
            return

        # Build context from top memories
        context_text = "\n".join([item.get("summary", "") for item in items[:3]])

        response = f"""💭 **Based on your memories:**

{context_text[:800]}

_Found {len(items)} relevant memory/memories_"""

        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    help_text = """🤖 **Voice Memory Bot Commands**

🎤 **Transcripts**
`/transcripts` - Show recent voice captures

🔍 **Search**
`/search <keyword>` - Search all memories

📊 **Stats**
`/stats` - Show memory statistics

💭 **Ask**
`/ask <question>` - Query your memories

💬 **Chat**
Just send a message to search!

❓ **Help**
`/help` - Show this message

⚡️ **Tech Stack:**
• Whisper.cpp (local transcription)
• Gemini 2.5 Flash (via CLIProxyAPI)
• memU (memory framework)
• SQLite (shared database)"""

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle natural language queries"""
    user_id = str(update.effective_user.id)
    text = update.message.text

    try:
        # Search memories
        queries = [{"role": "user", "content": {"text": text}}]
        result = await service.retrieve(queries=queries, where={"user_id": user_id})

        items = result.get("items", [])

        if items:
            # Found relevant memories
            summary = items[0].get("summary", "")[:300]
            count = len(items)
            response = f"💭 **Found {count} related memory/memories:**\n\n{summary}..."
        else:
            response = "🤔 No memories found. Try different keywords or use `/search`!"

        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(
            f"👋 Got your message!\n\nUse `/search {text[:50]}` to search memories.",
            parse_mode="Markdown",
        )


def main():
    """Start the bot"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        print("❌ ERROR: No Telegram bot token found!")
        print("\n📝 To fix this:")
        print("1. Get token from @BotFather on Telegram")
        print("2. Run: export TELEGRAM_BOT_TOKEN=your_token_here")
        print("   Or create a .env file with: TELEGRAM_BOT_TOKEN=your_token")
        return

    print("🤖 Starting Telegram bot...")
    print(f"🔑 Token: {token[:10]}...")

    # Create bot application
    app = Application.builder().token(token).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("transcripts", transcripts))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running!")
    print("📱 Open Telegram and find your bot")
    print("⏹️  Press Ctrl+C to stop")
    print()

    # Run the bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
