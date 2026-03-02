
import os
import sys
import json
import re
import logging
import traceback
import sqlite3
import base64
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Annotated

# --- Third-Party / Data Science ---
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Essential for headless/server environments
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from dotenv import load_dotenv

# --- Django Initialization ---
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

# --- LangChain & LangGraph Core ---
from langchain_core.messages import (
    AIMessage, HumanMessage, SystemMessage, ToolMessage, AnyMessage
)
from langchain_core.tools import tool, Tool
from langchain.chat_models import init_chat_model
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

# --- Search & Tools ---
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_community.utilities import SQLDatabase
from langchain_tavily import TavilySearch
from langchain_exa import ExaSearchResults, ExaFindSimilarResults
from django.core.mail import EmailMessage

# ==========================
# ⚙️ Configuration & Environment
# ==========================
load_dotenv()

# Environment Variable Mapping
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "AIzaSy...") # Replace with env var
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY", "")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
os.environ["SERPER_API_KEY"] = os.getenv("SERPER_API_KEY", "")
os.environ["EXA_API_KEY"] = os.getenv("EXA_API_KEY", "")

# LangSmith Tracing
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "Agent_Creation")

# ==========================
# 📝 Logging Configuration
# ==========================
# We rely on Django settings.LOGGING via the name 'hr.hr_bot' (or similar)
logger = logging.getLogger(__name__)

# --- Logger Helpers ---
def log_info(msg: str) -> None: logger.info(msg)
def log_debug(msg: str) -> None: logger.debug(msg)
def log_error(msg: str) -> None: logger.error(msg)
def log_exception_auto(msg: str) -> None: logger.error(msg, exc_info=True)

# ==========================
# 🤖 Model & State
# ==========================


model = init_chat_model("google_genai:gemini-flash-latest")
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
    job_description: Optional[str] = None
    candidates: Optional[List[Dict[str, Any]]] = None
    outreach_content: Optional[str] = None
    final_answer: Optional[Dict[str, Any]] = None
    
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

def process_message(message_content: str, session_id: str, file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Processes the user message through the LangGraph recruitment agent.
    Includes robust logging and data sanitization to prevent downstream crashes.
    """
    logger.info("🚀 process_message started | Session: %s", session_id)
    
    if file_path:
        logger.debug("📎 Attachment detected for session %s: %s", session_id, file_path)

    config = {"configurable": {"thread_id": session_id}}
    
    # 1. State Retrieval & Initialization
    # Ensure current_state matches the expected graph State structure
    current_state = SESSION_STORE.get(session_id)
    if not current_state:
        logger.info("🆕 Initializing new state for session: %s", session_id)
        current_state = {"messages": []}
    
    current_state["messages"].append(HumanMessage(content=message_content))

    try:
        # 2. Graph Execution
        logger.debug("🧠 Invoking Recruitment Graph for session %s", session_id)
        final_state = recruitment_graph.invoke(current_state, config)
        
        # Persist the state back to the store
        SESSION_STORE[session_id] = final_state
        
        
        # 1. Get the last message object
        last_message = final_state["messages"][-1]
        raw_text = ""

        # 2. Robust Extraction (Adapting to Gemini's list-of-dicts format)
        if isinstance(last_message.content, list):
            # Loop through blocks to find the 'text' type
            for block in last_message.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    raw_text += block.get("text", "")
                elif isinstance(block, str):
                    raw_text += block
        else:
            # Standard string content
            raw_text = last_message.content
        
        # 3. Safe Extraction of the Answer
        # We check final_answer first (from tools), then fall back to the last AI message
        last_msg_obj = final_state["messages"][-1]
        
        # Retrieve final_answer dict if it exists
        # final_ans_dict = final_state.get("final_answer", {})
        answer = raw_text

        # 🛡️ CRITICAL FIX: Flatten answer if it is a list to prevent Markdown 'strip' errors
        if isinstance(answer, list):
            logger.warning("⚠️ Graph returned 'answer' as a list for session %s. Flattening to string.", session_id)
            answer = " ".join([str(item) for item in answer])
            
        logger.info("✅ Graph execution successful for session %s", session_id)
        
        # 4. Final Payload Construction
        return {
            "answer": answer,
            "chart": None, # Captured if a tool generated a chart
            "metadata": {
                "llm_calls": final_state.get("llm_calls", 0),
                "session_id": session_id
            }
        }
    
    except Exception as e:
        # Use exc_info=True to ensure the full traceback is written to hr_error.log
        logger.error("❌ Graph execution failed for session %s: %s", session_id, str(e), exc_info=True)
        return {
            "answer": "I'm sorry, I encountered a system error while processing your request.",
            "metadata": {"error": str(e)}
        }