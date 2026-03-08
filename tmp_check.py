
import logging
import sys
from langchain_core.messages import HumanMessage

try:
    from langchain.agents import create_agent
    print(f"SUCCESS: Imported create_agent from langchain.agents. Type: {type(create_agent)}")
except ImportError as e:
    print(f"FAILURE: Could not import create_agent from langchain.agents: {e}")

try:
    import langchain
    print(f"LangChain version: {langchain.__version__}")
except:
    print("Could not check langchain version")

try:
    import langgraph
    print(f"LangGraph version: {langgraph.__version__}")
except:
    print("Could not check langgraph version")

# Test asyncio behavior
import asyncio
import nest_asyncio

async def test_async():
    print("Async function running...")
    return "Done"

print("Testing loop...")
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
nest_asyncio.apply()

result = loop.run_until_complete(test_async())
print(f"Sync call to async returned: {result}")
