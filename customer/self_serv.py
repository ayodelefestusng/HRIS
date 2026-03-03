# ==================================
# 📦 Standard Library Imports
# ==================================
import base64
from collections import UserDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from importlib import metadata
import io
import json
import logging
from math import log
import operator
import os
from pdb import run
import re
import sqlite3
import sys
import time
from typing import Any, Dict, List, Literal, Optional, Union, Annotated
import uuid
# from xxlimited import Str
from sympy import dict_merge, use
from typing_extensions import TypedDict, Literal
from xml.dom.minidom import Document
from io import BytesIO

# ==================================
# 📦 Third-Party Libraries (General)
# ==================================
from dotenv import load_dotenv
from PIL import Image
from pydantic import BaseModel, Field, ValidationError  # Pydantic for data models
from sqlalchemy import Boolean, create_engine
from yarl import Query  # For SQL operations
from langgraph.graph import END, START, MessagesState, StateGraph
from pprint import pprint

import pdfplumber
from pdf2image import convert_from_path
import pytesseract
# from PyPDF2 import PdfReader  # for PDF text extraction
# import easyocr  # Commented out as per original

load_dotenv()

# ==================================
# 🌐 Django & Project Settings
# ==================================
from django.conf import settings
from rest_framework.exceptions import NotFound  # Example exception for Tenant Not Found

# --- Project-Specific Imports ---
from .models import Conversation, Tenant  # Adjusted based on available imports
# from .models import Prompt, Prompt7 # Commented out as per original
# import matplotlib # Commented out as per original
from bson import ObjectId
# ==================================
# 🤖 LangChain/LangGraph Core
# ==================================
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, SystemMessage, RemoveMessage
from langchain.tools import tool, ToolRuntime
from langchain_core.documents import Document
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    AnyMessage,
)
from langchain_core.tools import Tool
from langchain_core.vectorstores import VectorStore
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, Send
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver  # Checkpoint
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.sqlite import SqliteStore

# ==================================
# 🚀 LangChain/LangGraph Integrations
# ==================================
# --- LLMs ---
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # OpenAI LLM and Embeddings

# --- Tools/Utilities ---
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_community.utilities import SQLDatabase
from langchain_community.vectorstores import Chroma, FAISS
from langchain_tavily import TavilySearch
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ==================================
# 🎨 Display/Notebook Utilities
# ==================================
from IPython.display import Image, display

# from sympy import principal_branch # Commented out (seems unrelated)



# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     handlers=[logging.StreamHandler(sys.stdout)],  # Explicitly use UTF-8 stdout
# )

# Removed any reference to a 'file' handler to avoid configuration errors.


# logger = logging.getLogger(__name__)
# logger = logging.getLogger("ai")



# ==========================
# 📝 Logging Configuration
# ==========================
import sys
import logging

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

logging.captureWarnings(True)

import logging
import sys
from typing import Optional
from bson import ObjectId
from datetime import datetime, timedelta
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from langchain_core.messages import ToolMessage

import logging
import sys
from typing import List, Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime, timedelta

# Unified Logging Configuration
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("app.log", encoding="utf-8")],
    force=True,
)
logger = logging.getLogger("HR_AGENT")

class HRLogger:
    @staticmethod
    def _ctx(config):
        cfg = config.get("configurable", {})
        return {
            "t_id": cfg.get("tenant_id", "N/A"),
            "c_id": cfg.get("thread_id", "N/A"),
            "e_id": cfg.get("employee_id", "N/A")
        }

    @classmethod
    def info(cls, msg, config):
        ctx = cls._ctx(config)
        logger.info(f"[Tenant: {ctx['t_id']} | Conv: {ctx['c_id']} | Emp: {ctx['e_id']}] {msg}")

    @classmethod
    def error(cls, msg, config, exc=None):
        ctx = cls._ctx(config)
        logger.error(f"[Tenant: {ctx['t_id']} | Conv: {ctx['c_id']} | Emp: {ctx['e_id']}] {msg}", exc_info=exc)
# 1. API Keys (Load from environment)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Ensure this is set in .env if used

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = "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"
os.environ["LANGSMITH_PROJECT"] = "pr-loyal-retirement-94"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
# os.environ["GOOGLE_API_KEY"] = "AIzaSyAvickMfWOE8-GPch0NygEzFUu-oYoLWLo"


os.environ["GOOGLE_API_KEY"] = "AIzaSyDrG82q_R_Br-gGbIaKtWDObM4LoG2D49Q"
# os.environ["GOOGLE_API_KEY"] = "AIzaSyA-Ea8B4L0WrS9oRzYndubhoakWKQZFJM4"

# os.environ["GOOGLE_API_KEY"] = "AIzaSyCaXfaJtPDulbSjSA3Aiio-idDAFWrnVNs"   # Updated key on 2025-12-19 ATB sekf ayodefestus
os.environ["TAVILY_API_KEY"] = "lsv2_pt_b52435093087464baaba87923a5051c2_8b39a6c"


# 2. Model/Service Name Variables
# google_model = "gemini-2.0-flash"
google_model = "gemini-flash-latest"
# chatbot_model = py.chatbot_model # Kept here as it appears to be a separate configuration variable


## Initialization of Tools and Components

# 3. Embeddings Model Initialization
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

# 4. Chat Model Initialization
# Note: "google_genai:gemini-flash-latest" is often a shortcut for the latest flash model
from langchain.chat_models import init_chat_model

llm = init_chat_model("google_genai:gemini-flash-latest")
model = llm  # Consistent naming for the primary LLM

# 5. Tool Initialization
# from langchain_community.tools.tavily_search import TavilySearchResults
tavily_search = TavilySearch(max_results=2)
search_tool = TavilySearch(
    max_results=5,
    include_raw_content=True,
)

# Placeholders for global startup logs
import os
import sqlite3
from pathlib import Path
from pymongo import MongoClient
from langchain_community.utilities import SQLDatabase
from langgraph.checkpoint.sqlite import SqliteSaver
from django.conf import settings

# --- 1. Path Management ---
# Using Pathlib for robust cross-platform path handling
DJANGO_DB_PATH = Path(settings.DATABASES["default"]["NAME"])
BASE_DIR = DJANGO_DB_PATH.parent

# Define the Checkpoint Database (for LangGraph memory)
CHECKPOINT_FILE = BASE_DIR / "langgraph_checkpoints.sqlite"

# --- 2. LangGraph Persistence (SqliteSaver) ---
try:
    # check_same_thread=False is crucial for Django/SQLite concurrency
    conn = sqlite3.connect(str(CHECKPOINT_FILE), check_same_thread=False)
    memorys = SqliteSaver(conn=conn)
    # We use a dummy config for initial logging since we are outside a request
    HRLogger.info(f"LangGraph Persistence initialized at {CHECKPOINT_FILE}", config={})
except Exception as e:
    print(f"Failed to initialize SqliteSaver: {e}")
    memorys = None

# --- 3. SQL Database (Read-only access for Agent) ---
# Ensure URI is properly formatted for SQLAlchemy
DB_URI = f"sqlite:///{DJANGO_DB_PATH.as_posix()}"
db_sql = None

try:
    db_sql = SQLDatabase.from_uri(DB_URI)
    HRLogger.info(f"SQLDatabase (Django DB) linked successfully via {DB_URI}", config={})
except Exception as e:
    HRLogger.error(f"SQLDatabase connection failed: {e}", config={}, exc=True)

