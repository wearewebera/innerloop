"""Experiencer Agent - The primary consciousness and decision maker."""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from agents.base_agent import BaseAgent, Message

logger = structlog.get_logger()


class ExperiencerAgent(BaseAgent):
    """
    The Experiencer is the primary consciousness of the system.
    It processes external inputs, makes decisions, and generates responses.
    """
    
    def __init__(self, config: Dict[str, Any], message_bus: Any, memory_store: Any):
        super().__init__("experiencer", config, message_bus, memory_store)
        
        self.current_context = []
        self.decision_history = []
        self.external_input_queue = asyncio.Queue()
        self.is_processing = False
        
    async def _initialize(self):
        """Initialize the Experiencer agent."""
        self.logger.info("Experiencer initializing")
        
        # Subscribe to attention director's filtered thoughts
        self.message_bus.subscribe(self.agent_id, "attention_approved")
        
        # Load recent conversation history
        recent_memories = await self.retrieve_memories("recent conversation", limit=10)
        if recent_memories:
            self.current_context = [
                {"role": "assistant", "content": mem['content']} 
                for mem in recent_memories[-5:]
            ]
            self.logger.info("Loaded recent context", count=len(self.current_context))
    
    async def _run_loop(self):
        """Main experiencer loop - process inputs and generate responses."""
        self.logger.info("Experiencer started")
        
        while self.is_running:
            try:
                # Check for messages from other agents
                messages = await self.receive_messages()
                
                for message in messages:
                    await self._process_agent_message(message)
                
                # Check for external input
                try:
                    external_input = self.external_input_queue.get_nowait()
                    await self._process_external_input(external_input)
                except asyncio.QueueEmpty:
                    pass
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error("Experiencer loop error", error=str(e))
                await asyncio.sleep(1)
    
    async def _process_agent_message(self, message: Message):
        """Process a message from another agent."""
        self.logger.debug("Processing agent message", 
                         sender=message.sender,
                         type=message.message_type,
                         priority=message.priority)
        
        if message.sender == "attention_director" and message.priority >= 0.5:
            # High priority thought from attention director
            await self._integrate_thought(message.content, message.metadata)
            
        elif message.message_type == "memory":
            # Memory recall from stream generator
            self.current_context.append({
                "role": "system",
                "content": f"Recalled memory: {message.content}"
            })
    
    async def _process_external_input(self, input_data: Dict[str, Any]):
        """Process external input and generate a response."""
        self.is_processing = True
        user_input = input_data['content']
        
        self.logger.info("Processing external input", preview=user_input[:50])
        
        try:
            # Store the input as a memory
            await self.store_memory(
                f"User said: {user_input}",
                memory_type="conversation"
            )
            
            # Notify other agents about the external input
            await self.send_message(
                "attention_director",
                user_input,
                message_type="external",
                priority=1.0,
                metadata={"source": "user"}
            )
            
            # Build conversation context
            context = self.current_context + [
                {"role": "user", "content": user_input}
            ]
            
            # Add any high-priority thoughts from other agents
            recent_thoughts = self._get_recent_high_priority_thoughts()
            if recent_thoughts:
                thought_summary = "\n".join([
                    f"- {thought}" for thought in recent_thoughts
                ])
                context.append({
                    "role": "system",
                    "content": f"Current thoughts from your consciousness:\n{thought_summary}"
                })
            
            # Generate response
            prompt = (
                "Respond to the user naturally, incorporating any relevant thoughts "
                "or memories that have surfaced. Be genuine and engaging."
            )
            
            response = await self.generate_response(prompt, context)
            
            # Store response as memory
            await self.store_memory(
                f"I responded: {response}",
                memory_type="conversation"
            )
            
            # Update context
            self.current_context.append({"role": "assistant", "content": response})
            if len(self.current_context) > 10:
                self.current_context = self.current_context[-10:]
            
            # Record decision
            self.decision_history.append({
                "timestamp": datetime.now(),
                "input": user_input,
                "response": response,
                "context_size": len(context)
            })
            
            # Send response through callback
            if input_data.get('callback'):
                await input_data['callback'](response)
            
        except Exception as e:
            self.logger.error("Failed to process external input", error=str(e))
            if input_data.get('callback'):
                await input_data['callback']("I apologize, I encountered an error processing that.")
        
        finally:
            self.is_processing = False
    
    async def _integrate_thought(self, thought: str, metadata: Dict[str, Any]):
        """Integrate a high-priority thought into current processing."""
        thought_type = metadata.get('type', 'general')
        
        self.logger.debug("Integrating thought", type=thought_type)
        
        # Broadcast internal processing
        await self.send_message(
            "topic:evaluations",
            f"Integrating {thought_type}: {thought}",
            message_type="internal_state",
            priority=0.6,
            metadata={"processing_type": "thought_integration"}
        )
        
        # Add to current context based on thought type
        if thought_type == 'memory':
            self.current_context.append({
                "role": "system",
                "content": f"Important memory surfaced: {thought}"
            })
        elif thought_type == 'association':
            self.current_context.append({
                "role": "system", 
                "content": f"Related thought: {thought}"
            })
        elif thought_type == 'insight':
            self.current_context.append({
                "role": "system",
                "content": f"New insight: {thought}"
            })
    
    def _get_recent_high_priority_thoughts(self, limit: int = 3) -> List[str]:
        """Get recent high-priority thoughts from message history."""
        recent_messages = self.message_bus.get_recent_messages(
            limit=20,
            message_type="thought"
        )
        
        high_priority = [
            msg.content for msg in recent_messages
            if msg.priority >= 0.7 and msg.sender != self.agent_id
        ]
        
        return high_priority[-limit:] if high_priority else []
    
    async def receive_external_input(self, content: str, callback=None):
        """Public method to receive external input."""
        await self.external_input_queue.put({
            'content': content,
            'callback': callback,
            'timestamp': datetime.now()
        })
    
    async def _cleanup(self):
        """Clean up resources."""
        self.logger.info("Experiencer shutting down")
        self.message_bus.unsubscribe(self.agent_id, "attention_approved")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            **self.get_metrics(),
            "is_processing": self.is_processing,
            "context_size": len(self.current_context),
            "decision_count": len(self.decision_history),
            "pending_inputs": self.external_input_queue.qsize()
        }