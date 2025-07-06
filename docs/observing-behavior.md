# Observing Autonomous Behavior

When running InnerLoop, watch for these emergent behaviors:

- **Spontaneous Comments**: Alex might suddenly share a thought or memory
- **Topic Connections**: Drawing unexpected links between concepts
- **Self-Reflection**: Comments about its own thinking process
- **Memory Integration**: References to earlier conversations
- **Initiative Taking**: Asking questions or suggesting new topics

## Continuous Thought Display

InnerLoop offers two interfaces:

### Simple CLI Mode (`python main.py --ui cli`)
Shows filtered thoughts inline with conversation:
```
[🔗 Association (0.65)]: This reminds me of neural networks...
[💡 Insight (0.82)]: Understanding emerges from simple rules!

You: What interests you most about AI?

[🤔 Wonder (0.45)]: I wonder how memories shape perception...
[💭 Memory (0.71)]: I remember discussing consciousness before...

Alex: I find myself constantly drawn to questions about consciousness...
```

### Multi-Panel TUI Mode (`python main.py`) - Default & Recommended
Shows ALL agent activity in real-time across four panels:

```
┌─────────────────────────┬─────────────────────────┬─────────────────────────┐
│   Stream Generator      │   Attention Director    │  Internal Processing    │
│ ────────────────────── │ ────────────────────── │ ────────────────────── │
│ [12:34:15] 🤔 Wonder   │ [12:34:15] Evaluating.. │ 💭 Processing user      │
│ I wonder about the     │ Priority: 0.25 < 0.3    │ query about conscious-  │
│ nature of...           │ Decision: ✗ FILTERED    │ ness...                 │
│                        │                         │                         │
│ [12:34:18] 💭 Memory   │ [12:34:18] Evaluating.. │ 🧠 Reasoning: Let me    │
│ Remember our discuss-  │ Priority: 0.65 > 0.3    │ think step by step...   │
│ ion about emergence... │ Decision: ✓ PASS        │                         │
│                        │ Relevance: 0.7          │ 🔧 Tool: time_awareness │
│ [12:34:21] 🔗 Assoc.   │                         │ Current time: 12:34 PM  │
│ This connects to...    │ [12:34:21] Evaluating.. │                         │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Main Conversation                              │
│ ─────────────────────────────────────────────────────────────────────────── │
│ You: What do you think about consciousness?                                │
│                                                                             │
│ Alex: That's fascinating! I was just having an insight about how           │
│ consciousness might emerge from simple rules, similar to how complex        │
│ patterns arise in neural networks...                                        │
│                                                                             │
│ You: _                                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
[Status: Active] [Thoughts/min: 3.2] [Filtered: 45%] [Memory: 142] [Uptime: 00:05:23]
```

### TUI Features:
- **Stream Generator Panel**: Shows ALL thoughts (even low priority)
- **Attention Director Panel**: Shows filtering decisions and scores
- **Conversation Panel**: Clean conversation between user and Alex
- **Internal Processing Panel**: Shows internal thoughts and processing
- **Status Bar**: Real-time metrics
- **Keyboard Shortcuts**: 
  - `Ctrl+C`: Quit
  - `Ctrl+L`: Clear all panels
  - `F1`: Toggle Stream Generator panel
  - `F2`: Toggle Attention Director panel
  - `F3`: Toggle Internal Processing panel

## System Monitoring

The system logs detailed metrics every 30 seconds:
- Agent activity levels
- Message passing statistics
- Memory usage
- Thought generation rates

View logs in real-time to see the inner workings of the tri-agent system.

## Understanding the Thought Types

InnerLoop generates various types of autonomous thoughts:

- **🤔 Wonder**: Questions and curiosities that arise spontaneously
- **💭 Memory**: Recalled experiences from previous conversations
- **🔗 Association**: Connections between current topics and other concepts
- **💡 Insight**: Deep realizations formed through reasoning
- **🎯 Focus**: Recognition of emerging conversation themes
- **🌱 Reflection**: Self-awareness about its own thinking process

Each thought is scored by the Attention Director based on relevance, urgency, novelty, and emotional significance.