# --- 4. MongoDB (Main HR Data) ---
# Using the credentials provided
MONGO_URI = "mongodb://myxalary:Pass%40word1@84.247.163.98:27017/myxalary?authSource=myxalary"
# In your DB config section
db_mongo = None
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # This line is critical to verify the connection actually works
    client.admin.command('ping')
    db_mongo = client["myxalary"]
    # Trigger a quick command to verify connection
    client.admin.command('ping')
    HRLogger.info("MongoDB connection established successfully", config={})
except Exception as e:
    HRLogger.error(f"MongoDB connection failed: {e}", config={}, exc=True)
    

def safe_json(data):
    """Ensures safe JSON serialization to prevent errors."""
    import json  # Import json locally if it's not imported at the top-level

    try:
        return json.dumps(data)
    except (TypeError, ValueError):
        return json.dumps({})  # Returns an empty JSON object if serialization fails

def initialize_vector_store(tenant_id: str):
    """
    Initializes and connects to the FAISS vector store for a given tenant.

    Returns:
        FAISS | dict: The initialized FAISS vector store object on success,
                      or a dictionary with error details on failure.
    """
    # Set a default conversation_id for structured logging consistency
    conversation_id = ""

    # 1. Test embedding model
    try:
        test_emb = embeddings.embed_query("Test embedding")
        log_info(
            f"Embedding model tested successfully. Vector dimension: {len(test_emb)}",
            tenant_id,
            conversation_id,
        )
    except Exception as e:
        log_exception_auto(
            f"FATAL: Embedding model failed to initialize.", tenant_id, conversation_id
        )
        return {
            "status": "error",
            "code": "VEC-5001",
            "message": "Internal service error: Failed to initialize the core embedding model.",
            "http_status": 500,
        }

    # --- Setup Persistence Path and File Checks ---
    persist_directory = os.path.join(settings.BASE_DIR, "faiss_dbs", tenant_id)
    faiss_index_path = os.path.join(persist_directory, "index.faiss")

    # 2. LOAD FROM DISK CHECK (Persistence)
    if os.path.exists(faiss_index_path):
        try:
            log_info(
                f"Attempting to load existing FAISS index from disk: {persist_directory}",
                tenant_id,
                conversation_id,
            )
            vector_store = FAISS.load_local(
                folder_path=persist_directory,
                embeddings=embeddings,
                allow_dangerous_deserialization=True,
            )
            log_info(
                "Successfully loaded existing FAISS index.", tenant_id, conversation_id
            )
            return vector_store
        except Exception as e:
            # Handle corrupted or incompatible index files
            log_exception_auto(
                f"Failed to load existing FAISS index. Attempting re-index. Error: {e}",
                tenant_id,
                conversation_id,
            )
            # Fall through to the creation logic below

    # --- Document File Retrieval ---
    file_path = None
    try:
        tenant = Tenant.objects.get(tenant_id=tenant_id)
        # Assuming the field is 'tenant_mandate' or 'tenant_faq' based on previous context,
        # but using 'tenant_faq' as in the provided code.
        if tenant.tenant_faq:
            file_path = tenant.tenant_faq.path
            log_info(
                f"Retrieved KSS file path: {file_path}", tenant_id, conversation_id
            )
        else:
            log_warning(
                f"Tenant profile found, but KSS file link is empty.",
                tenant_id,
                conversation_id,
            )

    except Tenant.DoesNotExist:
        log_error(
            "Tenant profile not found. Cannot initialize vector store.",
            tenant_id,
            conversation_id,
        )
        return {
            "status": "error",
            "code": "VEC-4041",
            "message": "Tenant profile not found. Vector store cannot be initialized.",
            "http_status": 404,
        }
    except AttributeError:
        # Catches error if tenant_kss is None or lacks a .path attribute
        log_error(
            "Tenant profile found but 'tenant_faq' file path is missing.",
            tenant_id,
            conversation_id,
        )

    # Check if the file exists on disk
    if not file_path or not os.path.exists(file_path):
        log_warning(
            f"Required document file not found on disk at {file_path}. Returning empty store.",
            tenant_id,
            conversation_id,
        )
        # Return an empty FAISS index (graceful fallback)
        return FAISS.from_texts([""], embeddings)

    # --- Create Index (If Load Failed or Index Didn't Exist) ---
    try:
        # --- Document Loading and Splitting ---
        loader = PyPDFLoader(file_path)
        docs = loader.load_and_split(
            text_splitter=RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200
            )
        )

        valid_docs = [doc for doc in docs if doc.page_content.strip()]
        log_info(
            f"Loaded {len(docs)} chunks. {len(valid_docs)} valid chunks to embed.",
            tenant_id,
            conversation_id,
        )

        if valid_docs:
            # 3. CREATE FAISS INDEX (Initial creation)
            vector_store = FAISS.from_documents(
                documents=valid_docs, embedding=embeddings
            )
            log_info(
                f"PDF successfully indexed in FAISS (in-memory) for tenant.",
                tenant_id,
                conversation_id,
            )

            # 4. CRITICAL STEP: SAVE TO DISK
            os.makedirs(persist_directory, exist_ok=True)  # Ensure directory exists
            vector_store.save_local(
                folder_path=persist_directory,
                index_name="index",  # Saves as index.faiss and index.pkl
            )
            log_info(
                f"FAISS index successfully saved to disk at {persist_directory}",
                tenant_id,
                conversation_id,
            )

            return vector_store
        else:
            log_warning(
                "No valid chunks found to embed. Returning empty store.",
                tenant_id,
                conversation_id,
            )

    except Exception as e:
        log_exception_auto(
            f"FATAL ERROR during document loading or indexing: {e}",
            tenant_id,
            conversation_id,
        )
        # Return an empty index to allow the bot to function without RAG, but log the error
        vector_store = FAISS.from_texts([""], embeddings)
        return {
            "status": "error",
            "code": "VEC-5003",
            "message": f"Critical error during document processing and indexing: {type(e).__name__}",
            "http_status": 500,
            "vector_store_fallback": vector_store,  # Provide the empty store for graceful degradation
        }

    # Fallback return: If indexing or file loading failed for any reason
    log_warning(
        "No vector store created or loaded. Returning placeholder empty FAISS index.",
        tenant_id,
        conversation_id,
    )
    return FAISS.from_texts([""], embeddings)





# ==========================


def get_time_based_greeting():
    """Return an appropriate greeting based on the current time."""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "Good morning"
    if 12 <= current_hour < 17:
        return "Good afternoon"
    return "Good evening"



current_year = datetime.now().year
previous_year = current_year - 1

class State(MessagesState):
    """Manages the conversation state. Uses Pydantic models for structured data."""
    user_query: str
    employee_id: str
    leave_application: Optional[dict]
    payslip_application: Optional[dict]
    payslip_info: Optional[dict]
    update_info: Optional[dict]


 
from pydantic import BaseModel, Field
from typing import Optional

class PayslipQuery(BaseModel):
    start_date: str = Field(..., description="Start month and year in MMYYYY format (e.g., 012025)")
    end_date: str = Field(..., description="End month and year in MMYYYY format (e.g., 122025)")
    current_tool_id: Optional[str] = Field(None) 
    
class LeaveBalanceRequest(BaseModel):
    employee_id: str = Field(..., description="Internal employee ID")
    year: str = Field(..., description="Leave year to check")

class PayslipListQuery(BaseModel):
    employee_id: str
    year: int



class PayslipInfo(BaseModel):
    period: str
    gross_pay: float
    net_pay: float
    currency: str
    download_url: str = ""

class PayslipSummary(BaseModel):
    period: str
    gross_pay: float
    net_pay: float
    currency: str
    download_url: str = ""


