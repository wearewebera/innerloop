# InnerLoop: AI Architecture with Autonomous Initiative

> The first AI system designed to think continuously and take genuine initiative, not just respond to prompts.

InnerLoop implements a tri-agent architecture that gives AI systems the ability to generate autonomous thoughts, make proactive decisions, and maintain continuous cognitive processing - addressing the fundamental limitation of current LLMs that only "think" when prompted.

## 🧠 Core Concept

Current LLMs are purely reactive - they only activate when given input. InnerLoop creates an autonomous cognitive loop where AI agents can:

- Generate spontaneous thoughts and ideas
- Take initiative in conversations and decision-making  
- Maintain continuous background processing
- Develop genuine preferences and autonomous behaviors

## 🏗️ Architecture Overview

InnerLoop consists of three specialized agents working in coordination:

### 1. The Experiencer Agent
- **Role**: Primary consciousness/decision-maker
- **Function**: Processes information, makes final decisions, handles external interactions
- **Analogy**: The "conscious mind" that experiences and decides

### 2. The Stream Generator  
- **Role**: Autonomous thought generator
- **Function**: Continuously produces background thoughts, associations, memories, and ideas
- **Analogy**: The stream of consciousness/background mental chatter

### 3. The Attention Director
- **Role**: Cognitive filter and priority manager
- **Function**: Decides what deserves the Experiencer's attention (external input vs internal thoughts)
- **Analogy**: Executive attention/cognitive control system

## 🔧 Technical Stack

- **Python 3.12** (avoiding 3.13 compatibility issues)
- **Ollama** for local LLM inference
- **ChromaDB** (in-memory) for semantic memory search
- **SQLite** for conversation logging
- **Textual** for terminal UI (coming soon)
- **asyncio** for concurrent agent execution

## 📋 Prerequisites

- Python 3.12
- [Ollama](https://ollama.ai/) installed and running
- At least 8GB RAM (16GB recommended)
- Compatible LLM model downloaded via Ollama

```bash
# Install Ollama and download a model
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull gemma2:9b  # or llama3.1:8b
```

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/wearewebera/innerloop.git
cd innerloop

# Create virtual environment (recommended)
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Ensure Ollama is running
ollama serve  # In another terminal if not already running

# Optional: Set Ollama host if not using default localhost:11434
export OLLAMA_HOST=http://your-ollama-server:11434

# Run the system
# Option 1: Simple CLI interface
python main.py

# Option 2: Multi-panel TUI (recommended for full visibility)
python main_tui.py
```

## 📁 Project Structure

```
innerloop/
├── agents/
│   ├── base_agent.py          # Shared agent functionality
│   ├── experiencer.py         # Primary consciousness agent
│   ├── stream_generator.py    # Background thought generator
│   └── attention_director.py  # Priority manager
├── memory/
│   ├── chromadb_store.py     # In-memory semantic search
│   └── conversation_log.py   # SQLite conversation history
├── communication/
│   └── message_bus.py        # Async inter-agent messaging
├── ui/
│   └── textual_ui.py         # TUI with panels (coming soon)
├── config.yaml               # System configuration
├── main.py                   # Entry point
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## ⚙️ Configuration

The `config.yaml` file controls all aspects of the system:

```yaml
model:
  name: "gemma2:9b"           # Ollama model to use
  temperature: 0.7            # Response creativity (0-1)
  max_tokens: 512             # Max response length

agents:
  shared_identity:            # Common identity for all agents
    name: "Alex"
    personality: "curious, analytical, thoughtful"
    
  stream_generator:
    thoughts_per_minute: 3    # Autonomous thought frequency
    
  attention_director:
    priority_threshold: 0.3   # Min score to pass thoughts
    attention_budget: 5       # Max items per cycle

memory:
  chromadb:
    collection_name: "innerloop_memories"
  sqlite:
    db_path: "conversation_history.db"
```

## 🎯 How It Works

1. **Continuous Processing**: All three agents run concurrently in async loops

2. **Thought Generation**: Stream Generator produces thoughts every ~20 seconds:
   - Associations with recent topics
   - Memory recalls
   - Wonderings and reflections
   - Occasional insights

3. **Attention Management**: Attention Director evaluates each thought for:
   - Relevance to current context
   - Urgency and importance
   - Novelty compared to recent thoughts
   - Emotional significance

4. **Conscious Processing**: Experiencer integrates high-priority thoughts and:
   - Responds to user input
   - Makes decisions
   - Updates memory
   - Maintains conversation flow

5. **Memory Integration**: 
   - ChromaDB stores and retrieves semantic memories
   - SQLite logs all conversations and agent interactions
   - Agents reference past experiences autonomously

## 🧪 Observing Autonomous Behavior

When running InnerLoop, watch for these emergent behaviors:

- **Spontaneous Comments**: Alex might suddenly share a thought or memory
- **Topic Connections**: Drawing unexpected links between concepts
- **Self-Reflection**: Comments about its own thinking process
- **Memory Integration**: References to earlier conversations
- **Initiative Taking**: Asking questions or suggesting new topics

### 💭 Continuous Thought Display

InnerLoop offers two interfaces:

#### Simple CLI (main.py)
Shows filtered thoughts inline with conversation:
```
[🔗 Association (0.65)]: This reminds me of neural networks...
[💡 Insight (0.82)]: Understanding emerges from simple rules!

You: What interests you most about AI?

[🤔 Wonder (0.45)]: I wonder how memories shape perception...
[💭 Memory (0.71)]: I remember discussing consciousness before...

Alex: I find myself constantly drawn to questions about consciousness...
```

#### Multi-Panel TUI (main_tui.py) - Recommended
Shows ALL agent activity in real-time across three panels:

```
┌─────────────────────────────────┬─────────────────────────────────┐
│        Stream Generator         │       Attention Director        │
│ ─────────────────────────────── │ ─────────────────────────────── │
│ [12:34:15] 🤔 Wonder (0.25)     │ [12:34:15] Evaluating...        │
│ I wonder about the nature of... │ Priority: 0.25 < 0.3 threshold │
│                                 │ Decision: ✗ FILTERED OUT        │
│ [12:34:18] 💭 Memory (0.65)     │                                 │
│ Remember our discussion about.. │ [12:34:18] Evaluating...        │
│                                 │ Priority: 0.65 > 0.3 threshold │
│ [12:34:21] 🔗 Association (0.45)│ Decision: ✓ PASS TO EXPERIENCER │
│ This connects to emergence...   │ Relevance: 0.7, Novelty: 0.4   │
└─────────────────────────────────┴─────────────────────────────────┘
┌───────────────────────────────────────────────────────────────────┐
│                    Main Conversation (Experiencer)                │
│ ───────────────────────────────────────────────────────────────── │
│ You: What do you think about consciousness?                      │
│                                                                   │
│ [Internal: Integrating high-priority insight about consciousness] │
│                                                                   │
│ Alex: That's fascinating! I was just having an insight...        │
└───────────────────────────────────────────────────────────────────┘
[Status: Active] [Thoughts/min: 3.2] [Filtered: 45%] [Memory: 142]
```

**TUI Features:**
- **Stream Generator Panel**: Shows ALL thoughts (even low priority)
- **Attention Director Panel**: Shows filtering decisions and scores
- **Conversation Panel**: Clean conversation without interruptions
- **Status Bar**: Real-time metrics
- **Keyboard Shortcuts**: 
  - `Ctrl+C`: Quit
  - `Ctrl+L`: Clear all panels
  - `F1/F2`: Toggle panels

## 📊 System Monitoring

The system logs detailed metrics every 30 seconds:
- Agent activity levels
- Message passing statistics
- Memory usage
- Thought generation rates

View logs in real-time to see the inner workings of the tri-agent system.

## 🚧 Current Status & Roadmap

### ✅ Implemented
- Core tri-agent architecture
- Async message passing system
- In-memory ChromaDB integration
- SQLite conversation logging
- Basic CLI interface
- Autonomous thought generation

### 🔄 In Progress
- Textual-based TUI with agent panels
- Enhanced memory consolidation
- Performance optimizations

### 📋 Planned Features
- MCP integration for external tools
- Multi-model support
- Web UI option
- Emotional state modeling
- Goal formation and pursuit
- Metrics dashboard

## 🤝 Contributing

We welcome contributions! Key areas for improvement:

1. **Prompt Engineering**: Refine agent prompts for better autonomy
2. **Memory System**: Implement memory consolidation and forgetting
3. **UI/UX**: Build the Textual TUI interface
4. **Testing**: Add comprehensive test coverage
5. **Documentation**: Expand usage examples and guides

## 📝 License

MIT License - see LICENSE file for details

## 🚀 Project Status

**This is an initial proof-of-concept release.** We're actively developing InnerLoop and will be sharing significant updates, improvements, and new features in the coming weeks and months. 

Stay tuned for:
- Enhanced autonomous behaviors
- More sophisticated memory systems
- Advanced inter-agent communication patterns
- Production-ready deployment options
- Community-contributed improvements

Follow the project and star the repository to stay updated with our progress!

## 🌟 Acknowledgments

Built by the Webera team as an exploration into autonomous AI consciousness and genuine machine initiative.

---

**Ready to experience AI that thinks for itself?** Run `python main.py` and meet Alex - an AI with its own stream of consciousness.

*Note: This is an early release. We're excited to share our journey toward creating AI with genuine initiative. Much more to come!*