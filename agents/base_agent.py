"""Base Agent class with shared functionality for all InnerLoop agents."""

import asyncio
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import structlog
from ollama import AsyncClient
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class Message(BaseModel):
    """Message structure for inter-agent communication."""
    id: str
    sender: str
    recipient: str
    content: str
    message_type: str = "thought"  # thought, decision, external, memory
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all InnerLoop agents."""
    
    def __init__(
        self,
        agent_id: str,
        config: Dict[str, Any],
        message_bus: Any,
        memory_store: Any,
        ollama_client: Optional[AsyncClient] = None
    ):
        self.agent_id = agent_id
        self.config = config
        self.message_bus = message_bus
        self.memory_store = memory_store
        
        # Extract shared identity
        self.identity = config['agents']['shared_identity']
        self.agent_config = config['agents'].get(agent_id, {})
        self.model_config = config['model']
        
        # Set up Ollama client with host from environment or config
        ollama_host = os.getenv('OLLAMA_HOST', self.config.get('ollama_host', 'http://localhost:11434'))
        self.ollama = ollama_client or AsyncClient(host=ollama_host)
        
        # Agent state
        self.is_running = False
        self.message_count = 0
        self.last_activity = datetime.now()
        
        # Logger with agent context (create early so _build_system_prompt can use it)
        self.logger = logger.bind(agent=agent_id)
        
        # Build agent prompt
        self.system_prompt = self._build_system_prompt()
        
    def _build_system_prompt(self) -> str:
        """Build the system prompt combining identity and role from files."""
        prompts_dir = Path("prompts")
        
        # Load shared identity prompt
        identity_prompt = ""
        identity_file = prompts_dir / "shared_identity.md"
        if identity_file.exists():
            identity_template = identity_file.read_text()
            # Format the template with identity values
            identity_prompt = identity_template.format(
                name=self.identity['name'],
                age=self.identity['age'],
                background=self.identity['background'],
                personality=self.identity['personality'],
                interests='\n'.join([f"- {interest}" for interest in self.identity['interests']])
            )
        else:
            # Fallback to hardcoded
            identity_prompt = (
                f"You are {self.identity['name']}, "
                f"a {self.identity['age']}-year-old {self.identity['background']}. "
                f"Your personality is {self.identity['personality']}. "
                f"Your interests include: {', '.join(self.identity['interests'])}."
            )
        
        # Load agent-specific prompt
        agent_prompt = ""
        agent_file = prompts_dir / f"{self.agent_id}.md"
        if agent_file.exists():
            agent_prompt = agent_file.read_text()
        else:
            # Fallback to config
            agent_prompt = (
                f"\nYour role in this system is: {self.agent_config.get('role', 'agent')}. "
                f"{self.agent_config.get('prompt_modifier', '')}"
            )
        
        # Combine prompts
        full_prompt = identity_prompt + "\n\n" + agent_prompt
        
        self.logger.info("Loaded system prompt", 
                        agent=self.agent_id,
                        from_files=identity_file.exists() and agent_file.exists())
        
        return full_prompt
    
    async def start(self):
        """Start the agent's main loop."""
        self.is_running = True
        self.logger.info("Agent starting", config=self.agent_config)
        
        try:
            await self._initialize()
            await self._run_loop()
        except Exception as e:
            self.logger.error("Agent error", error=str(e))
            raise
        finally:
            self.is_running = False
            self.logger.info("Agent stopped")
    
    async def stop(self):
        """Stop the agent gracefully."""
        self.is_running = False
        await self._cleanup()
    
    @abstractmethod
    async def _initialize(self):
        """Initialize agent-specific resources."""
        pass
    
    @abstractmethod
    async def _run_loop(self):
        """Main agent loop - must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def _cleanup(self):
        """Clean up agent-specific resources."""
        pass
    
    async def generate_response(self, prompt: str, context: List[Dict[str, str]] = None) -> str:
        """Generate a response using Ollama."""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if context:
            messages.extend(context)
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self.ollama.chat(
                model=self.model_config['name'],
                messages=messages,
                options={
                    "temperature": self.model_config['temperature'],
                    "num_predict": self.model_config['max_tokens'],
                }
            )
            
            return response['message']['content']
            
        except Exception as e:
            self.logger.error("Ollama generation failed", error=str(e))
            raise
    
    async def send_message(self, recipient: str, content: str, 
                          message_type: str = "thought", 
                          priority: float = 0.5,
                          metadata: Dict[str, Any] = None):
        """Send a message to another agent."""
        message = Message(
            id=f"{self.agent_id}_{self.message_count}",
            sender=self.agent_id,
            recipient=recipient,
            content=content,
            message_type=message_type,
            priority=priority,
            metadata=metadata or {}
        )
        
        self.message_count += 1
        await self.message_bus.send(message)
        
        self.logger.debug("Message sent", 
                         recipient=recipient, 
                         type=message_type,
                         priority=priority)
    
    async def receive_messages(self) -> List[Message]:
        """Receive messages from the message bus."""
        messages = await self.message_bus.receive(self.agent_id)
        if messages:
            self.last_activity = datetime.now()
            self.logger.debug("Messages received", count=len(messages))
        return messages
    
    async def store_memory(self, content: str, memory_type: str = "general"):
        """Store a memory in the memory store."""
        await self.memory_store.add_memory(
            agent_id=self.agent_id,
            content=content,
            memory_type=memory_type,
            timestamp=datetime.now()
        )
    
    async def retrieve_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant memories from the memory store."""
        return await self.memory_store.search_memories(
            query=query,
            limit=limit,
            agent_id=self.agent_id
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics for monitoring."""
        return {
            "agent_id": self.agent_id,
            "is_running": self.is_running,
            "message_count": self.message_count,
            "last_activity": self.last_activity.isoformat(),
            "uptime": (datetime.now() - self.last_activity).total_seconds()
        }