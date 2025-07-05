#!/usr/bin/env python3
"""InnerLoop - AI with autonomous initiative - Textual TUI version."""

import asyncio
import os
import sys
from pathlib import Path
import yaml
import structlog
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.experiencer import ExperiencerAgent
from agents.stream_generator import StreamGeneratorAgent
from agents.attention_director import AttentionDirectorAgent
from communication.message_bus import MessageBus
from memory.chromadb_store import ChromaMemoryStore
from memory.conversation_log import ConversationLogger
from ui.innerloop_tui import InnerLoopTUI
from ollama import AsyncClient

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class InnerLoopSystem:
    """Main InnerLoop system orchestrator for TUI."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = None
        self.agents = {}
        self.message_bus = None
        self.memory_store = None
        self.conversation_logger = None
        self.session_id = None
        self.is_running = False
        self.tui_app = None
        
    async def initialize(self):
        """Initialize all system components."""
        logger.info("Initializing InnerLoop TUI...")
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize message bus
        self.message_bus = MessageBus(
            max_queue_size=self.config['performance']['message_queue_size']
        )
        
        # Initialize memory stores
        self.memory_store = ChromaMemoryStore(
            collection_name=self.config['memory']['chromadb']['collection_name']
        )
        
        self.conversation_logger = ConversationLogger(
            db_path=self.config['memory']['sqlite']['db_path']
        )
        await self.conversation_logger.initialize()
        
        # Generate session ID
        from datetime import datetime
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Test Ollama connectivity
        await self._test_ollama_connection()
        
        # Initialize agents
        logger.info("Initializing agents...")
        
        # Register agents with message bus
        for agent_id in ['experiencer', 'stream_generator', 'attention_director']:
            self.message_bus.register_agent(agent_id)
        
        # Create agents
        self.agents['experiencer'] = ExperiencerAgent(
            self.config, self.message_bus, self.memory_store
        )
        
        self.agents['stream_generator'] = StreamGeneratorAgent(
            self.config, self.message_bus, self.memory_store
        )
        
        self.agents['attention_director'] = AttentionDirectorAgent(
            self.config, self.message_bus, self.memory_store
        )
        
        # Create TUI app
        self.tui_app = InnerLoopTUI(
            message_bus=self.message_bus,
            agents=self.agents,
            config=self.config
        )
        
        # Set memory store reference for metrics
        self.tui_app.memory_store = self.memory_store
        
        logger.info("InnerLoop TUI initialized successfully")
    
    async def _test_ollama_connection(self):
        """Test Ollama connectivity before starting agents."""
        ollama_host = os.getenv('OLLAMA_HOST', self.config.get('ollama_host', 'http://localhost:11434'))
        logger.info(f"Testing Ollama connection at {ollama_host}")
        
        try:
            client = AsyncClient(host=ollama_host)
            
            # Test basic connectivity
            models = await client.list()
            
            # Check if configured model exists
            model_name = self.config['model']['name']
            model_found = False
            
            # Handle different response structures
            model_list = []
            if hasattr(models, 'models'):
                model_list = models.models
            elif isinstance(models, dict) and 'models' in models:
                model_list = models['models']
            
            for m in model_list:
                # Check for 'model' attribute (ollama library) or 'name' (dict)
                m_name = None
                if hasattr(m, 'model'):
                    m_name = m.model
                elif isinstance(m, dict) and 'model' in m:
                    m_name = m['model']
                elif isinstance(m, dict) and 'name' in m:
                    m_name = m['name']
                
                if m_name and m_name.startswith(model_name.split(':')[0]):
                    model_found = True
                    break
            
            if not model_found:
                logger.warning(f"Model '{model_name}' not found in Ollama")
                # Extract model names for display
                available = []
                for m in model_list:
                    if hasattr(m, 'model'):
                        available.append(m.model)
                    elif isinstance(m, dict) and 'model' in m:
                        available.append(m['model'])
                    elif isinstance(m, dict) and 'name' in m:
                        available.append(m['name'])
                logger.info(f"Available models: {available}")
                logger.warning(f"Please run: ollama pull {model_name}")
                # Don't fail, just warn - the model might still work
            else:
                logger.info(f"Model '{model_name}' is available")
                
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            logger.error(f"Make sure Ollama is running at {ollama_host}")
            raise
    
    async def start(self):
        """Start all agents and the TUI."""
        self.is_running = True
        logger.info("Starting InnerLoop agents...")
        
        # Start all agents
        agent_tasks = []
        for name, agent in self.agents.items():
            task = asyncio.create_task(agent.start())
            agent_tasks.append(task)
            logger.info(f"Started {name} agent")
        
        # Give agents a moment to start
        await asyncio.sleep(1)
        
        # Run the TUI app
        logger.info("Starting TUI interface...")
        
        # Run TUI (Textual handles the async loop)
        try:
            # Textual apps run synchronously but handle async internally
            await self.tui_app.run_async()
        except Exception as e:
            logger.error("TUI error", error=str(e))
        finally:
            # Cancel agent tasks
            for task in agent_tasks:
                task.cancel()
            await self.shutdown()
    
    async def shutdown(self):
        """Gracefully shutdown the system."""
        logger.info("Shutting down InnerLoop...")
        self.is_running = False
        
        # Stop all agents
        for name, agent in self.agents.items():
            await agent.stop()
            logger.info(f"Stopped {name} agent")
        
        # Close database connections
        if self.conversation_logger:
            await self.conversation_logger.close()
        
        logger.info("InnerLoop shutdown complete")


async def main():
    """Main entry point."""
    print("\n🧠 InnerLoop - AI with Autonomous Initiative (TUI)")
    print("Starting system...\n")
    
    innerloop = InnerLoopSystem()
    
    try:
        await innerloop.initialize()
        await innerloop.start()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    except Exception as e:
        logger.error("Fatal error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())