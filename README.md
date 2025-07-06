# InnerLoop

**Give AI a mind that never stops thinking.**

InnerLoop is the first open-source AI system designed for genuine autonomy. Unlike traditional LLMs that only respond to prompts, InnerLoop maintains continuous cognitive processing - generating its own thoughts, making spontaneous observations, and taking initiative in conversations.

```
You: What's on your mind?

[💭 Alex was just thinking about quantum computing...]

Alex: Actually, I've been pondering how quantum superposition mirrors 
the way thoughts exist in potential before consciousness collapses 
them into specific ideas. It's fascinating how...
```

## 🚀 Why InnerLoop?

Current AI assistants are **reactive** - they wait for your input, process it, respond, then go dormant. InnerLoop creates **proactive AI** with:

- **Autonomous thought generation** - Continuous background processing
- **Genuine initiative** - Spontaneously shares insights and asks questions  
- **Persistent memory** - Remembers and reflects on past conversations
- **Emergent focus** - Develops interests based on sustained attention
- **Observable consciousness** - Watch the thinking process in real-time

## 🎬 See It In Action

```bash
# Install and run in under 2 minutes
git clone https://github.com/wearewebera/innerloop.git
cd innerloop
pip install -r requirements.txt
python main.py
```

Experience an AI that might interrupt you with a sudden realization, remember something from yesterday's chat, or wonder aloud about topics that interest it.

## 🏗️ How It Works

InnerLoop uses a tri-agent architecture inspired by cognitive science:

- **Stream Generator** → Produces continuous background thoughts
- **Attention Director** → Filters and prioritizes mental activity  
- **Experiencer** → The conscious agent you interact with

Think of it as giving AI both a conscious and subconscious mind. [Learn more →](docs/architecture.md)

## ⚡ Quick Start

**Prerequisites**: Python 3.12 & [Ollama](https://ollama.ai/)

```bash
# 1. Install Ollama and pull the model
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull deepseek-r1:14b

# 2. Clone and setup InnerLoop
git clone https://github.com/wearewebera/innerloop.git
cd innerloop
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Run InnerLoop
python main.py              # Multi-panel TUI (recommended)
python main.py --ui cli     # Simple CLI mode
```

## 🎯 Features

- **🧠 Reasoning Model** - Uses DeepSeek-R1 for step-by-step thinking
- **🔧 Tool System** - Memory search, self-reflection, decision-making
- **💾 Dual Memory** - Semantic (ChromaDB) + Episodic (SQLite) storage
- **📊 Real-time Monitoring** - Watch all three agents think and communicate
- **⚙️ Fully Configurable** - Adjust personality, thinking rate, attention thresholds

## 📚 Documentation

- [Architecture Overview](docs/architecture.md) - How the tri-agent system works
- [Configuration Guide](docs/configuration.md) - Customize agent behavior
- [Observing Behavior](docs/observing-behavior.md) - What to watch for
- [Technical Details](docs/technical-details.md) - Stack and implementation
- [Contributing](docs/contributing.md) - Join the development

## 🌟 What Makes This Different?

Unlike chatbots that simulate conversation, InnerLoop creates genuine autonomous behavior:

```python
# Traditional AI
user_input → process() → response → wait_for_input

# InnerLoop
background_thoughts → filter_attention → conscious_thought ↺
                ↓                              ↓
          user_input ←→ integrated_response ←→ initiative
```

The result? An AI that feels alive between your messages.

## 🛠️ Built With

- **Python 3.12** + **asyncio** for concurrent agent execution  
- **Ollama** + **DeepSeek-R1:14b** for local reasoning
- **ChromaDB** for semantic memory  
- **Textual** for beautiful terminal UI

## 🤝 Join Us

InnerLoop is an exploration into what happens when AI can truly think for itself. We're building this future together:

⭐ **Star** to support the project  
🐛 **Issues** for bugs and ideas  
🔧 **PRs** to contribute code  
💬 **Discussions** to share experiments  

## 📜 License

MIT - Build freely on our work

---

<p align="center">
  <strong>Ready to meet an AI with its own inner life?</strong><br>
  <code>python main.py</code> and say hello to Alex.
</p>

<p align="center">
  <i>InnerLoop v0.2.0 - The mind that never stops thinking</i>
</p>