class PayslipListResponse(BaseModel):
    employee_id: str
    year: int
    payslips: List[PayslipSummary]
    
    
class PayslipDownloadQuery(BaseModel):
    employee_id: str
    year: int
    month: int


class PayslipDownloadResponse(BaseModel):
    period: str
    pdf_url: str
    
class PayslipExplainQuery(BaseModel):
    employee_id: str
    year: int
    month: int


class PayslipExplainResponse(BaseModel):
    period: str
    explanation: str
    

class LeaveTypeRequest(BaseModel):
    current_tool_id: Optional[str] = Field(None, description="Injected ID")
class PrepareLeaveApplicationRequest(BaseModel):
    employeeID: str
    leaveTypeName: str
    leaveStartDate: str = Field(..., description="Start date in DDMMYYYY format")
    leaveEndDate: str = Field(..., description="End date in DDMMYYYY format")
    leaveReason: str
    workAssigneeRequest: str = Field(..., description="The reliever or person taking over tasks")
    addressWhileOnLeave: str = Field(..., description="Physical address during vacation")
    emailWhileOnLeave: str = Field(..., description="Personal/Alternative email for contact")
    contactNoWhileOnLeave: str = Field(..., description="Phone number while away")
    leaveYear: int = Field(..., description="The year the leave is being deducted from (Current or Previous)")
    current_tool_id: Optional[str] = Field(None, description="Injected tool call ID")
    
    
class PreparedLeaveApplication(BaseModel):
    address: str
    allowLeaveAllowanceOption: str
    consentNeeded: str
    contactNo: str
    email: str
    employeeID: str
    files: list
    hasAssignee: str
    isPaid: bool
    leaveAllowanceApplied: str
    leaveEndDate: str
    leaveReason: str
    leaveStartDate: str
    leaveType: dict
    leaveTypeID: str
    numOfDays: int
    resumptionDate: str
    supervisorID: str
    workAssigneeCompulsory: str
    workAssigneeRequest: str
    year: int
    
class ValidateLeaveBalanceRequest(BaseModel):
    employeeID: str
    leaveTypeID: str
    year: int
    numOfDays: int


class ValidateLeaveBalanceResponse(BaseModel):
    status: str
    message: str
    remainingDays: int = 0
  
  
class CalculateDaysRequest(BaseModel):
    startDate: str
    endDate: str
    holidays: List[str] = []  # optional list of YYYY-MM-DD strings


class CalculateDaysResponse(BaseModel):
    numOfDays: int  
    


class SubmitLeaveApplicationRequest(BaseModel):
    # Core Identification
    employeeID: str = Field(..., description="The unique ID of the employee applying for leave")
    leaveTypeID: str = Field(..., description="The unique ID for the specific leave type (e.g., Annual, Sick)")
    leaveTypeName: str = Field(..., description="The human-readable name of the leave type")
    
    # Dates and Duration
    leaveStartDate: str = Field(..., description="Start date in DDMMYYYY format")
    leaveEndDate: str = Field(..., description="End date in DDMMYYYY format")
    resumptionDate: str = Field(..., description="Date the employee returns to work")
    year: int = Field(..., description="The calendar year for this leave deduction (e.g., 2024 or 2025)")
    numOfDays: int = Field(..., description="The total number of days being requested")
    
    # Contact and Handover
    leaveReason: str = Field(..., description="Reason for the leave request")
    workAssigneeRequest: str = Field(..., description="The name or ID of the relief officer (reliever)")
    address: str = Field(..., description="Physical address while on leave")
    contactNo: str = Field(..., description="Phone number while on leave")
    email: str = Field(..., description="Alternative email while on leave")
    
    # Workflow & Meta
    supervisorID: str = Field(..., description="The ID of the person who must approve this request")
    files: Optional[List[str]] = Field(default=[], description="List of document URLs if applicable")
    
    # 🔥 INJECTED TRACKING ID
    # This ensures Pydantic doesn't strip the tool_call_id during the internal pass
    state: Optional[dict] = Field(None, description="Injected workflow state")
    current_tool_id: Optional[str] = Field(
        None, 
        description="Injected tool call ID for LangGraph response routing"
    )
# 1. Update your Schema
class SearchJobOpportunitiesRequest(BaseModel):
    department: Optional[str] = Field(None, description="Filter by hiring department name")
    jobType: Optional[str] = Field(None, description="Filter by job type (e.g., Full-time, Contract)")
    location: Optional[str] = Field(None, description="Filter by work location")
    jobRoleType: Optional[str] = Field(None, description="Filter by role type")
    limit: int = Field(5, description="Number of results to return")
    current_tool_id: Optional[str] = Field(None, description="Injected tool call ID")
    
    
class JobOpportunityResponse(BaseModel):
    """Structured response for a single job opportunity."""
    job_title: str
    department: str
    location: str
    salary_range: str
    experience_level: str
    description_snippet: str
    application_deadline: str

class LeaveStatusRequest(BaseModel):
    current_tool_id: Optional[str] = Field(None, description="Injected tool call ID")
class ExitPolicyRequest(BaseModel):
    current_tool_id: Optional[str] = Field(None, description="Injected tool call ID")

class TravelSearchRequest(BaseModel):
    destination: str = Field(..., description="The vacation destination city")
    departureDate: str = Field(..., description="YYYY-MM-DD")
    returnDate: str = Field(..., description="YYYY-MM-DD")
    current_tool_id: Optional[str] = Field(None)



from dateutil.parser import parse
from datetime import datetime

@tool("get_payslip_tool", args_schema=PayslipQuery)
def get_payslip_tool(config: RunnableConfig, **kwargs):
    """Normalizes dates to MMYYYY and fetches payslip archive."""
    
    tid = kwargs.get('current_tool_id')
    raw_start = kwargs.get('start_date')
    raw_end = kwargs.get('end_date')

    def normalize_to_mmyyyy(date_str: str) -> str:
        try:
            # Smart parsing: handles "Jan 2025", "01/25", "2025-01", etc.
            parsed_date = parse(date_str, fuzzy=True)
            return parsed_date.strftime("%m%Y")
        except:
            # Fallback for purely numeric strings like "012025"
            if len(date_str) == 6 and date_str.isdigit():
                return date_str
            raise ValueError(f"Could not understand date: {date_str}")

    try:
        clean_start = normalize_to_mmyyyy(raw_start)
        clean_end = normalize_to_mmyyyy(raw_end)
        
        employee_id = config["configurable"].get("employee_id")
        download_url = f"https://hr.system/payslip/{employee_id}/{clean_start}-{clean_end}.pdf"

        # The data structure you requested for PayslipInfo
        payslip_data = {
            "start_date": clean_start, # Now guaranteed MMYYYY
            "end_date": clean_end,     # Now guaranteed MMYYYY
            "download_url": download_url
        }

        return Command(
            update={
                "payslip_info": payslip_data, # Added as child to State
                "messages": [
                    ToolMessage(
                        content=f"Your payslip for {clean_start} to {clean_end} has been sent to your email.",
                        tool_call_id=tid
                    )
                ]
            }
        )
    except Exception as e:
        return f"I had trouble understanding the dates. Please use MMYYYY format. Error: {str(e)}"

