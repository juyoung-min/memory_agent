#!/usr/bin/env python3
"""
Reliable RAG client with retry logic
"""
import asyncio
import time
import sys
import subprocess
import json

async def run_with_retry(command, max_retries=3, delay=2):
    """Run command with retry logic"""
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries}")
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                output = result.stdout
                # Check if operation was successful
                if "success\": true" in output or "Operation successful" in output:
                    print("✅ Success!")
                    print(output)
                    return True
                elif "success\": false" in output and attempt < max_retries - 1:
                    print(f"⚠️  Operation failed, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
                    
            print(result.stdout)
            if result.stderr:
                print(f"Error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"⏱️  Timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                continue
                
        except Exception as e:
            print(f"❌ Error: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                continue
                
    return False

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client-rag-reliable.py '<original command>'")
        print("Example: python client-rag-reliable.py 'python client-rag.py http://localhost:8093 --action save --content \"test\" --namespace test'")
        sys.exit(1)
        
    command = ' '.join(sys.argv[1:])
    success = await run_with_retry(command)
    
    if not success:
        print("❌ All retry attempts failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())