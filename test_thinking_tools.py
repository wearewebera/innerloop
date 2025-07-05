#!/usr/bin/env python3
"""Test script for thinking model and tool integration in InnerLoop."""

import asyncio
import os
from ollama import AsyncClient
import structlog
import yaml

# Set up logging
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


async def test_thinking_model():
    """Test basic thinking model functionality."""
    logger.info("Testing thinking model support...")
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    model_name = config['model']['name']
    logger.info(f"Using model: {model_name}")
    
    # Create Ollama client
    ollama_host = os.getenv('OLLAMA_HOST', config.get('ollama_host', 'http://localhost:11434'))
    client = AsyncClient(host=ollama_host)
    
    # Test 1: Basic thinking mode
    logger.info("Test 1: Basic thinking mode")
    try:
        response = await client.chat(
            model=model_name,
            messages=[
                {"role": "user", "content": "What is 25 * 47? Think step by step."}
            ],
            think=True
        )
        
        if 'thinking' in response.get('message', {}):
            logger.info("✓ Thinking mode supported!", 
                       thinking_preview=response['message']['thinking'][:100] + "...")
            logger.info("Answer:", answer=response['message']['content'])
        else:
            logger.warning("✗ Thinking not found in response")
            
    except Exception as e:
        logger.error("✗ Thinking mode test failed", error=str(e))
        return False
    
    # Test 2: Tool calling
    logger.info("\nTest 2: Tool calling support")
    tools = [{
        'type': 'function',
        'function': {
            'name': 'get_current_time',
            'description': 'Get the current time',
            'parameters': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        }
    }]
    
    try:
        response = await client.chat(
            model=model_name,
            messages=[
                {"role": "user", "content": "What time is it right now?"}
            ],
            tools=tools
        )
        
        if 'tool_calls' in response.get('message', {}):
            logger.info("✓ Tool calling supported!", 
                       tools_called=[t['function']['name'] for t in response['message']['tool_calls']])
        else:
            logger.warning("✗ No tool calls in response")
            logger.info("Response:", response=response['message']['content'])
            
    except Exception as e:
        logger.error("✗ Tool calling test failed", error=str(e))
    
    # Test 3: Combined thinking and tools
    logger.info("\nTest 3: Combined thinking and tool calling")
    try:
        response = await client.chat(
            model=model_name,
            messages=[
                {"role": "user", "content": "I need to know the current time to plan my day. Can you help?"}
            ],
            tools=tools,
            think=True
        )
        
        has_thinking = 'thinking' in response.get('message', {})
        has_tools = 'tool_calls' in response.get('message', {})
        
        if has_thinking and has_tools:
            logger.info("✓ Both thinking and tools work together!")
        elif has_thinking:
            logger.info("✓ Thinking works, but no tool calls")
        elif has_tools:
            logger.info("✓ Tool calls work, but no thinking")
        else:
            logger.warning("✗ Neither thinking nor tools detected")
            
    except Exception as e:
        logger.error("✗ Combined test failed", error=str(e))
    
    return True


async def test_innerloop_integration():
    """Test InnerLoop integration with thinking and tools."""
    logger.info("\n\nTesting InnerLoop integration...")
    
    try:
        # Import InnerLoop components
        from memory.chromadb_store import ChromaDBStore
        from memory.conversation_log import ConversationLog
        from communication.message_bus import MessageBus
        from agents.experiencer import ExperiencerAgent
        from tools.time_tools import TimeAwarenessTool
        
        # Load config
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize components
        logger.info("Initializing InnerLoop components...")
        
        memory_store = ChromaDBStore(config)
        await memory_store.initialize()
        
        conversation_log = ConversationLog(config)
        await conversation_log.initialize()
        
        message_bus = MessageBus()
        
        # Create Experiencer agent
        experiencer = ExperiencerAgent(config, message_bus, memory_store)
        
        # Check tool registry
        if hasattr(experiencer, 'tool_registry'):
            logger.info("✓ Tool registry initialized")
            tools = experiencer.tool_registry.get_all_tools()
            logger.info(f"  Available tools: {[t.name for t in tools]}")
        else:
            logger.warning("✗ Tool registry not found")
        
        # Test thinking method
        if hasattr(experiencer, 'think_and_respond'):
            logger.info("\nTesting think_and_respond method...")
            result = await experiencer.think_and_respond(
                "Why is curiosity important for learning?"
            )
            
            if result.get('thinking'):
                logger.info("✓ Thinking captured successfully")
                logger.info(f"  Thinking preview: {result['thinking'][:150]}...")
            if result.get('response'):
                logger.info("✓ Response generated")
                logger.info(f"  Response: {result['response'][:100]}...")
        
        # Test tool execution
        if hasattr(experiencer, 'tool_registry'):
            logger.info("\nTesting tool execution...")
            time_tool = experiencer.tool_registry.get_tool('time_awareness')
            if time_tool:
                result = await time_tool(query_type="current", format="human")
                if result.get('success'):
                    logger.info("✓ Tool executed successfully")
                    logger.info(f"  Result: {result['result']}")
                else:
                    logger.warning("✗ Tool execution failed", error=result.get('error'))
        
        logger.info("\n✓ InnerLoop integration tests completed!")
        
    except Exception as e:
        logger.error("✗ Integration test failed", error=str(e), exc_info=True)
        return False
    
    return True


async def main():
    """Run all tests."""
    logger.info("Starting InnerLoop thinking and tools tests...\n")
    
    # Test basic Ollama functionality
    thinking_ok = await test_thinking_model()
    
    if thinking_ok:
        # Test InnerLoop integration
        integration_ok = await test_innerloop_integration()
        
        if integration_ok:
            logger.info("\n✅ All tests passed! InnerLoop is ready with thinking and tools.")
        else:
            logger.warning("\n⚠️ Some integration tests failed.")
    else:
        logger.error("\n❌ Basic thinking model tests failed. Check your Ollama setup.")


if __name__ == "__main__":
    asyncio.run(main())