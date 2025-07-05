#!/usr/bin/env python3
"""InnerLoop - AI with autonomous initiative - Simple CLI version."""

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
from ui.thought_display import ThoughtDisplay
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


class InnerLoop:
    """Main InnerLoop system orchestrator."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = None
        self.agents = {}
        self.message_bus = None
        self.memory_store = None
        self.conversation_logger = None
        self.thought_display = None
        self.session_id = None
        self.is_running = False
        
    async def initialize(self):
        """Initialize all system components."""
        logger.info("Initializing InnerLoop...")
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize message bus
        self.message_bus = MessageBus(
            max_queue_size=self.config['performance']['message_queue_size']
        )
        
        # Initialize thought display
        self.thought_display = ThoughtDisplay(self.config, self.message_bus)
        
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
        
        # Test Ollama connectivity before initializing agents
        await self._test_ollama_connection()
        
        # Initialize agents
        logger.info("Initializing agents...")
        
        # Register agents with message bus
        for agent_id in ['experiencer', 'stream_generator', 'attention_director']:
            self.message_bus.register_agent(agent_id)
        
        # Register thought monitor for the display
        self.message_bus.register_agent('thought_monitor')
        
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
        
        logger.info("InnerLoop initialized successfully")
    
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
        """Start all agents and the system."""
        self.is_running = True
        logger.info("Starting InnerLoop agents...")
        
        # Start all agents
        agent_tasks = []
        for name, agent in self.agents.items():
            task = asyncio.create_task(agent.start())
            agent_tasks.append(task)
            logger.info(f"Started {name} agent")
        
        # Start thought display monitoring
        await self.thought_display.start_monitoring()
        
        # Start monitoring task
        monitor_task = asyncio.create_task(self._monitor_system())
        
        # Start user input handler
        input_task = asyncio.create_task(self._handle_user_input())
        
        # Wait for all tasks
        try:
            await asyncio.gather(*agent_tasks, monitor_task, input_task)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error("System error", error=str(e))
        finally:
            await self.shutdown()
    
    async def _handle_user_input(self):
        """Handle user input in a simple CLI interface."""
        print("\n" + "="*60)
        print("InnerLoop AI - Ready for conversation")
        print("="*60)
        print(f"\nHello! I'm {self.config['agents']['shared_identity']['name']}.")
        print("Type your message and press Enter. Type 'quit' to exit.\n")
        
        # Create a task to periodically display thoughts
        thought_display_task = asyncio.create_task(self._periodic_thought_display())
        
        while self.is_running:
            try:
                # Display any pending thoughts before user input
                self.thought_display.display_thoughts()
                
                # Get user input (in a thread to not block async)
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "You: "
                )
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("\nGoodbye! It was nice talking with you.")
                    self.is_running = False
                    break
                
                if user_input.strip():
                    # Log the conversation
                    await self.conversation_logger.log_conversation(
                        self.session_id, "user", user_input
                    )
                    
                    # Send to experiencer and wait for response
                    response_received = asyncio.Event()
                    response_text = None
                    
                    async def response_callback(response):
                        nonlocal response_text
                        response_text = response
                        response_received.set()
                    
                    await self.agents['experiencer'].receive_external_input(
                        user_input, response_callback
                    )
                    
                    # Wait for response with timeout, displaying thoughts while waiting
                    try:
                        start_time = asyncio.get_event_loop().time()
                        timeout_duration = 30
                        
                        while not response_received.is_set():
                            # Check if we've timed out
                            if asyncio.get_event_loop().time() - start_time > timeout_duration:
                                raise asyncio.TimeoutError()
                            
                            # Wait a bit for response or display thoughts
                            try:
                                await asyncio.wait_for(response_received.wait(), timeout=1.0)
                            except asyncio.TimeoutError:
                                # Display any new thoughts while waiting
                                self.thought_display.display_thoughts(limit=2)
                        
                        if response_text:
                            # Display any final thoughts before the response
                            self.thought_display.display_thoughts()
                            
                            print(f"\nAlex: {response_text}\n")
                            
                            # Log the response
                            await self.conversation_logger.log_conversation(
                                self.session_id, "alex", response_text
                            )
                    except asyncio.TimeoutError:
                        print("\n[System: Response timeout]\n")
                
            except EOFError:
                # Handle Ctrl+D
                break
            except Exception as e:
                logger.error("Input handling error", error=str(e))
                print(f"\n[Error: {str(e)}]\n")
        
        # Cancel the thought display task
        thought_display_task.cancel()
        try:
            await thought_display_task
        except asyncio.CancelledError:
            pass
    
    async def _periodic_thought_display(self):
        """Periodically display thoughts when idle."""
        while self.is_running:
            try:
                # Wait for a period
                await asyncio.sleep(5.0)  # Display thoughts every 5 seconds when idle
                
                # Only display if we're not actively processing
                if not hasattr(self.agents.get('experiencer', {}), 'is_processing') or \
                   not self.agents['experiencer'].is_processing:
                    self.thought_display.display_thoughts(limit=1)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Periodic thought display error", error=str(e))
    
    async def _monitor_system(self):
        """Monitor system health and performance."""
        while self.is_running:
            try:
                # Log system metrics every 30 seconds
                await asyncio.sleep(30)
                
                # Get agent metrics
                for name, agent in self.agents.items():
                    metrics = agent.get_metrics()
                    logger.info(f"{name} metrics", **metrics)
                
                # Get message bus metrics
                bus_metrics = self.message_bus.get_metrics()
                logger.info("Message bus metrics", **bus_metrics)
                
                # Get memory stats
                memory_stats = self.memory_store.get_stats()
                logger.info("Memory store stats", **memory_stats)
                
            except Exception as e:
                logger.error("Monitoring error", error=str(e))
    
    async def shutdown(self):
        """Gracefully shutdown the system."""
        logger.info("Shutting down InnerLoop...")
        self.is_running = False
        
        # Stop thought display
        if self.thought_display:
            await self.thought_display.stop_monitoring()
        
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
    print("\n🧠 InnerLoop - AI with Autonomous Initiative")
    print("Starting system...\n")
    
    innerloop = InnerLoop()
    
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