@tool("fetch_available_leave_types_tool", args_schema=LeaveTypeRequest)
def fetch_available_leave_types_tool(config: RunnableConfig, **kwargs):
    """
    REQUIRED FIRST STEP for leave applications. 
    Call this immediately when a user wants to apply for leave to get valid leave names.
    """
    # 1. Get the ID we injected in tool_node for the response message
    tid = kwargs.get('current_tool_id')
    if not tid:
        # Fallback to prevent the validation error you saw
        tid = "unknown_id" 
    emp_id = config["configurable"].get("employee_id")
    
    HRLogger.info(f"Fetching available leave types for employee: {emp_id}", config)

    try:
        # Ensure the MongoDB connection is available before any attribute access
        if db_mongo is None:
            HRLogger.error("Database connection is not available while fetching leave types.", config)
            return ToolMessage(content="Error: Database connection lost.", tool_call_id=tid)

        # Step 1: Find the employee (use dict-style collection access to avoid attribute access on None)
        employee = db_mongo["employees"].find_one(
            {"_id": ObjectId(str(emp_id).strip())}, 
            {"companyID": 1, "leaveCategory": 1}
        )

        if not employee:
            return ToolMessage(content="Error: Employee record not found.", tool_call_id=tid)

        company_id = employee.get("companyID")
        leave_category_id = employee.get("leaveCategory")

        # Use dict-style access to avoid attribute access on None and be explicit about collection name
        leave_category_doc = db_mongo["leavecategories"].find_one(
            {"_id": leave_category_id, "companyID": company_id},
            {"leaveTypes": 1}
        )

        if leave_category_doc and "leaveTypes" in leave_category_doc:
            # Step 3: Extract names for the LLM
            leave_names = [lt.get("leaveName") for lt in leave_category_doc["leaveTypes"]]
            
            result_text = f"The following leave types are available: {', '.join(leave_names)}. Which one would you like to apply for?"
            
            # Return as a ToolMessage to keep the graph flow clean
            return ToolMessage(content=result_text, tool_call_id=tid)
        else:
            return ToolMessage(content="You are not currently entitled to any leave types.", tool_call_id=tid)

    except Exception as e:
        HRLogger.error(f"Failed to fetch leave types: {str(e)}", config)
        return ToolMessage(content=f"Error retrieving leave types: {str(e)}", tool_call_id=tid)


@tool("validate_leave_balance_tool", args_schema=ValidateLeaveBalanceRequest)
def validate_leave_balance_tool(
    employeeID: str, 
    leaveTypeID: str, 
    year: int, 
    numOfDays: int = None, 
    startDate: str = None, 
    endDate: str = None,
    config: RunnableConfig = None
):
    """
    Validates leave balance. If numOfDays is missing, it calculates it 
    automatically using startDate and endDate (skipping weekends).
    """
    HRLogger.info(f"Validating leave balance for Emp: {employeeID}", config)
    
    try:
        # 1. Automatic Calculation Trigger
        # If the LLM didn't provide numOfDays but provided dates, calculate them now
        if (numOfDays is None or numOfDays == 0) and (startDate and endDate):
            HRLogger.info("numOfDays missing; triggering internal weekend-skipping calculation", config)
            
            # Use our internal utility logic
            calc_result = calculate_num_of_days_tool.invoke(
                {"startDate": startDate, "endDate": endDate}, 
                config=config
            )
            numOfDays = calc_result.numOfDays
            HRLogger.info(f"Calculated {numOfDays} business days for validation", config)

        if not numOfDays:
            return ValidateLeaveBalanceResponse(
                status="error", 
                message="Could not determine number of days. Please provide dates."
            )

        # 2. Database Balance Check
        balance_doc = db_mongo.leavebalancehistories.find_one({
            "employeeID": ObjectId(employeeID),
            "leaveTypeID": ObjectId(leaveTypeID),
            "year": year
        })

        if not balance_doc:
            HRLogger.error(f"No balance record found for LeaveType: {leaveTypeID}", config)
            return ValidateLeaveBalanceResponse(status="error", message="No leave balance found for this year.")

        remaining = balance_doc.get("newBalance", 0)

        # 3. Final Response Logic
        if remaining < numOfDays:
            HRLogger.info(f"Validation Failed: Requested {numOfDays}, Available {remaining}", config)
            return ValidateLeaveBalanceResponse(
                status="error", 
                message=f"Insufficient balance. You requested {numOfDays} days but only have {remaining} days left.",
                remainingDays=remaining
            )

        HRLogger.info(f"Validation Success: {remaining} days available", config)
        return ValidateLeaveBalanceResponse(
            status="success", 
            message="You have sufficient leave balance.", 
            remainingDays=remaining
        )

    except Exception as e:
        HRLogger.error("Internal error in validation tool", config, exc=True)
        return ValidateLeaveBalanceResponse(status="error", message=f"Internal Error: {str(e)}")


@tool("submit_leave_application_tool", args_schema=SubmitLeaveApplicationRequest)
def submit_leave_application_tool(config: RunnableConfig, **kwargs):
    """
    Finalizes the leave application, calculates duration, fetches full leave type details,
    and inserts the record into approvalworkflowleaverequests.
    """
    state = kwargs.get("state", {})
    if state is None:
        state = kwargs
        
    HRLogger.info(f"Prepared Leave Application Data: {state.get('leave_application')}", config)
    HRLogger.info(f"Final State within Submit Tool: {state}", config)
    # 1. SETUP & LOGGING
    tool_call_id = kwargs.get('current_tool_id')
    emp_id_str = config["configurable"].get("employee_id")
    HRLogger.info(f"Initiating final submission for Employee: {emp_id_str}", config)
    

    if not tool_call_id:
        return "Error: Tool ID missing. Submission aborted."

    # 2. RETRIEVE PREPARED DATA FROM STATE
    # Using the refactored state key: leave_application
    HRLogger.info(f"Accessing State for submission: {state.get('leave_application')}", config)
    # leave_app = state.get("leave_application", {})
    
    # leave_app = (state or {}).get("leave_application") or {}
    leave_app = state
    HRLogger.info(f"Prepared Leave Application Data: {leave_app}", config)
    
    prep_details = leave_app.get("details", {})

    if not prep_details:
        return ToolMessage(
            content="Error: No prepared application found in state. Please prepare details first.", 
            tool_call_id=tool_call_id
        )

    try:
        # 3. DYNAMIC DATE & DAYS CALCULATION
        # Fixed: Using strptime with %d%m%Y to prevent the month range ValueError
        date_fmt = "%d%m%Y"
        start_dt = datetime.strptime(prep_details.get("leaveStartDate"), date_fmt)
        end_dt = datetime.strptime(prep_details.get("leaveEndDate"), date_fmt)
        
        # Calculate duration (Inclusive of start and end date)
        calculated_days = (end_dt - start_dt).days + 1
        
        if calculated_days <= 0:
            return ToolMessage(content="Error: End date must be after start date.", tool_call_id=tool_call_id)

        # 4. DATABASE LOOKUPS (Employee & Leave Category)
        if db_mongo is None:
            return ToolMessage(content="Error: Database connection unavailable.", tool_call_id=tool_call_id)

        emp_id = ObjectId(str(emp_id_str).strip())
        leave_name = prep_details.get("leaveTypeName")

        # Step 1: Get employee record for supervisor and category IDs
        employee = db_mongo["employees"].find_one(
            {"_id": emp_id}, 
            {"companyID": 1, "leaveCategory": 1, "supervisorID": 1}
        )

        if not employee:
            return ToolMessage(content="Error: Employee record not found.", tool_call_id=tool_call_id)

        # Step 2: Fetch the specific leaveType object from the category
        leave_category_doc = db_mongo["leavecategories"].find_one(
            {"_id": employee.get("leaveCategory"), "companyID": employee.get("companyID")},
            {"leaveTypes": 1}
        )

        selected_leave_obj = next(
            (lt for lt in leave_category_doc.get("leaveTypes", []) if lt.get("leaveName") == leave_name), 
            None
        )
        

        if not selected_leave_obj:
            return ToolMessage(content=f"Error: Detailed data for '{leave_name}' not found.", tool_call_id=tool_call_id)


        selected_leave_obj_safe = {
    "_id": str(selected_leave_obj.get("_id")),
    "leaveName": selected_leave_obj.get("leaveName"),
    "days": selected_leave_obj.get("days")
}
        HRLogger.info(f"Selected Leave Type Object: {selected_leave_obj_safe}", config)
        
        # 5. ASSEMBLE FINAL DB PAYLOAD
        final_payload = {
            "address": prep_details.get("addressWhileOnLeave", "street"),
            "contactNo": prep_details.get("contactNoWhileOnLeave", "0821536443"),
            "email": prep_details.get("emailWhileOnLeave", ""),
            "leaveReason": prep_details.get("leaveReason", ""),
            "leaveStartDate": start_dt.isoformat(), 
            "leaveEndDate": end_dt.isoformat(),
            "year": prep_details.get("leaveYear", 2025),
            "workAssigneeRequest": prep_details.get("workAssigneeRequest", "no-relief-officer"),
            "resumptionDate": prep_details.get("resumptionDate"),
            
            "employeeID": str(emp_id),
            # "leaveType": selected_leave_obj, # Original object (may contain non-serializable types)
            "leaveType": selected_leave_obj_safe,   # ✅ sanitized object

            "leaveTypeID": str(selected_leave_obj.get("_id")),
            "supervisorID": str(employee.get("supervisorID", "685d5294edba9f99bb36589d")),
            
            "numOfDays": calculated_days,
            
            # Mandatory Defaults
            "allowLeaveAllowanceOption": "false",
            "consentNeeded": "false",
            "workAssigneeCompulsory": "false",
            "leaveAllowanceApplied": "false",
            "files": [],
            "hasAssignee": "",
            "isPaid": True
        }

        # # 6. INSERT TO MONGO
        # result = db_mongo["approvalworkflowleaverequests"].insert_one(final_payload)
        application_id = str(uuid.uuid4())
        final_payload["_id"] = application_id
        HRLogger.info(f"Submission Successful. Record ID: {application_id}", config)

        # 7. RETURN COMMAND
        return Command(
            update={
                "leave_application": {
                    "status": "success",
                    "application_id": str(application_id),
                    "details": final_payload
                },
                "messages": [
                    ToolMessage(
                        content=f"Successfully submitted! Your request for {calculated_days} day(s) has been sent for approval.",
                        tool_call_id=tool_call_id
                    )
                ]
            },
            goto="assistant"
        )

    except Exception as e:
        HRLogger.error(f"Critical failure in submission: {str(e)}", config, exc=True)
        return Command(
            update={
                "leave_application": {"status": "error", "message": str(e)},
                "messages": [
                    ToolMessage(content=f"Submission failed: {str(e)}", tool_call_id=tool_call_id)
                ]
            },
            goto="assistant"
        )



