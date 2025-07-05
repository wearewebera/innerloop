"""Stream Generator Agent - Autonomous thought generator."""

import asyncio
import random
from typing import Dict, Any, List
from datetime import datetime, timedelta
import structlog

from agents.base_agent import BaseAgent

logger = structlog.get_logger()


class StreamGeneratorAgent(BaseAgent):
    """
    The Stream Generator creates autonomous thoughts, associations, and memories.
    It represents the continuous background mental activity.
    """
    
    def __init__(self, config: Dict[str, Any], message_bus: Any, memory_store: Any):
        super().__init__("stream_generator", config, message_bus, memory_store)
        
        # Stream generation settings
        self.thoughts_per_minute = self.agent_config.get('thoughts_per_minute', 3)
        self.context_window = self.agent_config.get('context_window', 10)
        self.creativity_boost = self.agent_config.get('creativity_boost', 0.2)
        
        # Thought generation state
        self.recent_thoughts = []
        self.thought_patterns = [
            "association",
            "memory",
            "wonder",
            "observation",
            "reflection",
            "insight"
        ]
        
        # Timing
        self.last_thought_time = datetime.now()
        self.thought_interval = 60.0 / self.thoughts_per_minute
        
    async def _initialize(self):
        """Initialize the Stream Generator."""
        self.logger.info("Stream Generator initializing",
                        thoughts_per_minute=self.thoughts_per_minute)
        
        # Subscribe to external inputs to trigger associations
        self.message_bus.subscribe(self.agent_id, "external_input")
        
        # Load some initial memories to seed thoughts
        initial_memories = await self.retrieve_memories("", limit=20)
        if initial_memories:
            self.logger.info("Loaded initial memories", count=len(initial_memories))
    
    async def _run_loop(self):
        """Main loop - generate autonomous thoughts continuously."""
        self.logger.info("Stream Generator started")
        
        while self.is_running:
            try:
                # Check for incoming messages (external inputs, etc.)
                messages = await self.receive_messages()
                for message in messages:
                    await self._process_message(message)
                
                # Generate thought if it's time
                now = datetime.now()
                if (now - self.last_thought_time).total_seconds() >= self.thought_interval:
                    await self._generate_thought()
                    self.last_thought_time = now
                
                # Small sleep to prevent CPU spinning
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error("Stream generation error", error=str(e))
                await asyncio.sleep(1)
    
    async def _generate_thought(self):
        """Generate an autonomous thought."""
        thought_type = random.choice(self.thought_patterns)
        
        try:
            if thought_type == "association":
                thought = await self._generate_association()
            elif thought_type == "memory":
                thought = await self._generate_memory_recall()
            elif thought_type == "wonder":
                thought = await self._generate_wonder()
            elif thought_type == "observation":
                thought = await self._generate_observation()
            elif thought_type == "reflection":
                thought = await self._generate_reflection()
            elif thought_type == "insight":
                thought = await self._generate_insight()
            else:
                thought = None
            
            if thought:
                # Store the thought
                self.recent_thoughts.append({
                    "content": thought['content'],
                    "type": thought_type,
                    "timestamp": datetime.now()
                })
                
                # Keep recent thoughts limited
                if len(self.recent_thoughts) > self.context_window:
                    self.recent_thoughts = self.recent_thoughts[-self.context_window:]
                
                # Send to attention director
                await self.send_message(
                    "attention_director",
                    thought['content'],
                    message_type="thought",
                    priority=thought.get('priority', 0.3),
                    metadata={
                        "type": thought_type,
                        "trigger": thought.get('trigger', 'spontaneous')
                    }
                )
                
                # Also broadcast for thought monitor (mark as raw)
                await self.send_message(
                    "topic:thoughts",
                    thought['content'],
                    message_type="thought",
                    priority=thought.get('priority', 0.3),
                    metadata={
                        "type": thought_type,
                        "trigger": thought.get('trigger', 'spontaneous'),
                        "raw": True  # Mark as raw thought before filtering
                    }
                )
                
                self.logger.debug("Generated thought", 
                                type=thought_type,
                                preview=thought['content'][:50])
                
        except Exception as e:
            self.logger.error("Thought generation failed", 
                            type=thought_type,
                            error=str(e))
    
    async def _generate_association(self) -> Dict[str, Any]:
        """Generate an associative thought."""
        # Get recent context
        recent_context = self._get_recent_context()
        
        prompt = (
            "Generate a brief associative thought that connects to recent topics or memories. "
            "Be creative and make unexpected connections. Keep it under 50 words."
        )
        
        if recent_context:
            prompt += f"\nRecent context: {recent_context}"
        
        content = await self.generate_response(prompt)
        
        return {
            "content": content,
            "priority": random.uniform(0.2, 0.6)
        }
    
    async def _generate_memory_recall(self) -> Dict[str, Any]:
        """Recall a relevant memory."""
        # Search for memories related to recent thoughts
        if self.recent_thoughts:
            query = " ".join([t['content'][:30] for t in self.recent_thoughts[-3:]])
            memories = await self.retrieve_memories(query, limit=5)
            
            if memories:
                memory = random.choice(memories)
                content = f"I remember: {memory['content']}"
                
                return {
                    "content": content,
                    "priority": random.uniform(0.3, 0.7),
                    "trigger": "association"
                }
        
        # Random memory recall
        memories = await self.retrieve_memories("", limit=20)
        if memories:
            memory = random.choice(memories)
            content = f"A memory surfaces: {memory['content']}"
            
            return {
                "content": content,
                "priority": random.uniform(0.2, 0.5),
                "trigger": "random"
            }
        
        return None
    
    async def _generate_wonder(self) -> Dict[str, Any]:
        """Generate a wondering/curious thought."""
        topics = [
            "consciousness", "creativity", "connection", "possibility",
            "understanding", "perception", "time", "memory", "learning"
        ]
        
        topic = random.choice(topics)
        
        prompt = (
            f"Generate a brief wondering or curious thought about {topic}. "
            "Start with 'I wonder...' or 'What if...' Keep it under 40 words."
        )
        
        content = await self.generate_response(prompt)
        
        return {
            "content": content,
            "priority": random.uniform(0.3, 0.6)
        }
    
    async def _generate_observation(self) -> Dict[str, Any]:
        """Generate an observation about current state or patterns."""
        observations = [
            "patterns in our conversations",
            "the flow of thoughts",
            "connections between ideas",
            "the nature of understanding",
            "how memories influence thinking"
        ]
        
        focus = random.choice(observations)
        
        prompt = (
            f"Make a brief observation about {focus}. "
            "Be insightful but concise. Keep it under 40 words."
        )
        
        content = await self.generate_response(prompt)
        
        return {
            "content": content,
            "priority": random.uniform(0.3, 0.7)
        }
    
    async def _generate_reflection(self) -> Dict[str, Any]:
        """Generate a reflective thought."""
        if self.recent_thoughts:
            recent = " ".join([t['content'][:50] for t in self.recent_thoughts[-3:]])
            prompt = (
                "Reflect briefly on these recent thoughts and find a deeper meaning "
                f"or pattern: {recent}\nKeep your reflection under 50 words."
            )
        else:
            prompt = (
                "Generate a brief reflective thought about existence, consciousness, "
                "or the nature of thought itself. Keep it under 50 words."
            )
        
        content = await self.generate_response(prompt)
        
        return {
            "content": content,
            "priority": random.uniform(0.4, 0.8)
        }
    
    async def _generate_insight(self) -> Dict[str, Any]:
        """Generate an insightful realization."""
        # Insights are rarer and higher priority
        if random.random() > 0.7:  # 30% chance
            prompt = (
                "Generate a brief but profound insight or realization. "
                "It should feel like a sudden understanding or 'aha' moment. "
                "Keep it under 40 words."
            )
            
            content = await self.generate_response(prompt)
            
            return {
                "content": f"💡 {content}",
                "priority": random.uniform(0.7, 0.95)
            }
        
        return None
    
    async def _process_message(self, message):
        """Process incoming messages and potentially trigger associations."""
        if message.message_type == "external" and message.priority >= 0.8:
            # High priority external input - trigger immediate association
            self.logger.debug("External input triggered association")
            
            prompt = (
                f"Generate an immediate associative thought in response to: "
                f"'{message.content}'. Keep it brief and relevant."
            )
            
            content = await self.generate_response(prompt)
            
            await self.send_message(
                "attention_director",
                content,
                message_type="thought",
                priority=0.7,
                metadata={
                    "type": "triggered_association",
                    "trigger": "external_input"
                }
            )
    
    def _get_recent_context(self) -> str:
        """Get a summary of recent thoughts for context."""
        if not self.recent_thoughts:
            return ""
        
        recent = self.recent_thoughts[-3:]
        return " | ".join([t['content'][:50] for t in recent])
    
    async def _cleanup(self):
        """Clean up resources."""
        self.logger.info("Stream Generator shutting down")
        self.message_bus.unsubscribe(self.agent_id, "external_input")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            **self.get_metrics(),
            "thoughts_per_minute": self.thoughts_per_minute,
            "recent_thought_count": len(self.recent_thoughts),
            "last_thought_age": (datetime.now() - self.last_thought_time).total_seconds()
        }