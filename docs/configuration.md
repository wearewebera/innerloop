# Configuration Guide

The `config.yaml` file controls all aspects of the system:

```yaml
model:
  name: "deepseek-r1:14b"     # DeepSeek reasoning model
  temperature: 0.7            # Response creativity (0-1)
  max_tokens: 512             # Max response length
  thinking:
    enabled: true             # Enable step-by-step reasoning
    display_thinking: true    # Show thinking in UI

agents:
  shared_identity:            # Common identity for all agents
    name: "Alex"
    personality: "curious, analytical, thoughtful"
    
  stream_generator:
    thoughts_per_minute: 1    # Autonomous thought frequency
    
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
```

## Configuration Options

### Model Settings
- **name**: The Ollama model to use (must be installed via `ollama pull`)
- **temperature**: Controls response creativity (0 = deterministic, 1 = creative)
- **max_tokens**: Maximum length of generated responses
- **thinking.enabled**: Whether to use reasoning models with step-by-step thinking
- **thinking.display_thinking**: Show thinking process in the UI

### Agent Configuration
- **shared_identity**: Common personality traits shared by all agents
- **stream_generator.thoughts_per_minute**: How often autonomous thoughts are generated
- **attention_director.priority_threshold**: Minimum score for thoughts to pass through
- **attention_director.attention_budget**: Maximum thoughts processed per cycle

### Tool System
- **enabled**: Master switch for the tool system
- **available_tools**: List of tools agents can use autonomously

### Memory Configuration
- **chromadb.collection_name**: Name for the semantic memory collection
- **sqlite.db_path**: Path to conversation history database

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

## Environment Variables

InnerLoop respects these environment variables:

- `OLLAMA_HOST`: Override default Ollama server location (default: http://localhost:11434)
- `INNERLOOP_CONFIG`: Default configuration file path
- `INNERLOOP_LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)