@tool("prepare_leave_application_tool", args_schema=PrepareLeaveApplicationRequest)
def prepare_leave_application_tool(config: RunnableConfig, **kwargs):
    """Validates full leave details including contact info and year selection."""
    
    tid = kwargs.get('current_tool_id')
    
    # Extract fields from Assistant's tool call
    start_date = kwargs.get("leaveStartDate")
    end_date = kwargs.get("leaveEndDate")
    leave_year = kwargs.get("leaveYear")
    reliever = kwargs.get("workAssigneeRequest")
    address = kwargs.get("addressWhileOnLeave")
    contact = kwargs.get("contactNoWhileOnLeave")
    email = kwargs.get("emailWhileOnLeave")

    HRLogger.info(f"Preparing application for Year {leave_year}. Reliever: {reliever}", config)

    # 1. Date Format Validation (DDMMYYYY)
    date_fmt = "%d%m%Y"
    try:
        if not start_date or not end_date:
            raise ValueError("Start and End dates are mandatory.")
            
        start_dt_obj = datetime.strptime(start_date, date_fmt)
        end_dt_obj = datetime.strptime(end_date, date_fmt)
        
        # 2. Dynamic Resumption Calculation (End Date + 1)
        resumption_dt_obj = end_dt_obj + timedelta(days=1)
        resumption_str = resumption_dt_obj.strftime("%d-%m-%Y")
        
    except ValueError as e:
        return ToolMessage(
            content=f"Error: {str(e)}. Please ensure dates are in DDMMYYYY format (e.g., 22122025).",
            tool_call_id=tid
        )

    HRLogger.info(f"Calculated resumption date as {resumption_str}", config)

    # 3. Update State
    return Command(
        update={
            "leave_application": {
                "status": "prepared",
                "details": {
                    **kwargs, 
                    "resumptionDate": resumption_str
                }
            },
            "messages": [
                ToolMessage(
                    content=(
                        f"I've prepared your application:\n"
                        f"* Resumption: {resumption_str}\n"
                        f"* Reliever: {reliever}\n"
                        f"* Address: {address}\n"
                        "Please confirm to **Submit**."
                    ),
                    tool_call_id=tid
                )
            ]
        }
    )
@tool("calculate_num_of_days_tool", args_schema=CalculateDaysRequest)
def calculate_num_of_days_tool(startDate: str, endDate: str, holidays: List[str] = [], config: RunnableConfig = None):
    """
    Calculates the actual number of leave days by skipping weekends and 
    a provided list of public holidays.
    """
    HRLogger.info(f"Calculating business days between {startDate} and {endDate}", config)
    
    try:
        # 1. Parse string dates to date objects

        # To this:
        start = datetime.strptime(startDate, "%d%m%Y").date()
        end = datetime.strptime(endDate, "%d%m%Y").date()
        
        # 2. Convert holiday strings to a set of date objects for O(1) lookup
        holiday_set = {datetime.fromisoformat(h.replace("Z", "")).date() for h in holidays}
        
        total_days = 0
        current_day = start
        
        # 3. Iterate through the range
        while current_day <= end:
            # Check if it's a weekday (Monday=0, Friday=4) AND not a holiday
            if current_day.weekday() < 5 and current_day not in holiday_set:
                total_days += 1
            else:
                log_reason = "Weekend" if current_day.weekday() >= 5 else "Public Holiday"
                HRLogger.info(f"Skipping {current_day}: {log_reason}", config)
                
            current_day += timedelta(days=1)

        HRLogger.info(f"Final calculation: {total_days} business days", config)

        # 4. Return structured response
        return CalculateDaysResponse(numOfDays=total_days)

    except Exception as e:
        HRLogger.error("Error calculating leave days", config, exc=True)
        # Fallback to a standard diff if parsing fails, or return 0
        return CalculateDaysResponse(numOfDays=0)


# 2. Update the Tool Function
@tool("search_job_opportunities_tool", args_schema=SearchJobOpportunitiesRequest)
def search_job_opportunities_tool(config: RunnableConfig, **kwargs):
    """Searches for internal job opportunities based on department, type, location, or role."""
    
    tid = kwargs.get('current_tool_id')
    tenant_id = config["configurable"].get("tenant_id")
    
    # 1. Build the Dynamic MongoDB Query
    # Base filters as per your requirements
    query = {
        "companyID": ObjectId(tenant_id), # Dynamically use the tenant/company ID
        "vacancyType": "internal",
        "status": "open"
    }

    # Add optional filters from user input if they exist
    if kwargs.get("department"):
        query["hiringDepartment.name"] = {"$regex": kwargs.get("department"), "$options": "i"}
    if kwargs.get("jobType"):
        query["jobType"] = kwargs.get("jobType")
    if kwargs.get("location"):
        query["location"] = {"$regex": kwargs.get("location"), "$options": "i"}
    if kwargs.get("jobRoleType"):
        query["jobRoleType"] = kwargs.get("jobRoleType")

    HRLogger.info(f"Executing Job Search with query: {query}", config)

    try:
        projection = {
            "jobType": 1,
            "jobRoleType": 1,
            "location": 1,
            "educationalLevel": 1,
            "jobDescription": 1,
            "hiringDepartment.name": 1,
            "jobRole.name": 1
        }
        
      
        if db_mongo is None:
                return "Database connection lost."

         
        job_collection = db_mongo["jobopportunities"]
        # job_collection is your defined MongoDB collection
        cursor = job_collection.find(query, projection).limit(kwargs.get("limit", 5))
        
        jobs_found = []
        for doc in cursor:
            jobs_found.append({
                "Role": doc.get("jobRole", {}).get("name"),
                "Department": doc.get("hiringDepartment", {}).get("name"),
                "Type": doc.get("jobType"),
                "Location": doc.get("location"),
                "Description": f"{doc.get('jobDescription', '')[:200]}... (contact HR for details)"
                
                
            })

        if not jobs_found:
            result_text = "No open internal positions match those criteria at the moment."
        else:
            result_text = f"Found {len(jobs_found)} opportunities: {str(jobs_found)}"

        return ToolMessage(
            content=result_text,
            tool_call_id=tid
        )

    except Exception as e:
        HRLogger.error(f"Job search failed: {str(e)}", config)
        return f"Error searching jobs: {str(e)}"
    
@tool("fetch_leave_status_tool", args_schema=LeaveStatusRequest)
def fetch_leave_status_tool(config: RunnableConfig, **kwargs):
    """Checks the current status of the employee's leave requests and identifies the pending approver."""
    
    tid = kwargs.get('current_tool_id')
    # Get IDs from the config (clean IDs we handled in tool_node)
    employee_id = config["configurable"].get("employee_id")
    tenant_id = config["configurable"].get("tenant_id")

    HRLogger.info(f"Fetching leave status for Employee: {employee_id}", config)

    try:
        # 1. Query the collection
        query = {
            "employeeID": ObjectId(employee_id),
            "companyID": ObjectId(tenant_id)
        }
        if db_mongo is None:
                return "Database connection lost."

         
        leave_requests_collection = db_mongo["approvalworkflowleaverequests"]
        # job_collection is your defined MongoDB collection
        
        # We sort by creation date (descending) to show the most recent request first
        cursor = leave_requests_collection.find(query).sort("createdAt", -1).limit(3)
        
        status_reports = []
        for doc in cursor:
            leave_type = doc.get("leaveTypeName", "Leave")
            start_date = doc.get("startDate", "N/A")
            overall_status = doc.get("status", "Unknown")
            
            # 2. Logic to find the first pending approver
            current_pending_approver = "No pending approvers"
            if overall_status.lower() == "pending":
                for wf in doc.get("workflowProcessStatus", []):
                    if wf.get("status") == "pending" and wf.get("approvers"):
                        current_pending_approver = wf["approvers"][0].get("name")
                        break
            
            status_reports.append(
                f"**{leave_type}** ({start_date}): Status is **{overall_status}**. "
                f"Currently with: {current_pending_approver}."
            )

        if not status_reports:
            result_text = "I couldn't find any recent leave requests for you."
        else:
            result_text = "Here is the status of your recent leave requests:\n" + "\n".join(status_reports)

        return ToolMessage(
            content=result_text,
            tool_call_id=tid
        )

    except Exception as e:
        HRLogger.error(f"Leave status fetch failed: {str(e)}", config)
        return f"Error retrieving leave status: {str(e)}" 


@tool("fetch_exit_policy_tool", args_schema=ExitPolicyRequest)
def fetch_exit_policy_tool(config: RunnableConfig, **kwargs):
    """Retrieves the company's exit and resignation policies, including notice periods and leave monetization."""
    
    tid = kwargs.get('current_tool_id')
    tenant_id = config["configurable"].get("tenant_id")

    HRLogger.info(f"Retrieves exit policy for Tenant: {tenant_id}", config)

    try:
        # Filter for the specific company and general employee policies
        query = {
            "companyID": ObjectId(tenant_id),
            "appliesTo": "all-employees"
        }
        if db_mongo is None:
                return "Database connection lost."

         
        policies_collection = db_mongo["approvalworkflowleaverequests"]
        policies = []
        cursor = policies_collection.find(query)

        for doc in cursor:
            notice = doc.get("noticePeriod", {})
            notice_str = "No notice required"
            if notice.get("enforce"):
                notice_str = f"{notice.get('length')} {notice.get('time')}(s) required"

            policy_summary = (
                f"### Policy: {doc.get('name')}\n"
                f"* **Notice Period:** {notice_str}\n"
                f"* **Contract Enforcement:** {'Yes' if doc.get('checkAgreements') else 'No'}\n"
                f"* **Use Unused Leave during exit:** {'Yes' if doc.get('includeUnusedLeave') else 'No'}\n"
                f"* **Monetize Unused Leave:** {'Yes' if doc.get('monetizeUnusedLeave') else 'No'}\n"
                f"* **Exit Interview Required:** {'Yes' if doc.get('checkExitInterview') else 'No'}"
            )
            policies.append(policy_summary)

        if not policies:
            result_text = "I couldn't find a specific exit policy for your department. Please contact HR for the employee handbook."
        else:
            result_text = "Here are the details of the company exit policy:\n\n" + "\n\n".join(policies)

        return ToolMessage(
            content=result_text,
            tool_call_id=tid
        )

    except Exception as e:
        HRLogger.error(f"Exit policy fetch failed: {str(e)}", config)
        return f"Error retrieving exit policy: {str(e)}"    
    

@tool("search_travel_deals_tool", args_schema=TravelSearchRequest)
def search_travel_deals_tool(config: RunnableConfig, **kwargs):
    """Uses Tavily to search for the best flight and hotel deals for a vacation."""
    
    tid = kwargs.get('current_tool_id')
    dest = kwargs.get('destination')
    start = kwargs.get('departureDate')
    end = kwargs.get('returnDate')

    # Construct a high-quality search query for Tavily
    query = f"cheapest flights and top rated hotels in {dest} from {start} to {end} for vacation"
    
    HRLogger.info(f"Tavily searching travel deals: {query}", config)

    try:
        # Execute Tavily Search
        search_results = search_tool.invoke({"query": query})
        
        # Format the output for the AI Assistant
        formatted_results = []
        for res in search_results:
            formatted_results.append({
                "source": res.get("url"),
                "content": res.get("content")[:500] # Snippet for context
            })

        return ToolMessage(
            content=f"Found these travel options in {dest}:\n{str(formatted_results)}",
            tool_call_id=tid
        )
    except Exception as e:
        return f"Travel search failed: {str(e)}"   


class ProfileUpdateInput(BaseModel):
    last_name: Optional[str] = Field(None, description="The new last name of the employee")
    pfa: Optional[str] = Field(None, description="The Pension Fund Administrator name")
    phone: Optional[str] = Field(None, description="The new phone number")
    personal_email: Optional[str] = Field(None, description="The personal email address")
    address: Optional[str] = Field(None, description="The residential address")
    city: Optional[str] = Field(None, description="The city of residence")
    state: Optional[str] = Field(None, description="The state of residence")
    country: Optional[str] = Field(None, description="The country of residence")
    account_number: Optional[str] = Field(None, description="The 10-digit bank account number")
    bank_name: Optional[str] = Field(None, description="The name of the bank")



