# InnerLoop Architecture

## Core Concept

Current LLMs are purely reactive - they only activate when given input. InnerLoop creates an autonomous cognitive loop where AI agents can:

- Generate spontaneous thoughts and ideas
- Take initiative in conversations and decision-making  
- Maintain continuous background processing
- Develop genuine preferences and autonomous behaviors

## Architecture Overview

InnerLoop consists of three specialized agents working in coordination:

### 1. The Experiencer Agent
- **Role**: Primary consciousness/decision-maker
- **Function**: Processes information, makes final decisions, handles external interactions
- **Analogy**: The "conscious mind" that experiences and decides

### 2. The Thoughts Agent  
- **Role**: Autonomous thought generator
- **Function**: Continuously produces background thoughts, associations, memories, and ideas
- **Analogy**: The stream of consciousness/background mental chatter

### 3. The Attention Director
- **Role**: Cognitive filter and priority manager
- **Function**: Decides what deserves the Experiencer's attention (external input vs internal thoughts)
- **Analogy**: Executive attention/cognitive control system

## How It Works

1. **Continuous Processing**: All three agents run concurrently in async loops

2. **Thought Generation**: Thoughts agent produces thoughts every ~60 seconds:
   - Associations with recent topics (using reasoning for focused areas)
   - Memory recalls
   - Wonderings and reflections
   - Deep insights using step-by-step thinking
   - Focus acknowledgments when new themes emerge

3. **Attention Management**: Attention Director evaluates each thought for:
   - Relevance to current context (using reasoning for complex evaluations)
   - Urgency and importance
   - Novelty compared to recent thoughts
   - Emotional significance
   - Focus area alignment and organic theme emergence

4. **Conscious Processing**: Experiencer integrates high-priority thoughts and:
   - Responds to user input (using deep thinking for complex questions)
   - Makes decisions using tool assistance
   - Updates memory with enhanced metadata
   - Maintains conversation flow
   - Shares spontaneous thoughts during idle periods

5. **Memory Integration**: 
   - ChromaDB stores and retrieves semantic memories
   - SQLite logs all conversations and agent interactions
   - Agents reference past experiences autonomously

## Project Structure

```
innerloop/
├── agents/
│   ├── base_agent.py          # Shared agent functionality with thinking
│   ├── experiencer.py         # Primary consciousness agent
│   ├── stream_generator.py    # Background thought generator
│   └── attention_director.py  # Priority manager with reasoning
├── tools/
│   ├── base_tool.py          # Tool system foundation
│   ├── registry.py           # Tool discovery and management
│   ├── memory_tools.py       # Memory search and storage
│   ├── focus_tools.py        # Focus area analysis
│   ├── decision_tools.py     # Autonomous decision making
│   ├── reflection_tools.py   # Self-reflection capabilities
│   └── time_tools.py         # Time awareness
├── memory/
│   ├── chromadb_store.py     # In-memory semantic search
│   └── conversation_log.py   # SQLite conversation history
├── communication/
│   └── message_bus.py        # Async inter-agent messaging
├── ui/
│   └── innerloop_tui.py      # Multi-panel Textual interface
├── prompts/                  # Agent system prompts
│   ├── shared_identity.md    # Common identity
│   ├── experiencer.md        # Experiencer role
│   ├── stream_generator.md   # Stream generator role
│   └── attention_director.md # Attention director role
├── config.yaml               # System configuration
├── main.py                   # Entry point
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```
## Message Flow & Tagging

All messages in the system are now tagged with their source for clarity:

### Message Source Tags
- **`<human>`** - External user messages
- **`<thoughts>`** - Autonomous thoughts from the Thoughts agent  
- **`<attention>`** - Filtered content from Attention Director
- **`<experiencer>`** - Experiencer's own messages or reflections
- **`<sleep>`** - Sleep cycle notifications

### Context Management
- Each agent maintains a configurable context window (default: 100 messages)
- System prompts are always preserved at the start of the context
- Thinking processes are kept separate from conversation context
- Full model context capacity (128K tokens) is utilized

### Human Responsiveness
- Queue evaluation every 2 seconds (was 5 seconds)
- Maximum wait time of 60 seconds guarantees response
- Priority boost for messages waiting longer
- Contextual evaluation for immediate processing

## Logging & Debugging

### Context Logging
Each agent logs its full context to text files:
- `logs/experiencer.log` - Primary consciousness context
- `logs/thoughts.log` - Autonomous thought generation
- `logs/attention_director.log` - Attention filtering decisions
- `logs/sleep_agent.log` - Sleep cycle activities

### Log Format
```
[2025-07-06T12:34:56] [USER]
<human>
What are you thinking about?
</human>
================================================================================

[2025-07-06T12:34:58] [ASSISTANT]
I'm currently experimenting with the concept of emergence...
================================================================================
```

## Configuration

Key settings in `config.yaml`:

```yaml
model:
  num_ctx: 128000           # Use full context window

experiencer:
  context_window_size: 100  # Messages to keep in memory
  queue_evaluation_interval: 2
  max_queue_wait: 60

thoughts:
  thoughts_per_minute: 2

agent_context_logging:
  enabled: true
  directory: "logs"
```
