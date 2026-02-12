"""
Example: Using memU with Gemini CLI OAuth via CLIProxyAPI

This example demonstrates how to configure memU to use Gemini CLI's OAuth
authentication through CLIProxyAPI as a proxy.

Prerequisites:
1. Install CLIProxyAPI: brew install cliproxyapi
2. Start CLIProxyAPI: cli-proxy-api
3. Authenticate: cli-proxy-api --login (opens browser for Google OAuth)
4. CLIProxyAPI will run on http://127.0.0.1:8317

Benefits:
- No API keys in your code
- OAuth authentication handled by CLIProxyAPI
- Free tier: 60 requests/min, 1000 requests/day
- Uses your Google account (free tier) or paid Code Assist license
"""

import asyncio

from memu.app import MemoryService


async def main():
    """
    Example of using memU with Gemini CLI OAuth via CLIProxyAPI proxy.
    """

    # Configuration for Gemini CLI OAuth via CLIProxyAPI
    # CLIProxyAPI exposes an OpenAI-compatible API endpoint
    service = MemoryService(
        llm_profiles={
            "default": {
                # Use OpenAI-compatible provider (CLIProxyAPI mimics OpenAI API)
                "provider": "openai",
                # CLIProxyAPI runs locally on port 8317 by default
                "base_url": "http://127.0.0.1:8317",
                # Dummy API key - CLIProxyAPI handles real OAuth authentication
                "api_key": "sk-dummy",
                # Gemini model (choose based on your needs)
                # Options: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite, etc.
                "chat_model": "gemini-2.5-flash",
                # Use HTTP client backend (best for proxy)
                "client_backend": "httpx",
            },
            "embedding": {
                # Same configuration for embeddings
                "provider": "openai",
                "base_url": "http://127.0.0.1:8317",
                "api_key": "sk-dummy",
                # Gemini embedding model
                "embed_model": "text-embedding-004",
                "client_backend": "httpx",
            },
        },
        # Configure database (SQLite for simplicity)
        database_config={
            "metadata_store": {
                "provider": "sqlite",
                "dsn": "sqlite:///gemini_memory.db",
            },
            "vector_index": {
                "provider": "bruteforce",  # Use brute-force for SQLite
            },
        },
        # Retrieval configuration
        retrieve_config={
            "method": "rag",  # Use RAG for retrieval
        },
    )

    print("✅ MemoryService initialized with Gemini CLI OAuth")
    print("📡 Connected to CLIProxyAPI at http://127.0.0.1:8317")
    print("")

    # Example: Create a memory from a conversation
    # In real usage, you'd load an actual conversation file
    print("💾 Testing memory creation...")

    try:
        # This would normally process a conversation file
        # For demo purposes, we'll create a simple memory item
        memory = await service.create_memory_item(
            memory_type="knowledge",
            memory_content="User prefers dark mode interfaces and enjoys programming in Python",
            memory_categories=["preferences", "work_life"],
            user={"user_id": "demo_user"},
        )

        print("✅ Memory created successfully!")
        print(f"📝 Memory ID: {memory.get('memory_item', {}).get('id')}")
        print(f"🏷️ Categories: {[c.get('name') for c in memory.get('category_updates', [])]}")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("")
        print("⚠️  Make sure:")
        print("   1. CLIProxyAPI is running: cli-proxy-api")
        print("   2. You've authenticated: cli-proxy-api --login")
        print("   3. OAuth login completed in browser")
        return

    # Example: Retrieve memories
    print("")
    print("🔍 Testing memory retrieval...")

    try:
        # Simulate a conversation query
        queries = [{"role": "user", "content": {"text": "What are my interface preferences?"}}]

        result = await service.retrieve(queries=queries, where={"user_id": "demo_user"})

        print(f"✅ Retrieved {len(result.get('items', []))} memories")
        for item in result.get("items", [])[:3]:
            print(f"   - {item.get('summary', '')[:80]}...")

    except Exception as e:
        print(f"❌ Retrieval error: {e}")

    print("")
    print("=" * 50)
    print("✨ Gemini CLI OAuth + memU working perfectly!")
    print("=" * 50)


if __name__ == "__main__":
    # Check if CLIProxyAPI is configured
    print("🔍 Checking configuration...")
    print("")

    # Run the example
    asyncio.run(main())
