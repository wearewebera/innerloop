# InnerLoop Project Context

## Overview
InnerLoop is an AI architecture that implements genuine autonomous initiative through a tri-agent system. Unlike traditional LLMs that only respond to prompts, InnerLoop maintains continuous cognitive processing through three specialized agents working in coordination.

## Architecture
- **Experiencer Agent**: Primary consciousness and decision-maker (with thinking and tool capabilities)
- **Stream Generator**: Autonomous thought generator (produces thoughts every ~60 seconds with reasoning)
- **Attention Director**: Filters and prioritizes information flow (uses reasoning for complex evaluations)

## Technical Stack
- Python 3.12 (NOT 3.13 due to compatibility issues)
- Ollama for local LLM inference (deepseek-r1:14b reasoning model)
- ChromaDB (in-memory) for semantic memory
- SQLite for conversation logging
- Textual for TUI (implemented)
- Pure Python asyncio for concurrency (no Redis, PostgreSQL, or external services)
- Tool system for extended capabilities (memory, time, decisions, reflection)

## Key Design Decisions
1. **Simplified tech stack**: Everything runs locally in Python
2. **In-memory ChromaDB**: No external database dependencies initially
3. **Async message bus**: Simple Python Queue-based implementation
4. **Configurable prompts**: System prompts stored in markdown files (prompts/ folder)
5. **Thinking model**: DeepSeek-R1 for step-by-step reasoning
6. **Tool system**: Extensible framework for agent capabilities
7. **Organic focus**: Bottom-up attention patterns instead of top-down tasks

## Project Structure
```
innerloop/
├── agents/              # Agent implementations with thinking support
├── tools/               # Tool system (memory, focus, decisions, etc.)
├── memory/              # ChromaDB and SQLite storage
├── communication/       # Message bus
├── prompts/            # Agent system prompts (markdown files)
├── ui/                 # Textual TUI and CLI display
├── config.yaml         # Configuration
├── main.py            # Entry point
└── requirements.txt   # Dependencies
```

## Current Status
- ✅ Core tri-agent architecture implemented
- ✅ Async message passing working
- ✅ Memory systems integrated
- ✅ Basic CLI interface functional
- ✅ Multi-panel Textual TUI implemented
- ✅ DeepSeek-R1 thinking model integrated
- ✅ Tool system implemented (memory, focus, decisions, reflection, time)
- ✅ Organic focus areas emergence
- ✅ Spontaneous thought sharing
- ✅ Step-by-step reasoning display

## Running the Project
```bash
# Ensure Python 3.12 and Ollama are installed
pip install -r requirements.txt
python test_ollama.py  # Verify Ollama connection
python main.py         # Start InnerLoop (TUI mode)
python main.py --ui cli  # Start InnerLoop (CLI mode)
```

## Important Notes
- The system generates autonomous thoughts continuously
- Watch the logs to see inter-agent communication
- Each agent has a configurable system prompt in prompts/ folder
- Memory persists in SQLite but ChromaDB is in-memory for now
- Thinking processes are shown in the Internal Processing panel
- Tools are called automatically based on context
- Focus areas emerge organically from sustained attention patterns
- Alex may spontaneously share thoughts during idle periods

## Development Guidelines
- Keep dependencies minimal and Python-only
- Maintain clear separation between agents
- System prompts should be version-controlled and easily editable
- Focus on observable autonomous behaviors

## Version Status
This is an **enhanced release** (v0.2.0) with thinking models and tools. The architecture now features:
- DeepSeek-R1 reasoning model for step-by-step thinking
- Comprehensive tool system for extended capabilities
- Organic focus emergence instead of rigid task management
- Spontaneous thought sharing and autonomous behaviors

Future versions will include:
- Web search and external information tools
- More sophisticated tool chaining
- Enhanced memory consolidation
- Production deployment features
- Performance optimizations

The core tri-agent concept is proven and working, with genuine reasoning capabilities.