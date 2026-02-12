"""Test that streaming works with Gemini proxy"""

import asyncio
import sys


async def test_streaming():
    try:
        from memu.llm.wrapper import LLMClient

        print("Testing Gemini Proxy Streaming...")
        print("")

        client = LLMClient(
            provider="openai", base_url="http://127.0.0.1:8317", api_key="sk-dummy", client_backend="httpx"
        )

        messages = [{"role": "user", "content": "Say hello in 5 words or less"}]

        print("Response: ", end="", flush=True)
        full_response = ""

        async for chunk in client.stream_chat_completion(messages=messages, model="gemini-2.0-flash"):
            print(chunk, end="", flush=True)
            full_response += chunk

        print("")
        print("")

        if full_response:
            print("✅ Streaming works!")
            print(f"   Received {len(full_response)} characters")
            return True
        else:
            print("❌ Streaming failed: No response received")
            return False

    except Exception as e:
        print(f"❌ Streaming test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_streaming())
    sys.exit(0 if success else 1)