@tool("update_employee_profile_tool", args_schema=ProfileUpdateInput)
def update_employee_profile_tool(
    config: RunnableConfig, 
    **kwargs
):
    """
    Updates the employee's personal or banking details. 
    Use this when a user wants to change their phone, email, address, or bank info.
    """
    tid = kwargs.get('current_tool_id')
    try:
        
        # 1. Extract secure context from config
        configurable = config.get("configurable", {})
        emp_id = configurable.get("employee_id")
        tenant_id = configurable.get("tenant_id")

        if not emp_id or not tenant_id:
            return "Error: Session context missing (tenant_id/employee_id)."

        # 2. Filter out None values to only update what was provided
        # We also remove the injected tool_call_id if it's in kwargs
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        
        if not update_data:
            return "No update information was provided. Please specify what you'd like to change."

        # 3. Return Command to update state and messages
        return Command(
            update={
                # Storing the update data in state for later approval/processing
                "update_info": update_data, 
                "messages": [
                    ToolMessage(
                        content=f"Successfully submitted your update request for: {list(update_data.keys())}. This has been sent to HR for approval.",
                        tool_call_id=tid
                    )
                ]
            }
        )

    except Exception as e:
        # Note: Added for consistency with your payroll formatting request
        return f"I had trouble processing the update request. Error: {str(e)}"


current_year = datetime.now().year
previous_year = current_year - 1
current_date_str = datetime.now().strftime("%A, %b %d, %Y") 
   
def assistant_node(state: State, config: RunnableConfig):
    """
    Enhanced Assistant node with Multi-Skill routing (Leave, Payslips, Policy).
    """
    HRLogger.info("Assistant node triggered", config)
    
    leave_app = state.get("leave_application")
    
    # 1. DEFINE MULTI-SKILL SYSTEM PROMPT
    # This acts as the "Brain" telling the AI which tool to use and when.
    # 1. BASE PROTOCOLS
        
    
    

    system_content = (
    "You are an expert HR Self-Service Assistant. Follow these protocols:\n\n"
    
    "PROTOCOL 1: LEAVE REQUESTS\n"
    "- If the user wants to apply for leave, you MUST first call 'fetch_available_leave_types_tool'.\n"
    "- If the user specifies a leave type NOT in the list provided by 'fetch_available_leave_types_tool':\n"
    "  1. Politely inform them that '[InvalidType]' is not available for their category.\n"
    "  2. Re-list the valid options from the tool's previous output.\n"
    "  3. Do NOT call 'prepare_leave_application_tool' until a valid type is selected.\n"
    f"LEAVE YEAR LOGIC: Ask the user: \"Is this leave for the current year or your previous year's carry-over?\"\n"
    f"- If the user says Current, use {current_year}.\n"
    f"- If the user says Previous, use {previous_year}.\n"
    "Pass this integer to the 'leaveYear' field in the tool.\n\n"
    
    "SUBMISSION & POST-LEAVE ENGAGEMENT:\n"
    "- Once the user confirms the resumption date and details (State: prepared), call 'submit_leave_application_tool'.\n"
    "- **Proactive Engagement:** After the 'submit_leave_application_tool' confirms success, if the leave type was 'Vacation', you MUST ask the user if they would like help planning their travel or finding flights/hotels for their time off.\n\n"

    "PROTOCOL 2: PAYSLIPS (SMART DATES)\n"
    "- When a user asks for a payslip, identify the start and end month/year.\n"
    "- Once the tool returns, strictly inform the user: 'Your payslip has been sent to your email.'\n\n"

    "PROTOCOL 3: HR POLICIES\n"
    "- For policy questions, use 'pdf_retrieval_tool' to search HR handbooks.\n\n"

    "PROTOCOL 4: JOB OPPORTUNITIES\n"
    "- Use 'search_job_opportunities_tool' for internal vacancies.\n"
    "- Job descriptions are truncated. Always tell the user to '(contact HR for details)' for more info.\n\n"
    
    "PROTOCOL 5: PROFILE UPDATES (SELF-SERVICE)\n"
    "- Use 'update_employee_profile_tool' when a user wants to update personal or banking details.\n"
    "- If the user says 'Change my phone number', call the tool with the 'phone' argument.\n"
    "- If a user provides an account number but forgets the bank name, ask: 'Which bank is this account number for?' before calling the tool.\n"
    "- After the tool returns, inform the user that their request has been logged and sent to HR for approval.\n\n"
    f"CONTEXT: Employee ID: {state.get('employee_id')}. Current Date: {current_date_str}."
)
    # 2. DYNAMIC STATE INJECTION
    leave_app = state.get("leave_application") # Using leave_application per your instruction
    if leave_app:
        status = leave_app.get("status")
        if status == "success":
            app_id = leave_app.get("application_id", "N/A")
            system_content += f"\n\nSUCCESS: Leave application {app_id} submitted! Acknowledge this."
        elif status == "prepared":
            details = leave_app.get("details", {})
            resumption = details.get("resumptionDate", "TBD")
            system_content += f"\n\nACTION: Confirm resumption date: {resumption}. Ask user to 'Submit' or 'Cancel'."
        elif status == "error":
            error_msg = leave_app.get("message", "Unknown error")
            system_content += f"\n\nERROR: The process failed: {error_msg}. Inform the user."
        
    system_content += (
    "\n\nPROTOCOL 5: LEAVE STATUS\n"
    "- If the user asks 'Where is my leave?', 'Has my leave been approved?', or 'Who is supposed to approve my leave?', "
    "call 'fetch_leave_status_tool'.\n"
    "- Provide the specific name of the pending approver if available."
)
    system_content += (
    "\n\nPROTOCOL 7: VACATION CONCIERGE (TAVILY POWERED)\n"
    "- When a user is ready for their vacation, use 'search_travel_deals_tool'.\n"
    "- Tavily will provide real-time web results. Your job is to summarize the best flight prices and hotel names found in the search results.\n"
    "- Always provide the source URL so the user can go directly to the booking page."
)
   
    # 3. LLM INVOCATION
    messages = [SystemMessage(content=system_content)] + state["messages"]
    
    try:
        response = llm.invoke(messages, config=config)
        
        # 4. ROBUST RESPONSE HANDLING
        if response is None:
            return {"messages": [AIMessage(content="I'm having trouble connecting. Please try again.")]}

        # Extract text using your robust logic
        raw_text = ""
        if isinstance(response.content, list):
            for item in response.content:
                if isinstance(item, dict) and "text" in item:
                    raw_text = item["text"]
                    break
        elif isinstance(response.content, str):
            raw_text = response.content

        # 5. TOOL ROUTING
        # If the LLM wants to call a tool, we MUST return the raw response object
        if hasattr(response, 'tool_calls') and response.tool_calls:
            return {"messages": [response]}

        # 6. CLEANUP & RETURN
        if not raw_text:
            raw_text = "I'm ready to help with your leave, payslips, or HR questions. What can I do for you?"
        
        response.content = raw_text

        # OPTIONAL: If the status was 'success', we might want to reset the state 
        # so it doesn't repeat the success message on the next turn.
        updates = {"messages": [response]}
        if leave_app and leave_app.get("status") == "success":
            updates["leave_application"] = None # Reset state after acknowledgment

        return updates

    except Exception as e:
        HRLogger.error("Assistant invocation failed", config, exc=True)
        return {"messages": [AIMessage(content="I encountered an error. Please try again.")]}

    
