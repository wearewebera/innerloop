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

### 2. The Stream Generator  
- **Role**: Autonomous thought generator
- **Function**: Continuously produces background thoughts, associations, memories, and ideas
- **Analogy**: The stream of consciousness/background mental chatter

### 3. The Attention Director
- **Role**: Cognitive filter and priority manager
- **Function**: Decides what deserves the Experiencer's attention (external input vs internal thoughts)
- **Analogy**: Executive attention/cognitive control system

## How It Works

1. **Continuous Processing**: All three agents run concurrently in async loops

2. **Thought Generation**: Stream Generator produces thoughts every ~60 seconds:
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