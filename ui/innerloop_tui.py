"""InnerLoop TUI - Multi-panel interface showing all agent activity."""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from collections import deque

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Input, RichLog, Label
from textual.reactive import reactive
from textual import events
from textual.binding import Binding

from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich.table import Table

import structlog

logger = structlog.get_logger()


class AgentPanel(RichLog):
    """Base class for agent activity panels."""
    
    def __init__(self, agent_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_name = agent_name
        self.border_title = agent_name
        
    def add_thought(self, thought_type: str, content: str, priority: float, 
                   metadata: Optional[Dict] = None):
        """Add a thought to the panel."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Get thought style
        styles = {
            'association': ('🔗', 'cyan'),
            'memory': ('💭', 'magenta'),
            'wonder': ('🤔', 'yellow'),
            'observation': ('👁️ ', 'blue'),
            'reflection': ('🪞', 'white'),
            'insight': ('💡', 'bright_yellow'),
            'focus_change': ('🎯', 'red'),
        }
        
        emoji, color = styles.get(thought_type, ('💭', 'white'))
        
        # Format the thought
        thought_text = Text()
        thought_text.append(f"[{timestamp}] ", style="dim")
        thought_text.append(f"{emoji} {thought_type.title()} ", style=f"bold {color}")
        thought_text.append(f"({priority:.2f})\n", style="dim")
        thought_text.append(f"  {content}\n", style=color)
        
        self.write(thought_text)


class StreamGeneratorPanel(AgentPanel):
    """Panel showing raw stream of consciousness."""
    
    def __init__(self):
        super().__init__("Stream Generator", wrap=True, highlight=True, markup=True, max_lines=500, auto_scroll=True)
        

class AttentionDirectorPanel(RichLog):
    """Panel showing attention evaluation and filtering."""
    
    def __init__(self):
        super().__init__(wrap=True, highlight=True, markup=True, max_lines=500, auto_scroll=True)
        self.border_title = "Attention Director"
        
    def add_evaluation(self, content: str, priority: float, decision: str, 
                      scores: Optional[Dict] = None):
        """Add an evaluation result."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        eval_text = Text()
        eval_text.append(f"[{timestamp}] ", style="dim")
        eval_text.append("Evaluating: ", style="bold")
        eval_text.append(f"{content[:50]}...\n" if len(content) > 50 else f"{content}\n")
        
        # Priority and decision
        if priority >= 0.7:
            priority_style = "bold red"
        elif priority >= 0.5:
            priority_style = "yellow"
        else:
            priority_style = "dim"
            
        eval_text.append(f"  Priority: {priority:.2f}", style=priority_style)
        
        if decision == "PASS":
            eval_text.append(" ✓ ", style="green")
            eval_text.append("FORWARD TO EXPERIENCER\n", style="bold green")
        else:
            eval_text.append(" ✗ ", style="red")
            eval_text.append("FILTERED OUT\n", style="dim red")
        
        # Add scores if available
        if scores:
            eval_text.append("  Scores: ", style="dim")
            for criterion, score in scores.items():
                eval_text.append(f"{criterion}={score:.2f} ", style="dim")
            eval_text.append("\n")
        
        eval_text.append("\n")
        self.write(eval_text)


class ConversationPanel(Vertical):
    """Panel for main conversation between user and Alex."""
    
    def __init__(self):
        super().__init__()
        # Limit conversation log to prevent memory issues with long conversations
        self.conversation_log = RichLog(
            wrap=True, 
            highlight=True, 
            markup=True,
            max_lines=1000,  # Keep only last 1000 lines
            auto_scroll=True  # Auto-scroll to latest messages
        )
        self.input_field = Input(placeholder="Type your message...")
        self.input_callback = None
        
    def compose(self) -> ComposeResult:
        yield self.conversation_log
        yield self.input_field
        
    def add_message(self, speaker: str, content: str, is_thought: bool = False):
        """Add a message to the conversation."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        msg_text = Text()
        if is_thought:
            msg_text.append(f"[{timestamp}] ", style="dim")
            msg_text.append("[Internal: ", style="dim italic")
            msg_text.append(content, style="dim italic")
            msg_text.append("]\n", style="dim italic")
        else:
            msg_text.append(f"[{timestamp}] ", style="dim")
            if speaker.lower() == "you":
                msg_text.append(f"{speaker}: ", style="bold cyan")
                msg_text.append(f"{content}\n", style="cyan")
            else:
                msg_text.append(f"{speaker}: ", style="bold green")
                msg_text.append(f"{content}\n", style="green")
        
        msg_text.append("\n")
        self.conversation_log.write(msg_text)
        
    async def on_input_submitted(self, event: Input.Submitted):
        """Handle input submission."""
        if self.input_callback and event.value.strip():
            # Clear input immediately before processing
            value = event.value
            self.input_field.clear()
            # Focus back on input field
            self.input_field.focus()
            # Process the input
            await self.input_callback(value)


class InternalProcessingPanel(RichLog):
    """Panel showing internal processing and thoughts from the Experiencer."""
    
    def __init__(self):
        super().__init__(wrap=True, highlight=True, markup=True, max_lines=500, auto_scroll=True)
        self.border_title = "Internal Processing"
        
    def add_internal_thought(self, content: str, thought_type: str = "thought"):
        """Add an internal thought or processing message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        thought_text = Text()
        thought_text.append(f"[{timestamp}] ", style="dim")
        
        if thought_type == "thinking":
            thought_text.append("🧠 Reasoning: ", style="bold yellow")
            thought_text.append(content, style="italic yellow")
        elif thought_type == "tool_call":
            thought_text.append("🔧 Tool: ", style="bold cyan")
            thought_text.append(content, style="cyan")
        else:
            thought_text.append("💭 ", style="magenta")
            thought_text.append(content, style="italic magenta")
            
        thought_text.append("\n")
        
        self.write(thought_text)


class StatusBar(Static):
    """Status bar showing system metrics."""
    
    thoughts_per_min = reactive(0.0)
    filtered_percentage = reactive(0.0)
    memory_count = reactive(0)
    uptime = reactive("00:00:00")
    queued_messages = reactive(0)
    active_experiments = reactive(0)
    
    def render(self):
        queue_style = "bold red" if self.queued_messages > 0 else "dim"
        experiment_style = "bold green" if self.active_experiments > 0 else "dim"
        
        status_parts = [
            "[Status: Active]",
            f"[Thoughts/min: {self.thoughts_per_min:.1f}]",
            f"[Filtered: {self.filtered_percentage:.0f}%]",
            f"[Memory: {self.memory_count}]",
            f"[{queue_style}]Queued: {self.queued_messages}[/{queue_style}]",
            f"[{experiment_style}]Experiments: {self.active_experiments}[/{experiment_style}]",
            f"[Uptime: {self.uptime}]"
        ]
        
        return " ".join(status_parts)


class InnerLoopTUI(App):
    """Main TUI application for InnerLoop."""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 2;
        grid-rows: 1fr 1fr 1;
        grid-columns: 1fr 1fr 1fr;
        grid-gutter: 1;
    }
    
    #stream-panel {
        column-span: 1;
        row-span: 1;
        border: solid green;
        height: 100%;
    }
    
    #attention-panel {
        column-span: 1;
        row-span: 1;
        border: solid yellow;
        height: 100%;
    }
    
    #internal-panel {
        column-span: 1;
        row-span: 1;
        border: solid magenta;
        height: 100%;
    }
    
    #conversation-panel {
        column-span: 3;
        row-span: 1;
        border: solid cyan;
        height: 100%;
    }
    
    #status-bar {
        column-span: 3;
        height: 1;
        dock: bottom;
        background: $surface;
    }
    
    Input {
        dock: bottom;
        height: 3;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear_all", "Clear All"),
        Binding("f1", "toggle_stream", "Toggle Stream"),
        Binding("f2", "toggle_attention", "Toggle Attention"),
        Binding("f3", "toggle_internal", "Toggle Internal"),
    ]
    
    def __init__(self, message_bus=None, agents=None, config=None):
        super().__init__()
        self.message_bus = message_bus
        self.agents = agents
        self.config = config or {}
        
        # Metrics tracking
        self.start_time = datetime.now()
        self.thought_count = 0
        self.filtered_count = 0
        self.total_evaluated = 0
        
        # Message queues for display
        self.stream_queue = asyncio.Queue(maxsize=1000)
        self.attention_queue = asyncio.Queue(maxsize=1000)
        self.conversation_queue = asyncio.Queue(maxsize=1000)
        self.internal_queue = asyncio.Queue(maxsize=1000)
        
    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=True)
        
        # Create panels - order matters for grid layout
        # Top row: three monitoring panels
        self.stream_panel = StreamGeneratorPanel()
        self.stream_panel.id = "stream-panel"
        yield self.stream_panel
        
        self.attention_panel = AttentionDirectorPanel()
        self.attention_panel.id = "attention-panel"
        yield self.attention_panel
        
        self.internal_panel = InternalProcessingPanel()
        self.internal_panel.id = "internal-panel"
        yield self.internal_panel
        
        # Bottom row: conversation panel (spans all columns)
        self.conversation_panel = ConversationPanel()
        self.conversation_panel.id = "conversation-panel"
        yield self.conversation_panel
        
        self.status_bar = StatusBar()
        self.status_bar.id = "status-bar"
        yield self.status_bar
        
        yield Footer()
    
    async def on_mount(self):
        """Start monitoring tasks when mounted."""
        # Set up input callback
        if self.agents and 'experiencer' in self.agents:
            self.conversation_panel.input_callback = self._handle_user_input
            
            # Set up spontaneous share callback
            self.agents['experiencer'].spontaneous_share_callback = self._handle_spontaneous_share
            
        # Start monitoring tasks
        self.monitor_task = asyncio.create_task(self._monitor_agents())
        self.update_task = asyncio.create_task(self._update_panels())
        self.metrics_task = asyncio.create_task(self._update_metrics())
        
        # Store tasks for cleanup
        self._tasks = [self.monitor_task, self.update_task, self.metrics_task]
        
        # Welcome message
        self.conversation_panel.add_message(
            "System", 
            f"InnerLoop AI - Multi-Panel Interface\nHello! I'm {self.config.get('agents', {}).get('shared_identity', {}).get('name', 'Alex')}.\nThinking model: {self.config.get('model', {}).get('name', 'unknown')}"
        )
    
    async def _handle_user_input(self, user_input: str):
        """Handle user input."""
        if user_input.lower() in ['quit', 'exit', 'bye']:
            self.exit()
            return
            
        # Add to conversation
        self.conversation_panel.add_message("You", user_input)
        
        # Send to experiencer if available
        if self.agents and 'experiencer' in self.agents:
            response_received = asyncio.Event()
            response_text = None
            
            async def response_callback(response):
                nonlocal response_text
                response_text = response
                response_received.set()
            
            # Notify that message is being queued
            self.conversation_panel.add_message(
                "System", 
                "[Your message has been queued. Alex will respond when contextually appropriate.]",
                is_thought=True
            )
            
            await self.agents['experiencer'].receive_external_input(
                user_input, response_callback
            )
            
            # Wait for response
            try:
                await asyncio.wait_for(response_received.wait(), timeout=60)  # Increased timeout for queued messages
                if response_text:
                    self.conversation_panel.add_message("Alex", response_text)
            except asyncio.TimeoutError:
                self.conversation_panel.add_message("System", "[Response pending - Alex is focused on experiments]")
    
    async def _handle_spontaneous_share(self, thought: str):
        """Handle spontaneous thought sharing from Experiencer."""
        # Add as a special type of message
        self.conversation_panel.add_message("Alex", thought, is_thought=True)
    
    async def _monitor_agents(self):
        """Monitor message bus for agent activity."""
        if not self.message_bus:
            return
            
        # Subscribe to all agent communications
        self.message_bus.subscribe("tui_monitor", "thoughts")
        self.message_bus.subscribe("tui_monitor", "filtered_thoughts")
        self.message_bus.subscribe("tui_monitor", "evaluations")
        self.message_bus.register_agent("tui_monitor")
        
        while True:
            try:
                messages = await self.message_bus.receive("tui_monitor", timeout=0.1)
                
                for msg in messages:
                    if msg.message_type == "thought" and msg.metadata.get('raw', True):
                        # Raw thought from stream generator
                        await self.stream_queue.put({
                            'type': msg.metadata.get('type', 'thought'),
                            'content': msg.content,
                            'priority': msg.priority,
                            'metadata': msg.metadata
                        })
                        self.thought_count += 1
                        
                    elif msg.message_type == "evaluation":
                        # Evaluation from attention director
                        await self.attention_queue.put({
                            'content': msg.metadata.get('evaluated_content', ''),
                            'priority': msg.metadata.get('final_priority', 0),
                            'decision': msg.metadata.get('decision', ''),
                            'scores': msg.metadata.get('scores', {})
                        })
                        self.total_evaluated += 1
                        if msg.metadata.get('decision') == 'FILTERED':
                            self.filtered_count += 1
                            
                    elif msg.message_type == "internal_state":
                        # Internal processing from experiencer - route to internal panel
                        thought_type = msg.metadata.get('type', 'thought')
                        content = msg.content
                        
                        # Handle full thinking if available
                        if thought_type == "thinking" and msg.metadata.get('full_thinking'):
                            # Show truncated thinking with indicator
                            full_thinking = msg.metadata.get('full_thinking', '')
                            if len(full_thinking) > 200:
                                content = f"{full_thinking[:200]}... [truncated, {len(full_thinking)} chars total]"
                            else:
                                content = full_thinking
                        
                        await self.internal_queue.put({
                            'content': content,
                            'type': thought_type
                        })
                    
                    elif msg.message_type == "tool_call":
                        # Tool execution messages
                        await self.internal_queue.put({
                            'content': f"Executing {msg.metadata.get('tool_name', 'unknown')}: {msg.content}",
                            'type': 'tool_call'
                        })
                        
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.error("Monitor error", error=str(e))
                
            await asyncio.sleep(0.01)
    
    async def _update_panels(self):
        """Update panels with queued messages."""
        while True:
            try:
                # Update stream panel
                try:
                    thought = await asyncio.wait_for(self.stream_queue.get(), timeout=0.01)
                    self.stream_panel.add_thought(
                        thought['type'],
                        thought['content'],
                        thought['priority'],
                        thought.get('metadata')
                    )
                except asyncio.TimeoutError:
                    pass
                
                # Update attention panel
                try:
                    eval_data = await asyncio.wait_for(self.attention_queue.get(), timeout=0.01)
                    self.attention_panel.add_evaluation(
                        eval_data['content'],
                        eval_data['priority'],
                        eval_data['decision'],
                        eval_data.get('scores')
                    )
                except asyncio.TimeoutError:
                    pass
                
                # Update internal processing panel
                try:
                    internal_data = await asyncio.wait_for(self.internal_queue.get(), timeout=0.01)
                    self.internal_panel.add_internal_thought(
                        internal_data['content'],
                        internal_data.get('type', 'thought')
                    )
                except asyncio.TimeoutError:
                    pass
                    
            except Exception as e:
                logger.error("Panel update error", error=str(e))
                
            await asyncio.sleep(0.01)
    
    async def _update_metrics(self):
        """Update status bar metrics."""
        while True:
            try:
                # Calculate metrics
                uptime = datetime.now() - self.start_time
                self.status_bar.uptime = str(uptime).split('.')[0]
                
                # Thoughts per minute (rolling average)
                if uptime.total_seconds() > 0:
                    self.status_bar.thoughts_per_min = (self.thought_count / uptime.total_seconds()) * 60
                
                # Filtered percentage
                if self.total_evaluated > 0:
                    self.status_bar.filtered_percentage = (self.filtered_count / self.total_evaluated) * 100
                
                # Memory count (if available)
                if hasattr(self, 'memory_store'):
                    stats = self.memory_store.get_stats()
                    self.status_bar.memory_count = stats.get('total_memories', 0)
                
                # Queued messages and experiments from Experiencer
                if self.agents and 'experiencer' in self.agents:
                    status = self.agents['experiencer'].get_status()
                    self.status_bar.queued_messages = status.get('queued_messages', 0)
                    self.status_bar.active_experiments = status.get('active_experiments', 0)
                    
            except Exception as e:
                logger.error("Metrics update error", error=str(e))
                
            await asyncio.sleep(1)
    
    def action_clear_all(self):
        """Clear all panels."""
        self.stream_panel.clear()
        self.attention_panel.clear()
        self.conversation_panel.conversation_log.clear()
        self.internal_panel.clear()
        
    def action_toggle_stream(self):
        """Toggle stream panel visibility."""
        self.stream_panel.visible = not self.stream_panel.visible
        
    def action_toggle_attention(self):
        """Toggle attention panel visibility."""
        self.attention_panel.visible = not self.attention_panel.visible
        
    def action_toggle_internal(self):
        """Toggle internal processing panel visibility."""
        self.internal_panel.visible = not self.internal_panel.visible
    
    async def on_unmount(self):
        """Clean up when app is closing."""
        # Cancel all tasks
        if hasattr(self, '_tasks'):
            for task in self._tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass