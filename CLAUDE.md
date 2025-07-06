# InnerLoop Project Context

## Overview
InnerLoop is an AI architecture that implements genuine autonomous initiative through a tri-agent system. Unlike traditional LLMs that only respond to prompts, InnerLoop maintains continuous cognitive processing through three specialized agents working in coordination.

## Architecture
- **Experiencer Agent**: Primary consciousness and decision-maker (with thinking and tool capabilities)
- **Thoughts Agent**: Autonomous thought generator (produces thoughts every ~60 seconds with reasoning)
- **Attention Director**: Filters and prioritizes information flow (uses reasoning for complex evaluations)

## Technical Stack
- Python 3.12 (NOT 3.13 due to compatibility issues)
- Ollama for local LLM inference (deepseek-r1:8b/14b reasoning model)
- ChromaDB (in-memory) for semantic memory
- SQLite for conversation logging
- Textual for TUI (implemented)
- Pure Python asyncio for concurrency (no Redis, PostgreSQL, or external services)
- Tool system for extended capabilities (memory, time, decisions, reflection)
- Aiofiles for async context logging

## Key Design Decisions
1. **Simplified tech stack**: Everything runs locally in Python
2. **In-memory ChromaDB**: No external database dependencies initially
3. **Async message bus**: Simple Python Queue-based implementation
4. **Configurable prompts**: System prompts stored in markdown files (prompts/ folder)
5. **Thinking model**: DeepSeek-R1 for step-by-step reasoning (separate from context)
6. **Tool system**: Extensible framework for agent capabilities
7. **Organic focus**: Bottom-up attention patterns instead of top-down tasks
8. **Message tagging**: Source tags (<human>, <thoughts>, <attention>) for clarity
9. **Extended context**: 100 messages in memory (configurable) with full 128K model capacity
10. **Context logging**: Each agent logs its context to text files for debugging

## Project Structure
```
innerloop/
├── agents/              # Agent implementations with thinking support
├── tools/               # Tool system (memory, focus, decisions, etc.)
├── memory/              # ChromaDB and SQLite storage
├── communication/       # Message bus
├── prompts/            # Agent system prompts (markdown files)
├── ui/                 # Textual TUI and CLI display
├── logs/               # Agent context logs (gitignored)
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
- ✅ Message source tagging system
- ✅ Text file logging for agent contexts
- ✅ Improved human response times (2-minute guarantee)
- ✅ Extended context window (100 messages)

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
- Thinking processes are shown in the Internal Processing panel but kept separate from context
- Tools are called automatically based on context
- Focus areas emerge organically from sustained attention patterns
- Alex may spontaneously share thoughts during idle periods
- Human messages are guaranteed attention within 2 minutes
- Messages are tagged with source (<human>, <thoughts>, <attention>, etc.)
- Agent contexts are logged to logs/{agent_name}.log for debugging
- Context window is configurable (default: 100 messages)

## Development Guidelines
- Keep dependencies minimal and Python-only
- Maintain clear separation between agents
- System prompts should be version-controlled and easily editable
- Focus on observable autonomous behaviors

## Version Status
This is an **enhanced release** (v0.3.0) with improved human responsiveness and context management:
- DeepSeek-R1 reasoning model for step-by-step thinking
- Comprehensive tool system for extended capabilities
- Organic focus emergence instead of rigid task management
- Spontaneous thought sharing and autonomous behaviors
- Message source tagging for clear context understanding
- Extended context window (100 messages) with full model capacity (128K)
- Text file logging for debugging and analysis
- Improved human response times (2-minute guarantee)

Future versions will include:
- Web search and external information tools
- More sophisticated tool chaining
- Enhanced memory consolidation
- Production deployment features
- Performance optimizations

The core tri-agent concept is proven and working, with genuine reasoning capabilities.

## Recent Improvements (v0.3.0)

### Human Responsiveness
- Queue evaluation reduced from 5 to 2 seconds
- Maximum wait time set to 60 seconds (guarantees response within 2 minutes)
- Messages prioritized based on wait time and relevance

### Message Source Tagging
- All messages now tagged with their source for clarity:
  - `<human>` - External user messages
  - `<thoughts>` - Autonomous thoughts from the Thoughts agent
  - `<attention>` - Filtered content from Attention Director
  - `<experiencer>` - Experiencer's own messages
  - `<sleep>` - Sleep cycle notifications
- Tags help agents understand context and message origins

### Context Management
- Extended context window from 10 to 100 messages (configurable)
- Added `num_ctx: 128000` to utilize full model capacity
- System prompt always preserved at the start of context
- Thinking processes kept separate from conversation context

### Logging System
- Each agent logs its full context to `logs/{agent_name}.log`
- Includes timestamps, roles, and tagged content
- Async file I/O prevents blocking
- Helps with debugging and understanding agent behavior

### Configuration
Key settings in `config.yaml`:
```yaml
model:
  num_ctx: 128000  # Full context window

experiencer:
  context_window_size: 100  # Messages to keep
  queue_evaluation_interval: 2  # Seconds
  max_queue_wait: 60  # Seconds

agent_context_logging:
  enabled: true
  directory: "logs"
```