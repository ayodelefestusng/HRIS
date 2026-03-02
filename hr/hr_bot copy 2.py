# # # ==========================
# # # 🌐 Django & Project Settings (Commented out as not used in standalone script)
# # # ==========================
# from django.conf import settings
# from .models import Prompt,Prompt7
from pickle import FALSE
import re
import base64
import io
import json
# # ==========================
# # 📦 Standard Library
# # ==========================
from logging import config
import os
# from langgraph.checkpoint.postgres import PostgresSaver
# # --- Project-Specific Imports ---
# # AJADI-2
import re
# from pprint import pprint
from socket import TCP_NODELAY
import sqlite3
from datetime import datetime
from io import BytesIO
# from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional

import matplotlib.pyplot as plt
# # ==========================
import pandas as pd
from django.conf import settings
# # ==========================
# # 📦 Third-Party Core
# ==========================
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_community.utilities import SQLDatabase
# # # ==========================
# # # 🤖 LangChain Core & Community
# # # ==========================
from langchain_core.messages import (AIMessage, HumanMessage, SystemMessage,
                                     ToolMessage)
from langchain_core.tools import Tool  # Explicitly import Tool
# from langchain_core.output_parsers import JsonOutputParser
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_deepseek import \
    ChatDeepSeek  # Import ChatDeepSeek for DeepSeek LLM
# from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_google_genai import (ChatGoogleGenerativeAI,
                                    GoogleGenerativeAIEmbeddings)
from langchain_groq import ChatGroq  # For Groq LLM
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver  # Using SqliteSaver as preferred

# # # ==========================
# # # 🔁 LangGraph Imports
# # # ==========================
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, create_react_agent, tools_condition
from matplotlib.ticker import FuncFormatter
from PIL import Image
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
# # ==========================
# # 🧠 Google Generative AI
# # ==========================
# import google.generativeai as genai
# from google.generativeai import GenerativeModel, configure
# from google.generativeai.types import HarmCategory, HarmBlockThreshold


#AKADI

import operator
import os
import sqlite3
from dataclasses import dataclass
from typing import Any, List, Literal, Annotated
from typing_extensions import TypedDict

from IPython.display import Image, display
from pydantic import BaseModel, Field

from langchain.tools import tool, ToolRuntime
from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, AnyMessage

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langgraph.store.memory import InMemoryStore
from langgraph.graph.message import REMOVE_ALL_MESSAGES


from langchain_community.utilities import GoogleSerperAPIWrapper

from langchain_exa import ExaSearchResults
from langchain_exa import ExaFindSimilarResults


from django.core.mail import EmailMessage
import logging
from langgraph.checkpoint.sqlite import SqliteSaver  # Using SqliteSaver as preferred
# Ensure you import necessary components like logger, State, get_context, 
# model, SystemMessage, AIMessage, EmailMessage (if using Django's core email)
from typing import Dict, Any

from typing import Dict, Any
# Ensure you import necessary components like logger, State, get_context, 
# model, SystemMessage, AIMessage, EmailMessage (if using Django's core email)
import json
from typing import Dict, Any, Literal

import json
import re
import json
import re
from typing import Optional, Dict, Any, List






#Akadi



# Load .env file
load_dotenv()
import matplotlib

matplotlib.use('Agg') # This prevents Matplotlib from trying to open a GUI window

import matplotlib

# This must be done BEFORE importing pyplot
matplotlib.use('Agg')

import base64
import io
import logging
import re
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter
from sqlalchemy import create_engine


from langchain_openai import OpenAIEmbeddings

import logging

# ==========================
# ⚙️ Configuration & Initialization
# ==========================
# Load API keys from environment variables for security
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_API_KEY = "AIzaSyAd35RkDDAKTLZahU9AaOTUP0yxTrNqfsA"


TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") # Ensure this is set in .env if used
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Ensure this is set in .env if used
PDF_PATH = os.getenv("PDF_PATH", "default.pdf") # Default value for PDF_PATH
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
EXA_API_KEY = os.getenv("EXA_API_KEY")

# # Set environment variables for LangSmith
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = LANGSMITH_API_KEY if LANGSMITH_API_KEY else ""
os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT if LANGSMITH_PROJECT else "Agent_Creation"
os.environ["LANGSMITH_ENDPOINT"] = LANGSMITH_ENDPOINT if LANGSMITH_ENDPOINT else "https://api.smith.langchain.com"
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY if GOOGLE_API_KEY else ""
os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY if TAVILY_API_KEY else ""
os.environ["GROQ_API_KEY"] = GROQ_API_KEY if GROQ_API_KEY else ""
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY if OPENAI_API_KEY else ""

if SERPER_API_KEY:
    os.environ["SERPER_API_KEY"] = SERPER_API_KEY
    
if EXA_API_KEY:
    os.environ["EXA_API_KEY"] = EXA_API_KEY  
    



llm = init_chat_model("google_genai:gemini-flash-latest")
model = llm # Consistent naming

import os
import sqlite3
from pathlib import Path




logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="app.log",       # <-- write logs to a file
    filemode="a",             # append mode
    encoding="utf-8"          # <-- ensures emoji/unicode characters are supported
)


from typing import Optional, Dict, Any
from typing_extensions import Annotated
from langgraph.graph import MessagesState
from langgraph.channels import LastValue
from typing import Optional, Literal
from pydantic import BaseModel, Field
from langchain.tools import tool, ToolRuntime

import logging
from typing import Optional
from langchain_core.tools import tool
from tavily import TavilyClient


from typing import Optional, Any, Dict, Literal
from typing_extensions import Annotated
from langgraph.graph import MessagesState
from langgraph.channels import LastValue

       
# Use a named logger
# logger = logging.getLogger("ai")
import logging
import logging, warnings
logging.captureWarnings(True)

import traceback
import sys

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# --- Helper functions ---
def log_info(msg: str) -> None:
    """Log an info-level message."""
    logger.info(msg)

def log_error(msg: str) -> None:
    """Log an error-level message."""
    logger.error(msg)

def log_debug(msg: str) -> None:
    """Log a debug-level message."""
    logger.debug(msg)

def log_warning(msg: str) -> None:
    """Log a warning-level message."""
    logger.warning(msg)

def log_exception(e: Exception) -> None:
    """Log an exception with full traceback manually."""
    tb = traceback.format_exc()
    logger.error(f"Exception: {e}\n{tb}")

def log_exception_auto(msg: str) -> None:
    """
    Logs an error message AND automatically appends the full traceback.
    Call this from inside the 'except' block.
    """
    logger.error(msg, exc_info=True)


try:
    from django.conf import settings
    DB_PATH = Path(settings.DATABASES["default"]["NAME"])
except Exception:
    DB_PATH = Path("db.sqlite3")

CHECKPOINT_FILE = DB_PATH.parent / "langgraph_checkpoints.sqlite"


# --- 2. LangGraph Persistence (SqliteSaver) ---
try:
    # check_same_thread=False is crucial for Django/SQLite concurrency
    conn = sqlite3.connect(str(CHECKPOINT_FILE), check_same_thread=False)
    memorys = SqliteSaver(conn=conn)
    # We use a dummy config for initial logging since we are outside a request
except Exception as e:
    print(f"Failed to initialize SqliteSaver: {e}")
    memorys = None

class State(MessagesState):
    human_feedback: Optional[bool] = None
    llm_calls: int = 0
    job_description: Optional[Any] = None
    candidates: Optional[Any] = None
    outreach_content: Optional[Any] = None
    final_answer: Optional[Any] = None
    
tavily = TavilySearch(
    max_results=10,
    topic="general",
    # include_answer=False,
    include_raw_content=True,
    # include_images=False,
    # include_image_descriptions=False,
    search_depth="advanced",
    # time_range="day",
    include_domains=["https://www.linkedin.com/"],
    # exclude_domains=None
)


search = GoogleSerperAPIWrapper()
serper = Tool(
    name="Intermediate_Answer",
    func=search.run,
    description="useful for when you need to ask with search",
)

exa_search = ExaSearchResults(
    exa_api_key=os.environ["EXA_API_KEY"],
    max_results=5,
)

exa_find_similar = ExaFindSimilarResults(
    exa_api_key=os.environ["EXA_API_KEY"],
    max_results=5,
)



class SendToCandidatesInput(BaseModel):
    role: str = Field(..., description="The job role for which candidates were searched.")
    outreach_content: str = Field(..., description="The outreach message content to be sent to candidates.")
    candidate_details: Optional[Dict[str, Any]] = Field(default=None, description="diction of name and email.")


@tool("send_to_candidates_tool", args_schema=SendToCandidatesInput)
def send_to_candidates(state: Dict[str, Any]) -> Dict[str, Any]:
    """Schedules interviews 7 days from today, starting at 10am with 45min intervals."""
    logger.info("📧 Send to Candidates Tool Activated.")
    
    role = state.get("role", "the position")
    # Supports different state keys for candidates
    results = state.get("candidates") or state.get("candidates_email") or []
    if isinstance(results, dict): results = results.get("results", [])
    
    outreach_content = state.get("outreach_content", "")

    if not results:
        logger.error("Attempted to send outreach with empty candidate list.")
        return {"answer": "Error: No candidates available to message."}

    # Scheduling: 7 days from today
    interview_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    current_time = datetime.strptime("10:00 AM", "%I:%M %p")
    
    num_sent = 0
    
    try:
        for cand in results:
            name = cand.get("name", "Candidate")
            email = cand.get("email") or cand.get("linkedin_profile")
            
            if not email: continue

            time_str = current_time.strftime("%I:%M %p")
            
            # Construct Email
            email_body = (
                f"Dear {name},\n\n"
                f"You are invited to interview for the **{role}** role.\n"
                f"Date: {interview_date}\nTime: {time_str}\n\n"
                f"{outreach_content}\n\nBest, HR Team"
            )

            # Simulated send (Replace with actual EmailMessage.send())
            logger.info(f"Sending to {name} at {time_str} ({email})")
            
            # Increment time for next person: T_next = T_current + 45 mins
            current_time += timedelta(minutes=45)
            num_sent += 1

        res = f"🎉 Success! Sent emails to {num_sent} candidates. First slot: 10:00 AM, Last slot: {current_time.strftime('%I:%M %p')}."
        return {"answer": res, "final_answer": {"answer": res}}

    except Exception as e:
        logger.error(f"Critical failure in email loop: {e}", exc_info=True)
        return {"answer": f"Failure: {str(e)}"}

# Add your new tool to the list
tools = [exa_find_similar, exa_search, serper, tavily, send_to_candidates]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)




# ==========================
RECRUITMENT_PROTOCOL = """
You are a Recruitment AI. You must follow this strict linear protocol with explicit user confirmations:

PHASE 1: JOB DESCRIPTION (JD)
- Draft or extract the JD.
- STOP and ask for confirmation.
- ACTION: Only move to Phase 2 if the user says the JD is "okay", "confirmed", or similar.

PHASE 2: CANDIDATE SEARCH
- Use search tools (Tavily/Exa) to find candidates.
- Present the names and details to the user.
- STOP and ask for confirmation.
- ACTION: Only move to Phase 3 if the user says the candidate list is "okay".

PHASE 3: OUTREACH & SENDING
- Draft the outreach letter/message content.
- STOP and ask for confirmation of the message content.
- ACTION: ONLY after the user confirms the message content is "okay", call the 'send_to_candidates_tool' to finalize the process.

STRICT RULE: You are forbidden from calling 'send_to_candidates_tool' until the user has explicitly confirmed the JD, the Candidates, AND the Message Content.
"""

def assistant_node(state: State):
    # Combine the protocol with the message history
    messages = [SystemMessage(content=RECRUITMENT_PROTOCOL)] + state["messages"]
    
    # The model decides whether to use tools (search) or draft text (JD/Outreach)
    response = model_with_tools.invoke(messages)
    
    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }
    
def tool_node(state: State):
    """Executes tool calls (Tavily, Exa, Serper)."""
    last_message = state["messages"][-1]
    results = []
    for tool_call in last_message.tool_calls:
        tool = tools_by_name[tool_call["name"]]
        output = tool.invoke(tool_call["args"])
        results.append(ToolMessage(tool_outputs=output, tool_call_id=tool_call["id"]))
    return {"messages": results}
def should_call_tool(state: State):
    last_message = state["messages"][-1]
    # If the assistant produced tool calls, we route to the tool node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

def build_graph():
    workflow = StateGraph(State)

    # Simplified Nodes: Only the Assistant and the Tools
    workflow.add_node("assistant", assistant_node)
    workflow.add_node("tools", tool_node)

    workflow.set_entry_point("assistant")

    # The model calls tools when it's time to search (Step 2)
    workflow.add_conditional_edges(
        "assistant",
        should_call_tool,
        {
            "tools": "tools",
            END: END,
        },
    )

    workflow.add_edge("tools", "assistant")

    return workflow.compile(checkpointer=memorys)
# Ensure you import HumanMessage, AIMessage, build_graph, logger, and SESSION_STORE
SESSION_STORE = {}
# Compile once at startup
recruitment_graph = build_graph()

def process_message(message_content: str, session_id: str,file_path: Optional[str] = None) -> Dict[str, Any]:
    
    logger.info(f"Processing message for session {session_id}: {message_content}")  
    config = {"configurable": {"thread_id": session_id}}
    
    # Retrieve or Initialize State
    current_state = SESSION_STORE.get(session_id, {"messages": []})
    current_state["messages"].append(HumanMessage(content=message_content))

    try:
        # Run Graph
        final_state = recruitment_graph.invoke(current_state, config)
        SESSION_STORE[session_id] = final_state
        
        last_msg = final_state["messages"][-1].content
        # Prioritize tool output if it exists in final_answer
        answer = final_state.get("final_answer", {}).get("answer", last_msg)
        
        return {"answer": answer, "metadata": {"llm_calls": final_state.get("llm_calls")}}
    
    except Exception as e:
        logger.error(f"Graph execution failed: {e}", exc_info=True)
        return {"answer": "I encountered a system error. Please try again."}