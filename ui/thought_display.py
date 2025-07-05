"""ThoughtDisplay component for showing autonomous thoughts in real-time."""

import asyncio
from collections import deque
from datetime import datetime
from typing import Dict, Any, Optional, Deque
import structlog

logger = structlog.get_logger()


class ThoughtDisplay:
    """Displays autonomous thoughts from agents in the CLI."""
    
    # Thought type emojis and colors
    THOUGHT_STYLES = {
        'association': {'emoji': '🔗', 'color': '\033[36m'},      # Cyan
        'memory': {'emoji': '💭', 'color': '\033[35m'},          # Magenta
        'wonder': {'emoji': '🤔', 'color': '\033[33m'},          # Yellow
        'observation': {'emoji': '👁️', 'color': '\033[34m'},     # Blue
        'reflection': {'emoji': '🪞', 'color': '\033[37m'},      # White
        'insight': {'emoji': '💡', 'color': '\033[93m'},         # Bright Yellow
        'triggered_association': {'emoji': '⚡', 'color': '\033[36m'},  # Cyan
        'focus_change': {'emoji': '🎯', 'color': '\033[91m'},    # Red
        'filtered_thought': {'emoji': '🧠', 'color': '\033[32m'}, # Green
    }
    
    RESET_COLOR = '\033[0m'
    DIM_COLOR = '\033[2m'
    
    def __init__(self, config: Dict[str, Any], message_bus: Any):
        self.config = config
        self.message_bus = message_bus
        
        # Configuration
        self.enabled = config.get('ui', {}).get('show_thoughts', True)
        self.min_priority = config.get('ui', {}).get('thought_min_priority', 0.3)
        self.max_display = config.get('ui', {}).get('max_thought_display', 5)
        self.show_metadata = config.get('ui', {}).get('show_thought_metadata', True)
        
        # Thought buffer
        self.thought_buffer: Deque[Dict[str, Any]] = deque(maxlen=100)
        self.displayed_thoughts = set()  # Track displayed thought IDs
        
        # Display state
        self.last_display_time = datetime.now()
        self.is_monitoring = False
        
        self.logger = logger.bind(component="thought_display")
    
    async def start_monitoring(self):
        """Start monitoring the message bus for thoughts."""
        if not self.enabled:
            self.logger.info("Thought display disabled in config")
            return
            
        self.is_monitoring = True
        self.logger.info("Started thought monitoring")
        
        # Register a special subscription for all thoughts
        self.message_bus.subscribe("thought_monitor", "thoughts")
        self.message_bus.subscribe("thought_monitor", "filtered_thoughts")
        
        # Start the monitoring task
        asyncio.create_task(self._monitor_thoughts())
    
    async def stop_monitoring(self):
        """Stop monitoring thoughts."""
        self.is_monitoring = False
        self.message_bus.unsubscribe("thought_monitor", "thoughts")
        self.message_bus.unsubscribe("thought_monitor", "filtered_thoughts")
        self.logger.info("Stopped thought monitoring")
    
    async def _monitor_thoughts(self):
        """Monitor message bus for thoughts to display."""
        while self.is_monitoring:
            try:
                # Check for new thoughts
                messages = await self.message_bus.receive("thought_monitor", timeout=0.5)
                
                for message in messages:
                    if message.priority >= self.min_priority:
                        thought_data = {
                            'id': message.id,
                            'content': message.content,
                            'type': message.metadata.get('type', 'thought'),
                            'priority': message.priority,
                            'sender': message.sender,
                            'timestamp': message.timestamp
                        }
                        
                        # Add to buffer if not already displayed
                        if message.id not in self.displayed_thoughts:
                            self.thought_buffer.append(thought_data)
                            
            except Exception as e:
                self.logger.error("Error monitoring thoughts", error=str(e))
                
            await asyncio.sleep(0.1)
    
    def get_pending_thoughts(self, limit: Optional[int] = None) -> list:
        """Get thoughts that haven't been displayed yet."""
        if not self.enabled:
            return []
            
        limit = limit or self.max_display
        pending = []
        
        for thought in self.thought_buffer:
            if thought['id'] not in self.displayed_thoughts:
                pending.append(thought)
                if len(pending) >= limit:
                    break
        
        return pending
    
    def format_thought(self, thought: Dict[str, Any]) -> str:
        """Format a thought for display."""
        thought_type = thought.get('type', 'thought')
        style = self.THOUGHT_STYLES.get(thought_type, {'emoji': '💭', 'color': ''})
        
        # Build the formatted thought
        parts = []
        parts.append(f"{self.DIM_COLOR}[")
        parts.append(f"{style['color']}{style['emoji']} {thought_type.replace('_', ' ').title()}")
        
        if self.show_metadata:
            parts.append(f" ({thought['priority']:.2f})")
            if thought['sender'] != 'stream_generator':
                parts.append(f" from {thought['sender']}")
        
        parts.append(f"{self.DIM_COLOR}]:{self.RESET_COLOR} ")
        parts.append(f"{style['color']}{thought['content']}{self.RESET_COLOR}")
        
        return ''.join(parts)
    
    def display_thoughts(self, limit: Optional[int] = None):
        """Display pending thoughts and mark them as shown."""
        thoughts = self.get_pending_thoughts(limit)
        
        if thoughts:
            print()  # Empty line before thoughts
            
            for thought in thoughts:
                print(self.format_thought(thought))
                self.displayed_thoughts.add(thought['id'])
            
            print()  # Empty line after thoughts
            
        return len(thoughts)
    
    async def display_continuous(self, interval: float = 2.0):
        """Continuously display new thoughts at intervals."""
        while self.is_monitoring:
            self.display_thoughts()
            await asyncio.sleep(interval)
    
    def clear_buffer(self):
        """Clear the thought buffer and displayed set."""
        self.thought_buffer.clear()
        self.displayed_thoughts.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get display statistics."""
        return {
            'enabled': self.enabled,
            'buffer_size': len(self.thought_buffer),
            'displayed_count': len(self.displayed_thoughts),
            'pending_count': len(self.get_pending_thoughts()),
            'min_priority': self.min_priority
        }