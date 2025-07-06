# Technical Details

## Technical Stack

- **Python 3.12** (avoiding 3.13 compatibility issues)
- **Ollama** for local LLM inference
- **DeepSeek-R1:14b** reasoning model with thinking capabilities
- **ChromaDB** (in-memory) for semantic memory search
- **SQLite** for conversation logging
- **Textual** for multi-panel terminal UI
- **asyncio** for concurrent agent execution
- **Tool System** for extended capabilities

## Prerequisites

- Python 3.12
- [Ollama](https://ollama.ai/) installed and running
- At least 8GB RAM (16GB recommended)
- Compatible LLM model downloaded via Ollama

```bash
# Install Ollama and download the reasoning model
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull deepseek-r1:14b
```

## Installation

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

# Test Ollama connection
python test_ollama.py
```

## Tool System

InnerLoop's tool system provides agents with extended capabilities:

- **memory_search**: Deep semantic searches through conversation history
- **focus_analysis**: Analyze emerging focus areas and themes
- **decision_maker**: Make autonomous decisions based on context
- **reflection**: Self-reflection and metacognitive processing
- **time_awareness**: Current time and date information

Tools are called automatically by agents based on context and need.

## Memory Architecture

### ChromaDB (Semantic Memory)
- In-memory vector database for fast semantic search
- Stores conversation snippets with embeddings
- Enables associative memory recalls
- No persistence in current version (planned for future)

### SQLite (Conversation Log)
- Persistent storage of all conversations
- Full agent interaction history
- Structured queries for specific events
- Used for long-term memory consolidation

## Async Message Bus

The communication system uses Python's asyncio:
- Queue-based message passing between agents
- Non-blocking async operations
- Priority-based message handling
- Real-time performance metrics

## Development Principles

1. **Minimal Dependencies**: Keep the stack Python-only where possible
2. **Local First**: Everything runs on the user's machine
3. **Observable Behavior**: All agent activity is visible in logs/UI
4. **Configurable**: Behavior controlled through config files and prompts
5. **Extensible**: Easy to add new tools and capabilities