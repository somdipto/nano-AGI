"""Test that Gemini proxy configuration loads correctly"""

from memu.app import MemoryService


def test_config():
    print("Testing Gemini Proxy Configuration...")
    print("")

    try:
        MemoryService(
            llm_profiles={
                "default": {
                    "provider": "openai",
                    "base_url": "http://127.0.0.1:8317",
                    "api_key": "sk-dummy",
                    "chat_model": "gemini-2.0-flash",
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
                "metadata_store": {"provider": "inmemory"},
                "vector_index": {"provider": "bruteforce"},
            },
        )
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return False
    else:
        print("✅ Configuration loaded successfully!")
        print("")
        print("Details:")
        print("  - Provider: openai (CLIProxyAPI)")
        print("  - Base URL: http://127.0.0.1:8317")
        print("  - Chat Model: gemini-2.0-flash")
        print("  - Embed Model: text-embedding-004")
        print("")
        return True


if __name__ == "__main__":
    success = test_config()
    exit(0 if success else 1)
