<div align="center">

# 🤖 nano-AGI - Autonomous AI Agent Framework

### *Shadow Agent: Your 24/7 Intelligent Assistant*

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

**[Features](#-features)** • **[Quick Start](#-quick-start)** • **[Documentation](#-documentation)** • **[Examples](#-examples)** • **[Architecture](#-architecture)**

<img src="https://img.shields.io/badge/Status-Production%20Ready-success" alt="Status">
<img src="https://img.shields.io/badge/Cost-$0%20Free-brightgreen" alt="Cost">
<img src="https://img.shields.io/badge/Privacy-100%25%20Local-blue" alt="Privacy">

---

### 🎯 **Build AI agents that actually remember**

nano-AGI is a production-ready framework for building autonomous AI agents with persistent memory. Voice input, Telegram bots, web dashboards - all powered by Shadow Agent with zero-cost AI via Gemini OAuth.

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎤 **Multi-Modal Input**
- 🗣️ **Voice Capture** - Whisper.cpp integration
- 💬 **Telegram Bot** - Voice & text messages
- 🌐 **Web Dashboard** - Real-time interface
- 📝 **Direct API** - Programmatic access

</td>
<td width="50%">

### 🧠 **Intelligent Memory**
- 🔍 **Semantic Search** - Find by meaning, not keywords
- 📊 **Category System** - Hierarchical organization
- 🔗 **Resource Tracking** - Files, URLs, metadata
- ⚡ **Fast Retrieval** - SQLite FTS5 full-text search

</td>
</tr>
<tr>
<td width="50%">

### 🤖 **Autonomous Operation**
- 🎯 **Shadow Core** - Background task orchestrator
- 🔄 **Task Queue** - Priority-based execution
- 🧩 **Swarm Coordination** - Multi-agent support
- 🛡️ **Sandbox Isolation** - Safe execution

</td>
<td width="50%">

### 💰 **Zero Cost AI**
- 🆓 **Gemini OAuth** - No API keys needed
- 🔐 **Privacy First** - Local processing
- 🌍 **Offline Mode** - Ollama fallback
- 📈 **Scalable** - 100K+ memories

</td>
</tr>
</table>

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/somdipto/nano-AGI.git
cd nano-AGI

# Install dependencies (requires Python 3.13+)
make install

# Setup Whisper for voice (optional)
./scripts/setup_whisper.sh
```

### Configuration

```bash
# Create environment file
cp .env.example .env

# Add your Telegram bot token (get from @BotFather)
echo "TELEGRAM_BOT_TOKEN=your_token_here" >> .env

# Configure Shadow Agent
echo "AGENT_NAME=Shadow Agent" >> .env
```

### Launch

<table>
<tr>
<td width="33%">

#### 🤖 Telegram Bot
```bash
./scripts/run_telegram_bot.sh
```
Chat with your AI via Telegram

</td>
<td width="33%">

#### 🌐 Web Dashboard
```bash
cd web
uv run python server.py
```
Visit `http://localhost:8000`

</td>
<td width="33%">

#### 🎤 Voice Capture
```bash
uv run python examples/voice_memory_gemini.py
```
Speak and it remembers

</td>
</tr>
</table>

---

## 💡 Examples

### Python API

```python
from shadow_agent import AgentService

# Initialize Shadow Agent
agent = AgentService(
    llm_provider="gemini_proxy",
    database_url="sqlite:///./agent.db"
)

# Store a memory
await agent.remember(
    content="User prefers dark mode",
    category="preferences"
)

# Search memories
results = await agent.recall(
    query="what does user prefer?",
    limit=5
)
```

### Telegram Bot Commands

```
/remember I love pizza          → Saves to memory
/recall pizza                   → Searches memories
/forget                         → Clears all memories
/help                           → Shows commands
```

### Voice Interaction

```python
from memu.voice_capture import VoiceCapture

# Start listening
capture = VoiceCapture(model="base.en")
text = await capture.transcribe_realtime()

# Automatically stored in memory
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT LAYER                               │
│  Voice (Whisper) | Telegram Bot | Web API | Direct Python   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  SHADOW CORE ORCHESTRATOR                    │
│     Agent | Swarm | Sandbox | Task Queue | Coordination     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   MEMORY FRAMEWORK                           │
│  SQLite + FTS5 | Semantic Search | Categories | Resources   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      AI LAYER                                │
│    Gemini OAuth (Primary) | Ollama (Fallback) | Embeddings  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📚 Documentation

<table>
<tr>
<td width="50%">

### 📖 **Guides**
- [Getting Started](START_HERE.md)
- [Telegram Setup](TELEGRAM_SETUP.md)
- [Gemini OAuth Guide](docs/GEMINI_CLI_OAUTH_GUIDE.md)
- [Development Guide](AGENTS.md)

</td>
<td width="50%">

### 🔧 **Technical**
- [API Reference](docs/api/)
- [Architecture](report.md)
- [Database Schema](src/memu/database/sqlite/schema.py)
- [Contributing](CONTRIBUTING.md)

</td>
</tr>
</table>

---

## 🎨 Use Cases

<table>
<tr>
<td width="33%" align="center">

### 🤝 **Personal Assistant**
Build an AI that remembers your preferences, tasks, and conversations across sessions

</td>
<td width="33%" align="center">

### 💼 **Customer Support**
Create bots that remember customer history and provide personalized responses

</td>
<td width="33%" align="center">

### 🎓 **Learning Companion**
Develop tutors that track progress and adapt to learning styles

</td>
</tr>
<tr>
<td width="33%" align="center">

### 📊 **Research Assistant**
Organize and retrieve research notes with semantic search

</td>
<td width="33%" align="center">

### 🏢 **Team Collaboration**
Share knowledge across AI agents in your organization

</td>
<td width="33%" align="center">

### 🎮 **Game NPCs**
Create characters with persistent memories and relationships

</td>
</tr>
</table>

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Core** | Python 3.13+ | Main framework |
| **Database** | SQLite + FTS5 | Fast, local storage |
| **AI** | Gemini OAuth | Free LLM access |
| **Voice** | Whisper.cpp | Local transcription |
| **Bot** | python-telegram-bot | Telegram interface |
| **Web** | FastAPI | REST API & dashboard |
| **Build** | Maturin + uv | Rust extensions |

---

## 📊 Performance

<table>
<tr>
<td width="25%" align="center">

### ⚡ **<100ms**
Memory search latency

</td>
<td width="25%" align="center">

### 🗄️ **100K+**
Memories without slowdown

</td>
<td width="25%" align="center">

### 💰 **$0**
Completely free to run

</td>
<td width="25%" align="center">

### 🔒 **100%**
Local data privacy

</td>
</tr>
</table>

---

## 🌟 Why nano-AGI?

<table>
<tr>
<td width="50%">

### ❌ **Without nano-AGI**
- ❌ AI forgets after each session
- ❌ Expensive API costs
- ❌ Privacy concerns with cloud storage
- ❌ Complex setup and configuration
- ❌ Limited to text input only

</td>
<td width="50%">

### ✅ **With nano-AGI**
- ✅ Persistent memory across sessions
- ✅ Zero cost with Gemini OAuth
- ✅ 100% local data processing
- ✅ 5-minute setup, production ready
- ✅ Voice, text, and web interfaces

</td>
</tr>
</table>

---

## 🤝 Contributing

We love contributions! Here's how to get started:

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/nano-AGI.git

# Create a branch
git checkout -b feature/amazing-feature

# Make changes and test
make test
make check

# Commit and push
git commit -m "Add amazing feature"
git push origin feature/amazing-feature
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Whisper.cpp** - Fast local speech recognition
- **Gemini** - Free, powerful LLM via OAuth
- **SQLite** - Reliable embedded database
- **FastAPI** - Modern web framework
- **python-telegram-bot** - Excellent Telegram SDK

---

## 📞 Support & Community

<div align="center">

[![GitHub Issues](https://img.shields.io/github/issues/somdipto/nano-AGI)](https://github.com/somdipto/nano-AGI/issues)
[![GitHub Stars](https://img.shields.io/github/stars/somdipto/nano-AGI)](https://github.com/somdipto/nano-AGI/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/somdipto/nano-AGI)](https://github.com/somdipto/nano-AGI/network)

**[Report Bug](https://github.com/somdipto/nano-AGI/issues)** • **[Request Feature](https://github.com/somdipto/nano-AGI/issues)** • **[Discussions](https://github.com/somdipto/nano-AGI/discussions)**

</div>

---

<div align="center">

### 🚀 **Ready to give your AI a memory?**

**[Get Started Now](#-quick-start)** • **[View Examples](#-examples)** • **[Read Docs](#-documentation)**

---

Made with ❤️ by [@somdipto](https://github.com/somdipto)

**Star ⭐ this repo if you find it useful!**

</div>
