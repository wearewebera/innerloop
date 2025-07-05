# InnerLoop Project Context

## Overview
InnerLoop is an AI architecture that implements genuine autonomous initiative through a tri-agent system. Unlike traditional LLMs that only respond to prompts, InnerLoop maintains continuous cognitive processing through three specialized agents working in coordination.

## Architecture
- **Experiencer Agent**: Primary consciousness and decision-maker
- **Stream Generator**: Autonomous thought generator (produces thoughts every ~20 seconds)
- **Attention Director**: Filters and prioritizes information flow

## Technical Stack
- Python 3.12 (NOT 3.13 due to compatibility issues)
- Ollama for local LLM inference (gemma3:27b-it-qat model)
- ChromaDB (in-memory) for semantic memory
- SQLite for conversation logging
- Textual for TUI (pending implementation)
- Pure Python asyncio for concurrency (no Redis, PostgreSQL, or external services)

## Key Design Decisions
1. **Simplified tech stack**: Everything runs locally in Python
2. **In-memory ChromaDB**: No external database dependencies initially
3. **Async message bus**: Simple Python Queue-based implementation
4. **Configurable prompts**: System prompts stored in markdown files (prompts/ folder)

## Project Structure
```
innerloop/
├── agents/              # Agent implementations
├── memory/              # ChromaDB and SQLite storage
├── communication/       # Message bus
├── prompts/            # Agent system prompts (markdown files)
├── ui/                 # Textual TUI (pending)
├── config.yaml         # Configuration
├── main.py            # Entry point
└── requirements.txt   # Dependencies
```

## Current Status
- ✅ Core tri-agent architecture implemented
- ✅ Async message passing working
- ✅ Memory systems integrated
- ✅ Basic CLI interface functional
- 🔄 Prompts being moved to separate files
- 📋 Textual UI pending

## Running the Project
```bash
# Ensure Python 3.12 and Ollama are installed
pip install -r requirements.txt
python test_ollama.py  # Verify Ollama connection
python main.py         # Start InnerLoop
```

## Important Notes
- The system generates autonomous thoughts continuously
- Watch the logs to see inter-agent communication
- Each agent has a configurable system prompt in prompts/ folder
- Memory persists in SQLite but ChromaDB is in-memory for now

## Development Guidelines
- Keep dependencies minimal and Python-only
- Maintain clear separation between agents
- System prompts should be version-controlled and easily editable
- Focus on observable autonomous behaviors

## Version Status
This is an **initial proof-of-concept release** (v0.1.0). The architecture is functional but will undergo significant improvements. Future versions will include:
- More sophisticated agent behaviors
- Enhanced memory and learning capabilities
- Better tool integration (MCP)
- Production deployment features
- Performance optimizations

The core tri-agent concept is proven and working, but much development is planned.