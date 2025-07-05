#!/usr/bin/env python3
"""Quick test script to verify Ollama connectivity."""

import asyncio
import os
from ollama import AsyncClient

async def test_ollama():
    """Test Ollama connection and model availability."""
    print("Testing Ollama connection...")
    
    try:
        ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        print(f"Connecting to Ollama at: {ollama_host}")
        client = AsyncClient(host=ollama_host)
        
        # Test connection
        models = await client.list()
        print(f"\n✓ Connected to Ollama")
        
        # Handle different response structures from ollama library
        model_list = []
        model_names = []
        
        # Extract model list based on response type
        if hasattr(models, 'models'):
            model_list = models.models
        elif isinstance(models, dict) and 'models' in models:
            model_list = models['models']
        elif isinstance(models, list):
            model_list = models
        
        # Extract model names
        for m in model_list:
            if isinstance(m, dict) and 'name' in m:
                model_names.append(m['name'])
            elif isinstance(m, dict) and 'model' in m:
                model_names.append(m['model'])
            elif hasattr(m, 'name'):
                model_names.append(m.name)
            elif hasattr(m, 'model'):
                model_names.append(m.model)
            elif isinstance(m, str):
                model_names.append(m)
            else:
                pass  # Skip unknown formats
            
        if model_names:
            print(f"\nAvailable models: {model_names}")
        else:
            print("\nNo models found or unable to parse model list")
        
        # Test generation with model if available
        model_name = "gemma3:27b-it-qat"
        model_found = False
        
        # Check if the model exists
        for name in model_names:
            if name.startswith(model_name.split(':')[0]):
                model_found = True
                # Use the exact model name found
                model_name = name
                break
        
        if model_found:
            print(f"\nTesting generation with {model_name}...")
            
            response = await client.chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say hello in 10 words or less."}
                ]
            )
            
            print(f"Response: {response['message']['content']}")
            print("\n✓ Ollama is working correctly!")
        else:
            print(f"\n⚠️  Model {model_name} not found. Please run: ollama pull {model_name}")
            
    except Exception as e:
        import traceback
        print(f"\n✗ Error: {e}")
        print(f"Error type: {type(e).__name__}")
        print("\nFull traceback:")
        traceback.print_exc()
        print("\nMake sure Ollama is running: ollama serve")

if __name__ == "__main__":
    asyncio.run(test_ollama())
