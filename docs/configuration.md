# Configuration Guide

The `config.yaml` file controls all aspects of the system:

```yaml
model:
  name: "deepseek-r1:8b"      # DeepSeek reasoning model (8b or 14b)
  temperature: 0.7            # Response creativity (0-1)
  max_tokens: 512             # Max response length
  num_ctx: 128000             # Context window size in tokens
  thinking:
    enabled: true             # Enable step-by-step reasoning
    display_thinking: true    # Show thinking in UI
    include_in_context: false # Keep thinking separate from context

agents:
  shared_identity:            # Common identity for all agents
    name: "Alex"
    personality: "curious, analytical, thoughtful"
    
  experiencer:
    context_window_size: 100  # Messages to keep in context
    queue_evaluation_interval: 2   # Check queue every N seconds
    max_queue_wait: 60        # Force processing after N seconds
    
  thoughts:
    thoughts_per_minute: 2    # Autonomous thought frequency
    
  attention_director:
    priority_threshold: 0.3   # Min score to pass thoughts
    attention_budget: 5       # Max items per cycle

tools:
  enabled: true               # Enable tool calling
  available_tools:
    - memory_search          # Deep memory searches
    - focus_analysis         # Analyze focus areas
    - decision_maker         # Make autonomous decisions
    - reflection             # Self-reflection
    - time_awareness         # Current time/date

memory:
  chromadb:
    collection_name: "innerloop_memories"
  sqlite:
    db_path: "conversation_history.db"

agent_context_logging:
  enabled: true               # Log agent contexts to files
  directory: "logs"           # Directory for log files
  max_entries: 10000          # Entries before rotation
  include_metadata: true      # Include message metadata
```

## Configuration Options

### Model Settings
- **name**: The Ollama model to use (must be installed via `ollama pull`)
- **temperature**: Controls response creativity (0 = deterministic, 1 = creative)
- **max_tokens**: Maximum length of generated responses
- **num_ctx**: Context window size in tokens (default: 128000 for full capacity)
- **thinking.enabled**: Whether to use reasoning models with step-by-step thinking
- **thinking.display_thinking**: Show thinking process in the UI
- **thinking.include_in_context**: Whether to include thinking in conversation context (default: false)

### Agent Configuration
- **shared_identity**: Common personality traits shared by all agents
- **experiencer.context_window_size**: Number of messages to keep in context (default: 100)
- **experiencer.queue_evaluation_interval**: How often to check message queue in seconds
- **experiencer.max_queue_wait**: Maximum seconds before forcing message processing
- **thoughts.thoughts_per_minute**: How often autonomous thoughts are generated
- **attention_director.priority_threshold**: Minimum score for thoughts to pass through
- **attention_director.attention_budget**: Maximum thoughts processed per cycle

### Tool System
- **enabled**: Master switch for the tool system
- **available_tools**: List of tools agents can use autonomously

### Memory Configuration
- **chromadb.collection_name**: Name for the semantic memory collection
- **sqlite.db_path**: Path to conversation history database

### Context Logging
- **agent_context_logging.enabled**: Enable logging of agent contexts to text files
- **agent_context_logging.directory**: Directory for agent log files (gitignored)
- **agent_context_logging.max_entries**: Maximum log entries before rotation
- **agent_context_logging.include_metadata**: Include message metadata in logs

## Command Line Options

You can override configuration at runtime:

```bash
# Use a custom configuration file
python main.py --config custom_config.yaml

# Select UI mode
python main.py --ui cli      # Simple CLI interface
python main.py --ui tui      # Multi-panel TUI (default)

# View all options
python main.py --help
```

## Message Source Tagging

All messages in the system are tagged with their source for clarity:

- `<human>` - External user messages
- `<thoughts>` - Autonomous thoughts from the Thoughts agent
- `<attention>` - Filtered content from Attention Director  
- `<experiencer>` - Experiencer's own messages
- `<sleep>` - Sleep cycle notifications

These tags help agents understand message context and are included in log files.

## Environment Variables

InnerLoop respects these environment variables:

- `OLLAMA_HOST`: Override default Ollama server location (default: http://localhost:11434)
- `INNERLOOP_CONFIG`: Default configuration file path
- `INNERLOOP_LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)