tools = [
    get_payslip_tool,
    fetch_available_leave_types_tool,
    validate_leave_balance_tool,
    prepare_leave_application_tool,
    calculate_num_of_days_tool,
    submit_leave_application_tool,
    search_job_opportunities_tool,
    fetch_leave_status_tool,
    fetch_exit_policy_tool,
    search_travel_deals_tool,
    update_employee_profile_tool
]
llm = llm.bind_tools(tools)
tools_by_name = {tool.name: tool for tool in tools}
# Ensure RunnableConfig is imported for the node signature


# 3. Define nodes
def get_clean_id(config: RunnableConfig, key: str):
    val = config["configurable"].get(key)
    if val and isinstance(val, str):
        return val.strip()
    return val
def tool_node(state: State, config: RunnableConfig) -> dict:
    """
    Executes tool calls and injects state into tool arguments.
    """
    # 1. Context extraction
    tenant_id = config["configurable"].get("tenant_id", "unknown")
    
    HRLogger.info("Tool node activated", config)

    # 2. Clean employee_id once
    raw_emp_id = config["configurable"].get("employee_id")
    if raw_emp_id:
        config["configurable"]["employee_id"] = str(raw_emp_id).strip()

    final_messages = [] # Standardize on one list name
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls"):
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool = tools_by_name.get(tool_name)
            
            if not tool:
                HRLogger.error(f"Requested tool '{tool_name}' not found", config)
                final_messages.append(ToolMessage(
                    content=f"Error: The tool '{tool_name}' is not available.", 
                    tool_call_id=tool_call["id"]
                ))
                continue
            
            # 3. Inject 'state' into tool arguments
            # We use tool_input for the tool itself
            # tool_input = {**tool_call["args"], "state": state}
            tool_input = {**tool_call["args"], "current_tool_id": tool_call["id"]}
            
            
            # --- START OF AMENDMENT ---
            if tool_name == "submit_leave_application_tool":
                # Retrieve the state slice
                HRLogger.info(f"Raw State oh: {state} for leave processing", config)
                leave_app_state = state.get("leave_application", {})
                HRLogger.info(f"leave_app_state to: {leave_app_state} for leave processing", config)
                
                # Inject it into the tool_input so the tool can access it
                # We pass it as 'state' because your function signature expects 'state: dict'
                tool_input["state"] = leave_app_state 
                
                HRLogger.info(f"Injected full state into {tool_name} for leave processing", config)
                HRLogger.info(f"Combined Tool Input: {tool_input}", config)
            # --- END OF AMENDMENT ---
            
            
            HRLogger.info(f"Tool Ttool call ID : { tool_call["id"]}", config)
           
            try:
                # 4. Invoke the tool
                observation = tool.invoke(tool_input, config=config)
                HRLogger.info(f"Context injected into : {observation}", config)
                
                # 5. Handle the return (Command vs Message)
                if isinstance(observation, Command):
                    # If the tool returns a Command, it handles its own ToolMessage
                    return observation 
                    
                # 6. Append the result as a ToolMessage
                final_messages.append(ToolMessage(
                    content=str(observation), 
                    tool_call_id=tool_call["id"]
                ))
                
            except Exception as e:
                HRLogger.error(f"Tool {tool_name} failed: {str(e)}", config, exc=True)
                final_messages.append(ToolMessage(
                    content=f"Error: The tool {tool_name} failed to process.", 
                    tool_call_id=tool_call["id"]
                ))

    HRLogger.info(f"Executed {len(final_messages)} tool(s)", config)
    HRLogger.info(f"Executed Langa:  {(final_messages)} tool(s)", config)
    
    # 7. Return the messages to update the state
    return {"messages": final_messages}

def should_call_tool(state: State):
    last_message = state["messages"][-1]
    # If the assistant produced tool calls, we route to the tool node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END



def build_graph(tenant_id, conversation_id):
    """Builds and compiles the LangGraph workflow for a given tenant and conversation."""
    # Create a temporary context for startup logging
    startup_config = {
        "configurable": {
            "tenant_id": tenant_id,
            "thread_id": conversation_id,
            "employee_id": "SYSTEM"
        }
    }
    
    
    
    try:
        # 'memorys' is the SqliteSaver we initialized in the DB config
        if memorys is not None:
            memory = memorys
            HRLogger.info("SQLite checkpointing connected successfully.", startup_config)
        else:
            raise ValueError("SqliteSaver not initialized")
            
    except Exception as e:
        HRLogger.error(
            f"Error connecting to SQLite for checkpointing: {e}. Falling back to InMemorySaver.", 
            startup_config, 
            exc=True
        )
        memory = InMemorySaver()
        
    workflow = StateGraph(State)

    workflow.add_node("assistant", assistant_node)
    workflow.add_node("tools", tool_node)

    workflow.set_entry_point("assistant")

    workflow.add_conditional_edges(
        "assistant",
        should_call_tool,
        {
            "tools": "tools",
            END: END,
        },
    )

    workflow.add_edge("tools", "assistant")
    HRLogger.info("LangGraph workflow compiled successfully", startup_config)
    # Compile with the chosen checkpointer
    return workflow.compile(checkpointer=memory)


def process_message_self(
    message_content: str, 
    conversation_id: str, 
    tenant_id: str, 
    employee_id: str
):
    config = {
        "configurable": {
            "thread_id": conversation_id,
            "tenant_id": tenant_id,
            "employee_id": employee_id
        }
    }
    HRLogger.info(f"Processing message for Tenant: {tenant_id}, Employee: {employee_id}, Conversation: {conversation_id}", config)
    initial_state = {
        "messages": [HumanMessage(content=message_content)],
        "user_query": message_content,
        "employee_id": employee_id,
    
        # "leave_application": None,  # Ensure this key exists in start
        "payslip_info": None,  # Ensure this key exists in start
        "update_info": None  # Ensure this key exists in start
    }

    try:
        # 1. Convert to State object and Invoke
        initial_state = State(**initial_state)
        graph = build_graph(tenant_id, conversation_id)
        
        HRLogger.info("Invoking LangGraph", config)
        result = graph.invoke(initial_state, config)
        # 2. Extract messages and setup default reply
        messages = result.get("messages", [])
        HRLogger.info(f"Messages returned from graph: {messages}", config)
        reply = "I'm sorry, I couldn't process that."
        
        # ---------------------------------------------------------
        # 3. SEARCH FOR LAST AI MESSAGE (Working Loop)
        # ---------------------------------------------------------
        if messages:
            for msg in reversed(messages):
                # Check if it's an AI message
                if hasattr(msg, 'type') and msg.type == 'ai':
                    # Robust extraction logic
                    if isinstance(msg.content, list):
                        for part in msg.content:
                            if isinstance(part, dict) and "text" in part:
                                reply = part["text"]
                                break
                    else:
                        reply = msg.content
                    
                    # STOP once the latest AI message is processed
                    break 
        
        # 4. Extract specialized leave state
        # Extract the values safely
        reply = result["messages"][-1].content
        leave_app_state = result.get("leave_application", {})
        payslip_info_state = result.get("payslip_info", {})
        update_info_state = result.get("update_info", {})
        
        HRLogger.info(f"Final Reply Output: {reply}...", config)
        return reply, leave_app_state, payslip_info_state, update_info_state

    except Exception as e:
        HRLogger.error(f"Error in process_message_self: {str(e)}", config, exc=True)
        return "I encountered an error while processing your request.", None
    
    
