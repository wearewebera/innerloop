"""Sleep Agent - Manages dormancy, summarization, and wake-up context."""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import structlog

from agents.base_agent import BaseAgent, Message

logger = structlog.get_logger()


class SleepAgent(BaseAgent):
    """
    The Sleep Agent monitors system activity and manages sleep/wake cycles.
    It detects when agents are stuck in loops or when it's time to rest,
    summarizes the conversation, and creates wake-up contexts.
    """
    
    def __init__(self, config: Dict[str, Any], message_bus: Any, memory_store: Any):
        super().__init__("sleep_agent", config, message_bus, memory_store)
        
        # Sleep configuration
        self.sleep_interval = self.agent_config.get('sleep_interval', 600)  # 10 minutes default
        self.loop_detection_window = self.agent_config.get('loop_detection_window', 60)  # 1 minute
        self.loop_threshold = self.agent_config.get('loop_threshold', 5)  # Same pattern 5 times
        self.wake_context_length = self.agent_config.get('wake_context_length', 3)  # Messages
        
        # State tracking
        self.last_sleep_time = datetime.now()
        self.is_sleeping = False
        self.message_history = []
        self.pattern_counts = defaultdict(int)
        self.agents_to_manage = ['experiencer', 'stream_generator', 'attention_director']
        
        # Sleep summaries
        self.sleep_summaries = []
        self.current_sleep_context = None
        
    async def _initialize(self):
        """Initialize the Sleep Agent."""
        self.logger.info("Sleep Agent initializing", 
                        sleep_interval=self.sleep_interval,
                        loop_threshold=self.loop_threshold)
        
        # Subscribe to all agent messages to monitor activity
        self.message_bus.subscribe(self.agent_id, "thoughts")
        self.message_bus.subscribe(self.agent_id, "filtered_thoughts")
        self.message_bus.subscribe(self.agent_id, "conversation")
        
    async def _run_loop(self):
        """Main sleep agent loop - monitor for sleep conditions."""
        self.logger.info("Sleep Agent started monitoring")
        
        while self.is_running:
            try:
                if not self.is_sleeping:
                    # Collect messages for pattern analysis
                    messages = await self.receive_messages()
                    for msg in messages:
                        await self._analyze_message(msg)
                    
                    # Check sleep conditions
                    should_sleep, reason = await self._check_sleep_conditions()
                    
                    if should_sleep:
                        await self._initiate_sleep(reason)
                else:
                    # We're sleeping - just wait
                    await asyncio.sleep(1)
                
                # Small delay
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error("Sleep agent loop error", error=str(e))
                await asyncio.sleep(1)
    
    async def _analyze_message(self, message: Message):
        """Analyze messages for patterns and activity."""
        # Add to history
        self.message_history.append({
            'content': message.content,
            'sender': message.sender,
            'type': message.message_type,
            'timestamp': datetime.now()
        })
        
        # Keep only recent history
        cutoff = datetime.now() - timedelta(seconds=self.loop_detection_window)
        self.message_history = [
            msg for msg in self.message_history 
            if msg['timestamp'] > cutoff
        ]
        
        # Extract pattern signature
        pattern = self._extract_pattern(message.content)
        if pattern:
            self.pattern_counts[pattern] += 1
            
            # Decay old patterns
            for p in list(self.pattern_counts.keys()):
                if p != pattern:
                    self.pattern_counts[p] *= 0.9
                    if self.pattern_counts[p] < 1:
                        del self.pattern_counts[p]
    
    def _extract_pattern(self, content: str) -> Optional[str]:
        """Extract a pattern signature from content."""
        # Simple pattern extraction - could be made more sophisticated
        words = content.lower().split()[:5]  # First 5 words
        if len(words) >= 3:
            return ' '.join(words[:3])
        return None
    
    async def _check_sleep_conditions(self) -> tuple[bool, str]:
        """Check if it's time to sleep."""
        now = datetime.now()
        
        # Check 1: Time-based sleep
        time_since_sleep = (now - self.last_sleep_time).total_seconds()
        if time_since_sleep >= self.sleep_interval:
            return True, f"Regular sleep interval reached ({self.sleep_interval}s)"
        
        # Check 2: Loop detection
        for pattern, count in self.pattern_counts.items():
            if count >= self.loop_threshold:
                return True, f"Loop detected: pattern '{pattern}' repeated {count} times"
        
        # Check 3: Low activity (no messages in last 30 seconds)
        if self.message_history:
            last_message_age = (now - self.message_history[-1]['timestamp']).total_seconds()
            if last_message_age > 30 and time_since_sleep > 60:  # Don't sleep too frequently
                return True, "Low activity detected"
        
        return False, ""
    
    async def _initiate_sleep(self, reason: str):
        """Initiate sleep mode for all agents."""
        self.logger.info("Initiating sleep mode", reason=reason)
        self.is_sleeping = True
        
        # Notify all agents to pause
        for agent_id in self.agents_to_manage:
            await self.send_message(
                agent_id,
                "SLEEP_MODE_ACTIVATED",
                message_type="system_command",
                priority=1.0,
                metadata={"reason": reason}
            )
        
        # Generate conversation summary
        summary = await self._generate_summary()
        
        # Create wake-up context
        wake_context = await self._create_wake_context(summary)
        
        # Store sleep summary
        self.sleep_summaries.append({
            'timestamp': datetime.now(),
            'reason': reason,
            'summary': summary,
            'wake_context': wake_context
        })
        
        # Store in memory for persistence
        await self.store_memory(
            f"Sleep cycle: {summary}",
            memory_type="sleep_summary"
        )
        
        # Broadcast sleep status
        await self.send_message(
            "topic:system",
            f"System entering sleep mode: {reason}",
            message_type="sleep_notification",
            priority=0.9,
            metadata={
                "summary": summary[:200],
                "wake_context": wake_context
            }
        )
        
        # Schedule wake-up
        await asyncio.sleep(10)  # Brief sleep for now (10 seconds)
        await self._wake_up(wake_context)
    
    async def _generate_summary(self) -> str:
        """Generate a summary of recent conversation and discoveries."""
        # Collect recent important messages
        important_messages = []
        
        # Get recent memories
        recent_memories = await self.retrieve_memories("recent activity", limit=20)
        
        # Extract key themes and discoveries
        if recent_memories:
            memory_text = "\n".join([m['content'] for m in recent_memories[-10:]])
            
            prompt = (
                "Summarize the key discoveries, experiments, and insights from this recent activity. "
                "Focus on: 1) What was learned, 2) Active experiments, 3) Emerging patterns. "
                "Be concise but capture the essence of the exploration.\n\n"
                f"Recent activity:\n{memory_text}\n\n"
                "Summary:"
            )
            
            summary = await self.generate_response(prompt)
            return summary
        else:
            return "Quiet period with minimal activity. Ready to resume exploration."
    
    async def _create_wake_context(self, summary: str) -> str:
        """Create a context message for waking up."""
        prompt = (
            f"Create a wake-up message that will help resume exploration after a rest. "
            f"Include: 1) What was being explored, 2) Next steps to try, 3) Exciting possibilities.\n\n"
            f"Sleep summary: {summary}\n\n"
            f"Wake-up message (address as 'you' to the waking consciousness):"
        )
        
        wake_context = await self.generate_response(prompt)
        return wake_context
    
    async def _wake_up(self, wake_context: str):
        """Wake up all agents with context."""
        self.logger.info("Waking up agents")
        
        # Send wake context to Experiencer first
        await self.send_message(
            "experiencer",
            wake_context,
            message_type="wake_context",
            priority=1.0,
            metadata={
                "sleep_duration": 10,
                "previous_summaries": len(self.sleep_summaries)
            }
        )
        
        # Brief delay
        await asyncio.sleep(1)
        
        # Wake all agents
        for agent_id in self.agents_to_manage:
            await self.send_message(
                agent_id,
                "SLEEP_MODE_DEACTIVATED",
                message_type="system_command",
                priority=1.0,
                metadata={"wake_context": wake_context[:100]}
            )
        
        # Reset state
        self.is_sleeping = False
        self.last_sleep_time = datetime.now()
        self.pattern_counts.clear()
        
        # Broadcast wake status
        await self.send_message(
            "topic:system",
            "System awakened and resuming exploration",
            message_type="wake_notification",
            priority=0.9
        )
        
        self.logger.info("Wake-up complete")
    
    async def force_sleep(self, reason: str = "Manual sleep requested"):
        """Public method to force sleep mode."""
        if not self.is_sleeping:
            await self._initiate_sleep(reason)
    
    async def _cleanup(self):
        """Clean up resources."""
        self.logger.info("Sleep Agent shutting down")
        self.message_bus.unsubscribe(self.agent_id, "thoughts")
        self.message_bus.unsubscribe(self.agent_id, "filtered_thoughts")
        self.message_bus.unsubscribe(self.agent_id, "conversation")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        time_since_sleep = (datetime.now() - self.last_sleep_time).total_seconds()
        
        return {
            **self.get_metrics(),
            "is_sleeping": self.is_sleeping,
            "time_since_sleep": time_since_sleep,
            "sleep_cycles": len(self.sleep_summaries),
            "pattern_count": len(self.pattern_counts),
            "max_pattern_repetition": max(self.pattern_counts.values()) if self.pattern_counts else 0
        }