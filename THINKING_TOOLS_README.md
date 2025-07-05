# InnerLoop Thinking Models & Tools Integration

This document describes the new thinking model and tool support features added to InnerLoop.

## Overview

InnerLoop now supports DeepSeek-R1:8b, a reasoning model that can think step-by-step through problems and use tools to enhance its capabilities.

## Key Features

### 1. Thinking/Reasoning Mode
- Agents can now use deep reasoning for complex decisions
- Thinking processes are captured separately from responses
- The UI displays reasoning in the Internal Processing panel

### 2. Tool System
Available tools:
- **memory_search**: Deep semantic memory searches
- **focus_analysis**: Analyze and manage focus areas
- **decision_maker**: Make autonomous decisions with criteria
- **reflection**: Deep self-reflection capabilities
- **time_awareness**: Current time/date awareness

### 3. Enhanced Agents
- **Experiencer**: Uses thinking for complex questions and can call tools
- **Stream Generator**: Uses reasoning for insights and focus acknowledgments
- **Attention Director**: Uses reasoning for filtering decisions

### 4. UI Enhancements
- Internal Processing panel shows thinking processes
- Tool calls are displayed in real-time
- Spontaneous thought sharing during idle periods

## Configuration

The system is configured to use DeepSeek-R1:14b by default. Key settings in `config.yaml`:

```yaml
model:
  name: "deepseek-r1:14b"
  thinking:
    enabled: true
    display_thinking: true

tools:
  enabled: true
  available_tools:
    - memory_search
    - focus_analysis
    - decision_maker
    - reflection
    - time_awareness
```

## Testing

Run the test scripts to verify everything is working:

```bash
# Basic Ollama and thinking test
python test_ollama.py

# Comprehensive thinking and tools test
python test_thinking_tools.py

# Start InnerLoop with all features
python main.py
```

## Usage Examples

When chatting with InnerLoop, try these to see thinking in action:

1. **Complex reasoning**: "Why is curiosity important for learning?"
2. **Decision making**: "Should I learn Python or JavaScript first?"
3. **Time awareness**: "What time is it? How long have we been chatting?"
4. **Self-reflection**: "What have you been thinking about lately?"

## Technical Details

### Thinking Mode
- Triggered automatically for complex queries
- Keywords that trigger thinking: why, how, explain, analyze, compare, etc.
- Thinking temperature is higher (0.9) for creative reasoning

### Tool Execution
- Tools are registered per agent
- Tool calls are executed asynchronously
- Results are integrated into responses

### Autonomous Features
- Spontaneous thought sharing after 30 seconds of idle time
- Focus areas emerge organically from sustained attention
- Agents can make autonomous decisions using tools

## Future Enhancements

- Web search tool (optional, for external information)
- More sophisticated tool chaining
- Visual thinking process diagrams
- Tool result caching
- Custom tool development framework