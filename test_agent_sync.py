
import os
import sys
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from unittest.mock import MagicMock

# Dummy LLM
class MockLLM:
    def invoke(self, messages, **kwargs):
        from langchain_core.messages import AIMessage
        return AIMessage(content="Final Answer: done")
    def bind_tools(self, tools, **kwargs):
        return self

llm = MockLLM()
tools = []
agent = create_react_agent(llm, tools)

print("Starting agent.invoke()...")
try:
    res = agent.invoke({"messages": [HumanMessage(content="test")]})
    print(f"SUCCESS: {res}")
except Exception as e:
    print(f"FAILURE: {e}")
