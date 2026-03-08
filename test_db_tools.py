
import os
import sys
import logging
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from customer.ollama_service import OllamaService
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("DB_TEST")

DB_URI = os.getenv("DB_URI", "postgresql://postgres:postgres@localhost:5432/hris?sslmode=disable")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "ollama_cloud")

print(f"Testing connection to: {DB_URI}")

try:
    db = SQLDatabase.from_uri(DB_URI)
    print("SUCCESS: SQLDatabase connection established.")
    print(f"Dialect: {db.dialect}")
    print(f"Tables: {db.get_usable_table_names()}")

    llm = OllamaService(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        username="",
        password=""
    )

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()
    print(f"Toolkit initialized with {len(tools)} tools.")

    # Test a simple tool call directly
    list_tables_tool = next(t for t in tools if t.name == "sql_db_list_tables")
    print("Executing sql_db_list_tables tool...")
    res = list_tables_tool.invoke("")
    print(f"Tool Result: {res}")

    print("--- TEST COMPLETE ---")

except Exception as e:
    import traceback
    print(f"FAILURE: {e}")
    traceback.print_exc()
except BaseException as be:
    print(f"CRITICAL SYSTEM FAILURE: {be}")
