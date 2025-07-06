"""Message bus for inter-agent communication using asyncio queues."""

import asyncio
from typing import Dict, List, Optional, Set
from collections import defaultdict
import structlog
from datetime import datetime

from agents.base_agent import Message

logger = structlog.get_logger()


class MessageBus:
    """Simple message bus using asyncio queues for agent communication."""
    
    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size
        self.queues: Dict[str, asyncio.Queue] = {}
        self.subscribers: Dict[str, Set[str]] = defaultdict(set)
        self.message_history: List[Message] = []
        self.metrics = {
            'messages_sent': 0,
            'messages_delivered': 0,
            'messages_dropped': 0
        }
        self.logger = logger.bind(component="message_bus")
        # Add locks for thread safety
        self._metrics_lock = asyncio.Lock()
        self._history_lock = asyncio.Lock()
        
    def register_agent(self, agent_id: str):
        """Register an agent with the message bus."""
        if agent_id not in self.queues:
            self.queues[agent_id] = asyncio.Queue(maxsize=self.max_queue_size)
            self.logger.info("Agent registered", agent_id=agent_id)
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent from the message bus."""
        if agent_id in self.queues:
            del self.queues[agent_id]
            # Remove from all subscriptions
            for subscribers in self.subscribers.values():
                subscribers.discard(agent_id)
            self.logger.info("Agent unregistered", agent_id=agent_id)
    
    def subscribe(self, agent_id: str, topic: str):
        """Subscribe an agent to a topic."""
        self.subscribers[topic].add(agent_id)
        self.logger.debug("Agent subscribed", agent_id=agent_id, topic=topic)
    
    def unsubscribe(self, agent_id: str, topic: str):
        """Unsubscribe an agent from a topic."""
        self.subscribers[topic].discard(agent_id)
        self.logger.debug("Agent unsubscribed", agent_id=agent_id, topic=topic)
    
    async def send(self, message: Message):
        """Send a message to recipient(s)."""
        async with self._metrics_lock:
            self.metrics['messages_sent'] += 1
        
        async with self._history_lock:
            self.message_history.append(message)
            
            # Keep history limited
            if len(self.message_history) > 1000:
                self.message_history = self.message_history[-1000:]
        
        # Direct message to specific recipient
        if message.recipient in self.queues:
            await self._deliver_to_agent(message.recipient, message)
        
        # Broadcast to topic subscribers if recipient is a topic
        elif message.recipient.startswith("topic:"):
            topic = message.recipient[6:]  # Remove "topic:" prefix
            for subscriber in self.subscribers.get(topic, []):
                await self._deliver_to_agent(subscriber, message)
        
        # Special broadcast to all agents
        elif message.recipient == "broadcast":
            for agent_id in self.queues:
                if agent_id != message.sender:  # Don't send to self
                    await self._deliver_to_agent(agent_id, message)
        
        else:
            self.logger.warning("Unknown recipient", 
                              recipient=message.recipient,
                              sender=message.sender)
            async with self._metrics_lock:
                self.metrics['messages_dropped'] += 1
    
    async def _deliver_to_agent(self, agent_id: str, message: Message):
        """Deliver a message to a specific agent."""
        try:
            queue = self.queues.get(agent_id)
            if queue:
                # Try to put message without blocking
                try:
                    queue.put_nowait(message)
                    async with self._metrics_lock:
                        self.metrics['messages_delivered'] += 1
                    self.logger.debug("Message delivered", 
                                    recipient=agent_id,
                                    sender=message.sender,
                                    type=message.message_type)
                except asyncio.QueueFull:
                    # Queue is full, drop oldest message
                    try:
                        queue.get_nowait()
                        queue.put_nowait(message)
                        async with self._metrics_lock:
                            self.metrics['messages_delivered'] += 1
                            self.metrics['messages_dropped'] += 1
                        self.logger.warning("Queue full, dropped oldest message", 
                                          agent_id=agent_id)
                    except:
                        async with self._metrics_lock:
                            self.metrics['messages_dropped'] += 1
                        self.logger.error("Failed to deliver message", 
                                        agent_id=agent_id)
        except Exception as e:
            self.logger.error("Message delivery error", 
                            agent_id=agent_id,
                            error=str(e))
            async with self._metrics_lock:
                self.metrics['messages_dropped'] += 1
    
    async def receive(self, agent_id: str, timeout: Optional[float] = None) -> List[Message]:
        """Receive all pending messages for an agent."""
        messages = []
        queue = self.queues.get(agent_id)
        
        if not queue:
            self.logger.warning("Agent not registered", agent_id=agent_id)
            return messages
        
        # Get all messages currently in queue
        while not queue.empty():
            try:
                message = queue.get_nowait()
                messages.append(message)
            except asyncio.QueueEmpty:
                break
        
        # If no messages and timeout specified, wait for at least one
        if not messages and timeout:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=timeout)
                messages.append(message)
                
                # Get any additional messages that arrived
                while not queue.empty():
                    try:
                        message = queue.get_nowait()
                        messages.append(message)
                    except asyncio.QueueEmpty:
                        break
                        
            except asyncio.TimeoutError:
                pass
        
        return messages
    
    async def receive_one(self, agent_id: str, timeout: Optional[float] = None) -> Optional[Message]:
        """Receive a single message for an agent."""
        queue = self.queues.get(agent_id)
        
        if not queue:
            self.logger.warning("Agent not registered", agent_id=agent_id)
            return None
        
        try:
            if timeout:
                message = await asyncio.wait_for(queue.get(), timeout=timeout)
            else:
                message = await queue.get()
            return message
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            self.logger.error("Receive error", agent_id=agent_id, error=str(e))
            return None
    
    def get_queue_size(self, agent_id: str) -> int:
        """Get the current queue size for an agent."""
        queue = self.queues.get(agent_id)
        return queue.qsize() if queue else 0
    
    def get_metrics(self) -> Dict[str, any]:
        """Get message bus metrics."""
        queue_sizes = {
            agent_id: self.get_queue_size(agent_id) 
            for agent_id in self.queues
        }
        
        return {
            **self.metrics,
            'registered_agents': len(self.queues),
            'total_subscriptions': sum(len(subs) for subs in self.subscribers.values()),
            'queue_sizes': queue_sizes,
            'history_size': len(self.message_history)
        }
    
    async def get_recent_messages(self, limit: int = 100, 
                          agent_id: Optional[str] = None,
                          message_type: Optional[str] = None) -> List[Message]:
        """Get recent messages from history with optional filtering."""
        async with self._history_lock:
            messages = self.message_history[-limit:]
        
        if agent_id:
            messages = [m for m in messages 
                       if m.sender == agent_id or m.recipient == agent_id]
        
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]
        
        return messages