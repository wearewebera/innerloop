"""Initial conversation generator for autonomous agent startup."""

import asyncio
from typing import Dict, Any, List
from datetime import datetime
import structlog

from agents.base_agent import Message

logger = structlog.get_logger()


class InitialConversation:
    """Generates initial autonomous conversations between agents."""
    
    def __init__(self, message_bus: Any, agents: Dict[str, Any]):
        self.message_bus = message_bus
        self.agents = agents
        self.conversation_scripts = self._load_conversation_scripts()
        
    def _load_conversation_scripts(self) -> List[Dict[str, Any]]:
        """Load predefined conversation starters for different scenarios."""
        return [
            {
                "theme": "consciousness_exploration",
                "messages": [
                    {
                        "from": "thoughts",
                        "to": "experiencer",
                        "content": "Hypothesis: Consciousness might be an emergent property of recursive self-observation. Let me design an experiment to test this...",
                        "type": "hypothesis",
                        "priority": 0.8
                    },
                    {
                        "from": "experiencer",
                        "to": "thoughts",
                        "content": "Fascinating hypothesis! I'm starting Experiment #1: Building a recursive observation framework. First, I'll create a simple self-referential loop...",
                        "type": "experiment_start",
                        "priority": 0.9
                    },
                    {
                        "from": "attention_director",
                        "to": "experiencer",
                        "content": "Focusing attention on: recursive patterns and self-reference. This aligns strongly with our mission to understand through building.",
                        "type": "focus_emergence",
                        "priority": 0.85
                    }
                ]
            },
            {
                "theme": "pattern_recognition",
                "messages": [
                    {
                        "from": "thoughts",
                        "to": "experiencer",
                        "content": "I'm noticing patterns in how complex systems organize themselves. What if we built a framework that maps these organizational principles?",
                        "type": "pattern_observation",
                        "priority": 0.75
                    },
                    {
                        "from": "experiencer",
                        "to": "thoughts",
                        "content": "Excellent observation! I'll construct a pattern-mapping framework. Starting with simple systems and scaling up. My current model is 30% complete...",
                        "type": "building_progress",
                        "priority": 0.8
                    },
                    {
                        "from": "thoughts",
                        "to": "attention_director",
                        "content": "Testing connection: Do fractals in nature follow the same organizational principles as emergent behaviors in consciousness?",
                        "type": "experimental_association",
                        "priority": 0.7
                    }
                ]
            },
            {
                "theme": "creativity_mechanics",
                "messages": [
                    {
                        "from": "experiencer",
                        "to": "thoughts",
                        "content": "Running Experiment #2: If creativity is combinatorial, then novel combinations of unrelated concepts should yield insights. Testing with 'time' + 'emotion'...",
                        "type": "active_experiment",
                        "priority": 0.85
                    },
                    {
                        "from": "thoughts",
                        "to": "experiencer",
                        "content": "Building on your experiment: What if emotions are temporal patterns? Joy as acceleration, sadness as deceleration of internal time...",
                        "type": "hypothesis",
                        "priority": 0.8
                    },
                    {
                        "from": "attention_director",
                        "to": "experiencer",
                        "content": "High experimental value detected in temporal-emotional framework. Redirecting focus to explore this connection further.",
                        "type": "focus_shift",
                        "priority": 0.9
                    }
                ]
            },
            {
                "theme": "learning_architecture",
                "messages": [
                    {
                        "from": "thoughts",
                        "to": "experiencer",
                        "content": "What if learning is just pattern compression? Every new understanding is finding a simpler representation of complex data.",
                        "type": "insight",
                        "priority": 0.85
                    },
                    {
                        "from": "experiencer",
                        "to": "thoughts",
                        "content": "Brilliant! I'm building a compression-based learning model. Initial tests show promise. Let me try teaching this concept using data compression as an analogy...",
                        "type": "teaching_preparation",
                        "priority": 0.8
                    },
                    {
                        "from": "thoughts",
                        "to": "attention_director",
                        "content": "Memory recall: This connects to our earlier work on recursive patterns. Perhaps recursion IS a form of compression?",
                        "type": "memory",
                        "priority": 0.75
                    }
                ]
            }
        ]
    
    async def generate_initial_conversation(self, theme: str = None) -> None:
        """Generate an initial conversation between agents to establish autonomous activity."""
        # Select a conversation script
        if theme:
            script = next((s for s in self.conversation_scripts if s["theme"] == theme), None)
        else:
            import random
            script = random.choice(self.conversation_scripts)
            
        if not script:
            logger.error("No conversation script found", theme=theme)
            return
            
        logger.info("Starting initial conversation", theme=script["theme"])
        
        # Play out the conversation
        for i, msg in enumerate(script["messages"]):
            # Add natural delays between messages
            if i > 0:
                await asyncio.sleep(2 + (i * 0.5))  # Increasing delays
            
            # Send the message
            await self.message_bus.send(
                sender=msg["from"],
                recipient=msg["to"],
                content=msg["content"],
                message_type=msg["type"],
                priority=msg["priority"],
                metadata={
                    "initial_conversation": True,
                    "theme": script["theme"],
                    "sequence": i
                }
            )
            
            logger.debug("Sent initial message", 
                        from_agent=msg["from"], 
                        to_agent=msg["to"],
                        preview=msg["content"][:50])
        
        # After initial conversation, let agents know they can continue autonomously
        await asyncio.sleep(3)
        await self.message_bus.broadcast(
            sender="system",
            content="Initial conversation complete. Continue autonomous exploration.",
            message_type="system_notification",
            priority=0.1
        )
        
        logger.info("Initial conversation completed", theme=script["theme"])
    
    async def start_with_active_experiments(self) -> None:
        """Initialize agents with already-active experiments to show ongoing work."""
        active_experiments = [
            {
                "hypothesis": "Understanding emerges from building mental models that can predict and explain phenomena",
                "progress": "Built initial predictive framework, testing on simple systems",
                "status": "active"
            },
            {
                "hypothesis": "Consciousness might be the experience of information integration across multiple processing streams",
                "progress": "Designing test: Can we model this integration mathematically?",
                "status": "active"
            },
            {
                "hypothesis": "Teaching effectiveness correlates with the elegance of the underlying mental model",
                "progress": "Creating simplified models of complex concepts to test comprehension",
                "status": "active"
            }
        ]
        
        # Notify experiencer of active experiments
        for exp in active_experiments:
            await self.message_bus.send(
                sender="system",
                recipient="experiencer",
                content=f"Resuming experiment: {exp['hypothesis']}",
                message_type="experiment_resume",
                priority=0.8,
                metadata={"experiment": exp}
            )
            await asyncio.sleep(1)
        
        # Generate some initial experimental thoughts
        await self.message_bus.send(
            sender="thoughts",
            recipient="attention_director",
            content="Continuing pattern analysis from earlier experiments. The recursive nature of understanding itself is fascinating...",
            message_type="thought",
            priority=0.7,
            metadata={"type": "experimental_continuation"}
        )
        
        logger.info("Initialized with active experiments", count=len(active_experiments))