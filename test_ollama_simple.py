#!/usr/bin/env python3
"""Simple Ollama connection test."""

import asyncio
import os
from ollama import AsyncClient

async def test_simple():
    """Basic Ollama test."""
    ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    print(f"Testing Ollama at: {ollama_host}")
    
    try:
        client = AsyncClient(host=ollama_host)
        
        # Try the simplest possible call
        print("\n1. Testing list models...")
        result = await client.list()
        print(f"   Result type: {type(result)}")
        print(f"   Result: {result}")
        
        # Try a simple generation with a common model
        print("\n2. Testing generation...")
        try:
            response = await client.generate(
                model="llama2",  # Try a common model
                prompt="Hello"
            )
            print(f"   Success! Response: {response}")
        except Exception as e:
            print(f"   Generation failed: {e}")
            
            # Try chat instead
            print("\n3. Testing chat...")
            response = await client.chat(
                model="llama2",
                messages=[{"role": "user", "content": "Hello"}]
            )
            print(f"   Success! Response: {response}")
            
    except Exception as e:
        import traceback
        print(f"\nError: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple())