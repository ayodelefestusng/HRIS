
import os
import sys
import logging
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.prebuilt import create_react_agent
from customer.ollama_service import OllamaService
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("AGENT_TEST")

DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/hris?sslmode=disable")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "ollama_cloud")

print(f"Testing Agent with DB: {DB_URI}")

try:
    db = SQLDatabase.from_uri(DB_URI)
    llm = OllamaService(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        username="",
        password=""
    )

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()
    
    # Match the initialization in tools.py
    agent = create_react_agent(
        llm,
        tools,
        prompt="You are a SQL expert. Use the tools to answer the user query."
    )
    
    print("Agent created. Calling agent.invoke()...")
    query = "List all tables"
    res = agent.invoke({"messages": [HumanMessage(content=query)]})
    print(f"SUCCESS! Result: {res}")

except Exception as e:
    import traceback
    print(f"FAILURE: {e}")
    traceback.print_exc()
except BaseException as be:
    print(f"CRITICAL SYSTEM FAILURE: {be}")
