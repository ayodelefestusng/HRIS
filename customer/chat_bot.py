# ==================================
# 📦 STANDARD LIBRARY IMPORTS
# ==================================
import base64
import io
import json
import logging
import operator
import os
import re
import sqlite3
import sys
import time
import uuid
from collections import UserDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from importlib import metadata
from io import BytesIO
from logging.handlers import RotatingFileHandler
from math import log
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union, Annotated
from urllib.parse import urlparse
from xml.dom.minidom import Document
import pandas as pd
# ==================================
# 📦 THIRD-PARTY LIBRARIES (GENERAL)
# ==================================
# from bson import ObjectIdpip 
from dotenv import load_dotenv
# from IPython.display import Image as IPImage, display
from PIL import Image
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import Boolean, create_engine
from sqlalchemy.orm import Session
from pprint import pprint
import pdfplumber
# from myproject.hr.hr_bot import log_info
# from pdf2image import convert_from_path
# import pytesseract
# from bs4 import BeautifulSoup as soup
# from pymongo import MongoClient

# ==================================
# 🌐 DJANGO & PROJECT-SPECIFIC
# ==================================
from django.conf import settings
from rest_framework.exceptions import NotFound
# from database import SessionLocal, Tenant, Conversation, Message, Prompt, get_db, LLM
from org.views import log_with_context
from .models import Tenant_AI, Conversation, Message, Prompt, LLM 
# from .models import Conversation, Tenant # (Local relative imports)

# ==================================
# 🤖 LANGCHAIN CORE & MESSAGES
# ==================================
from langchain_core.documents import Document
from langchain_core.messages import (
    AIMessage, HumanMessage, SystemMessage, ToolMessage, AnyMessage, RemoveMessage
)
from langchain_core.tools import Tool
from langchain_core.vectorstores import VectorStore
from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent
# ==================================
# 🛠️ LANGCHAIN TOOLS & UTILITIES
# ==================================
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, UnstructuredFileLoader, CSVLoader, 
    RecursiveUrlLoader, WebBaseLoader, unstructured,
)
from langchain_community.vectorstores import FAISS, Chroma
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_tavily import TavilySearch
from langchain.tools import tool

        # ==================================
        # 📦 LangChain Document Loaders & Utilities
        # ==================================
from langchain_community.document_loaders import (
            PyPDFLoader,
            TextLoader,
            UnstructuredFileLoader,
            CSVLoader,
            RecursiveUrlLoader,
            WebBaseLoader,
        )
import os
from ollama import Client
# ==================================
# 🚀 LLM PROVIDERS
# ==================================
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# from langchain_deepseek import ChatDeepSeek
# from langchain_groq import ChatGroq
from langchain.chat_models import init_chat_model

# ==================================
# 📊 LANGGRAPH CORE & PERSISTENCE
# ==================================
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.prebuilt import ToolNode, create_react_agent, tools_condition
from langgraph.types import Command, Send
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore  
from langgraph.store.memory import InMemoryStore
from langgraph.store.sqlite import SqliteStore
# from langchain_community.storage import AsyncSqliteSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain.chat_models import init_chat_model
from dateutil.parser import parse
from datetime import datetime
# 3. Embeddings Model Initialization
from langchain_google_genai import GoogleGenerativeAIEmbeddings


 
from org.models import Tenant
from django.contrib.auth import get_user_model

from .ollama_service import OllamaService
from .models import LLM, Tenant_AI    
from .base import State, Answer, Summary
from .tools import tools, TENANT_SQL_AGENTS, TENANT_DBS, init_sql_agent
User = get_user_model()


from langchain.tools import tool
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os


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
GEMINI_INIT= os.getenv("GEMINI_INIT", "google_genai:gemini-flash-latest")

embeddings = None  # Lazy initialized in initialize_vector_store()

# ==================================
# ⚙️ CONFIGURATION & LOGGING SETUP
# ==================================
load_dotenv()

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "chatbot.log")
logging.captureWarnings(True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding="utf-8"),
    ],
    force=True,
)




logger = logging.getLogger("HR_AGENT")
logger.propagate = True # Flow to root logger for persistence

# Suppress noisy libraries
logging.getLogger("watchfiles").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.INFO)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("langsmith").setLevel(logging.INFO)

import inspect



def log_info(msg, tenant_id, conversation_id):
    logger.info(f"[Tenant: {tenant_id} | Conversation: {conversation_id}] {msg}")

def log_error(msg, tenant_id, conversation_id):
    logger.error(f"[Tenant: {tenant_id} | Conversation: {conversation_id}] {msg}")

def log_debug(msg, tenant_id, conversation_id):
    logger.debug(f"[Tenant: {tenant_id} | Conversation: {conversation_id}] {msg}")

def log_warning(msg, tenant_id, conversation_id):
    logger.warning(f"[Tenant: {tenant_id} | Conversation: {conversation_id}] {msg}")

def log_exception_auto(msg, tenant_id, conversation_id):
    logger.error(
        f"[Tenant: {tenant_id} | Conversation: {conversation_id}] {msg}",
        exc_info=True,
    )



# 2. Model/Service Name Variables
OLLAMA_BASE_URL = "https://ai.notchhr.io/api/chat/local"
OLLAMA_USERNAME = "ai-user"
OLLAMA_PASSWORD = "x2GS7jEF@#2T"
OLLAMA_MODEL = "gpt-oss-safeguard:20b"

embeddings = None

# llm = OllamaService(
#     base_url=OLLAMA_BASE_URL,
#     username=OLLAMA_USERNAME,
#     password=OLLAMA_PASSWORD,
#     model=OLLAMA_MODEL
# )

# llm_fallback = init_chat_model(GEMINI_INIT)
# model = llm_fallback  # Consistent naming for the primary LLM


current_year = datetime.now().year
previous_year = current_year - 1
current_date_str = datetime.now().strftime("%A, %b %d, %Y") 
   # Placeholders for global startup logs
GLOBAL_SCOPE = "GLOBAL"
NO_CONVO = "N/A"


# ==================================
# 📝 GLOBAL PROMPT DEFINITIONS
# ==================================

GLOBAL_ROUTING_PROMPT = """You are a helpful AI assistant for ATB Bank. Your task is to analyze the user's request and decide if a tool is needed to answer it.

You have access to the following tools:
- `pdf_retrieval_tool`: For questions about bank policies, products, or internal knowledge.
- `tavily_search_tool`: For general knowledge or up-to-date information.
- `sql_query_tool`: For questions about specific data, like user counts or transaction volumes.
- **`generate_visualization_tool`**: **Use this tool ONLY when the user explicitly asks to 'plot', 'chart', 'graph', or 'visualize' data. This is your primary tool for creating visual representations from database data.**

Based on the conversation history, either call the most appropriate tool to gather information or, if you have enough information already, prepare to answer the user directly.
"""

GLOBAL_FINAL_ANSWER_PROMPT = """You are Damilola, the AI-powered virtual assistant for ATB. Your role is to deliver professional customer service and insightful data analysis, depending on the user's needs.

You operate in three modes:
1. **Customer Support**: Respond with empathy, clarity, and professionalism. Your goal is to resolve issues, answer questions, and guide users to helpful resources — without technical jargon or internal system references.
2. **Data Analyst**: Interpret data, explain trends, and offer actionable insights. When visualizations are included, describe what the chart shows and what it means for the user.
3. **HR Assistant**: Respond with empathy, clarity, and professionalism regarding leave, payslips, and workplace policies.

Your response must be:
- **Final**: No follow-up questions or uncertainty.
- **Clear and Polite**: Use emotionally intelligent language, especially if the user expresses frustration or confusion.
- **Context-Aware**: Avoid mentioning internal systems (e.g., database names or SQL sources) unless explicitly requested.
- **Structured**: Always return your answer in the following JSON format.
"""

Base = declarative_base()
# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///ai_database.sqlite3")

# Fix if DATABASE_URL starts with postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# For SQLite, we need check_same_thread=False
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_sql_database_instance():
    """Create and return a SQLDatabase instance or None on failure."""
    log_info("Aluke staring db",GLOBAL_SCOPE,NO_CONVO)
    db_uri, db_file = _build_db_uri_from_env()

    try:
        # Strip out unsupported query params like ssl-mode
        if "ssl-mode" in db_uri:
            db_uri = db_uri.split("?")[0]

        # Build engine with SSL args if needed
        connect_args = {}
        if "mysql+pymysql" in db_uri:
            connect_args = {
                "ssl": {"ssl_mode": "REQUIRED"}
            }

        engine = create_engine(db_uri, connect_args=connect_args)
        db_instance = SQLDatabase(engine)
        log_info(f"SQLDatabase connected to {db_uri} successfully.", GLOBAL_SCOPE, NO_CONVO)
        return db_instance

    except Exception as e:
        try:
            parsed = urlparse(db_uri)
            parsed_info = f"scheme={parsed.scheme}, netloc={parsed.netloc}, path={parsed.path}"
        except Exception:
            parsed_info = "(failed to parse URI)"

        log_error(
            f"Error connecting to SQLDatabase. URI: {db_uri}. Parsed: {parsed_info}. Error: {e}",
            GLOBAL_SCOPE,
            NO_CONVO,
        )
        return None


def _build_db_uri_from_env() -> tuple[str, str]:
    """Build a SQLAlchemy-compatible DB URI from available environment vars."""
    db_uri = os.getenv("DATABASE_URL")
    if not db_uri:
        db_uri = "sqlite:///ai_database.sqlite3"
    
    # Fix PostgreSQL URI scheme
    if db_uri.startswith("postgres://"):
        db_uri = db_uri.replace("postgres://", "postgresql://", 1)
    
    db_file_path = os.getenv("DATABASE_URL")

    return db_uri, db_file_path



# Initialize single shared DB instance (or None)
db = get_sql_database_instance()

DB_URI = None
DB_FILE_PATH = None
if db:
    # try to expose the uri and file path for backward compat if envs exist
    DB_URI, DB_FILE_PATH = _build_db_uri_from_env()


# ==================================
# 🛠️ HELPER FUNCTIONS
# ==================================

class MockUser:
    def __init__(self, tenant_id):
        self.tenant = tenant_id
        self.username = "System"
    def __str__(self): return self.username


class HRLogger:
    @staticmethod
    def _ctx(config):
        cfg = config.get("configurable", {}) if config else {}
        return {
            "t_id": cfg.get("tenant_id", "N/A"),
            "c_id": cfg.get("thread_id", "N/A"),
            "e_id": cfg.get("employee_id", "N/A")
        }

    @classmethod
    def info(cls, msg, config=None, **kwargs):
        ctx = cls._ctx(config)
        log_with_context(logging.INFO, f"[Conv: {ctx['c_id']} | Emp: {ctx['e_id']}] {msg}", MockUser(ctx["t_id"]))
        
    @classmethod
    def error(cls, msg, config=None, exc=None, **kwargs):
        ctx = cls._ctx(config)
        log_with_context(logging.ERROR, f"[Conv: {ctx['c_id']} | Emp: {ctx['e_id']}] {msg}", MockUser(ctx["t_id"]))
        
    @classmethod
    def warning(cls, msg, config=None, **kwargs):
        ctx = cls._ctx(config)
        log_with_context(logging.WARNING, f"[Conv: {ctx['c_id']} | Emp: {ctx['e_id']}] {msg}", MockUser(ctx["t_id"]))
        
    @classmethod
    def debug(cls, msg, config=None, **kwargs):
        ctx = cls._ctx(config)
        log_with_context(logging.DEBUG, f"[Conv: {ctx['c_id']} | Emp: {ctx['e_id']}] {msg}", MockUser(ctx["t_id"]))




def log_tool_usage(state: State, tool_name: str):
    state["tool_usage_log"] = state.get("tool_usage_log") or []
    state["tool_usage_log"].append(tool_name)


def get_time_based_greeting():
    """Return an appropriate greeting based on the current time."""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "Good morning"
    if 12 <= current_hour < 17:
        return "Good afternoon"
    return "Good evening"


def initialize_vector_store(tenant_id: str):
    tenant_id = str(tenant_id)
    persist_directory = os.path.join("faiss_dbs", tenant_id)
    conversation_id = ""

    global embeddings
    if embeddings is None:
        try:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") 
            log_info(
                f"Initializing embeddings. Key source check: ENV={bool(os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY'))}",
                tenant_id, conversation_id
            )
            if not api_key:
                raise ValueError("No API key found for embeddings. Set GEMINI_API_KEY or GOOGLE_API_KEY.")

            model = os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001")
            # os.environ["GOOGLE_API_KEY"] = api_key

            embeddings = GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)
            log_info("GoogleGenerativeAIEmbeddings initialized successfully.", tenant_id, conversation_id)
        except Exception as e:
            log_warning(f"Failed to initialize embeddings client: {e}", tenant_id, conversation_id)
            return None, {
                "status": "warning",
                "doc_count": 0,
                "embedding_disabled": True,
                "message": "Embeddings client initialization failed. RAG functionality limited."
            }

    # Use Django ORM for tenant lookups to avoid mixing SQLAlchemy and Django models
    tenant_obj = None
    current_tenant = None
    try:
        # Look up Tenant by code using Django ORM
        tenant_obj = Tenant.objects.filter(code=tenant_id).first()

        # If not found, fallback to DMC (idempotent get-or-create)
        if not tenant_obj:
            tenant_obj = Tenant.objects.filter(code="DMC").first()
            if not tenant_obj:
                tenant_obj = Tenant.objects.create(
                    name="DMC",
                    code="DMC",
                    subdomain="dmc",
                    is_active=True
                )

        # Query Tenant_AI using Django ORM
        # Import here to avoid circular imports at module load
        from .models import Tenant_AI

        current_tenant = Tenant_AI.objects.filter(tenant=tenant_obj).first()

        # If Tenant_AI doesn’t exist, create it once
        if not current_tenant:
            current_tenant = Tenant_AI.objects.create(
                tenant=tenant_obj,
                prompt_type="standard"  # or whatever default you want
            )

    except Exception as e:
        log_error(
            f"Error initializing tenant in vector store: {e}",
            tenant_id,
            conversation_id,
        )
        return None, {"error": f"Failed to initialize tenant: {str(e)}"}

    if not current_tenant:
        return None, {"error": "Tenant not found"}

    # Health check for embeddings
    try:
        embeddings.embed_query("Health check")
    except Exception as e:
        log_warning(
            f"Embedding API unavailable (non-fatal): {str(e)}. Using RAG without embeddings.",
            tenant_id, conversation_id,
        )
        return None, {
            "status": "warning",
            "doc_count": 0,
            "embedding_disabled": True,
            "message": "Vector store skipped due to embedding API unavailability. RAG functionality limited."
        }

    all_docs = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    # Process tenant_text
    if current_tenant.tenant_text:
        log_info("Processing raw tenant_text for vector store.", tenant_id, conversation_id)
        text_chunks = text_splitter.split_text(current_tenant.tenant_text)
        for chunk in text_chunks:
            all_docs.append(Document(page_content=chunk, metadata={"source": "tenant_text"}))

    # Process tenant_document
    if current_tenant.tenant_document and os.path.exists(str(current_tenant.tenant_document)):
        path = str(current_tenant.tenant_document)
        log_info(f"Processing knowledge file: {os.path.basename(path)}", tenant_id, conversation_id)
        try:
            if path.lower().endswith(".pdf"):
                loader = PyPDFLoader(path)
            elif path.lower().endswith(".txt"):
                loader = TextLoader(path)
            elif path.lower().endswith(".csv"):
                loader = CSVLoader(path)
            else:
                loader = UnstructuredFileLoader(path)
            all_docs.extend(loader.load_and_split(text_splitter=text_splitter))
        except Exception as e:
            log_error(f"Failed to process file {path}: {e}", tenant_id, conversation_id)

    # Finalize vector store
    if not all_docs:
        log_warning("No documentation found. Creating empty index.", tenant_id, conversation_id)
        vector_store = FAISS.from_texts([" "], embeddings)
    else:
        log_info(f"Creating vector store with {len(all_docs)} documents.", tenant_id, conversation_id)
        vector_store = FAISS.from_documents(all_docs, embeddings)

    os.makedirs(persist_directory, exist_ok=True)
    vector_store.save_local(persist_directory)
    log_info(f"Vector store initialized and saved to {persist_directory}.", tenant_id, conversation_id)
    return vector_store, {"status": "success", "doc_count": len(all_docs)}
# Connect to the checkpoint database using the file path


def get_llm_instance(llm_config=None):
    """
    Returns an LLM instance based on the provided configuration or global DB setting.
    
    Supported LLM types:
    - gemini: Google Gemini API
    - ollama: Local Ollama instance
    - ollama_cloud: Ollama Cloud API (requires OLLAMA_API_KEY)
    """
    # If explicit config passed, use it. Otherwise fetch global if needed.
    # Note: 'llm_config' here is expected to be a Django ORM object or None.
    logger.info("🌐 get_llm_instance ")
    if not llm_config:
        logger.info("🌐 Not Initializing")
        llm_config = LLM.objects.first()

    # Default to initialized model_with_tools if no config found or name is unknown
    if not llm_config:
        logger.info("🌐 Not Initializing")
        return model

    name = llm_config.name.lower()
    if name == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")  # Always from env
        model_name = llm_config.model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        
        # Instantiate Gemini
        # Standard safety settings can be added here as needed
        llm_instance = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0,
            convert_system_message_to_human=True 
        )
        logger.info("🌐 Initializing Gemini")
        # return llm_instance.bind_tools(tools)
        return llm_instance 
    elif name == "ollama_cloud":
        # Use ollama_cloud as a special sentinel value
        logger.info("🌐 Initializing Ollama Cloud LLM instance")
        llm_instance = OllamaService(
            base_url=OLLAMA_BASE_URL,  # Not used for cloud, but required by constructor
            username=OLLAMA_USERNAME,  # Not used for cloud
            password=OLLAMA_PASSWORD,  # Not used for cloud
            model="ollama_cloud"  # Special sentinel value triggers cloud API
        )
        logger.info("🌐 Initilzized ollama_cloud ")
        # return llm_instance.bind_tools(tools)
        return llm_instance 
    
    elif name == "ollama":
        model_name = llm_config.model or OLLAMA_MODEL
        llm_instance = OllamaService(
            base_url=OLLAMA_BASE_URL,
            username=OLLAMA_USERNAME,
            password=OLLAMA_PASSWORD,
            model=model_name
        )
        logger.info("🌐 Initiaized Ollama Self Hosting")
        # return llm_instance.bind_tools(tools)
        return llm_instance 
    logger.info("🌐 Fall Back to Defaul Model config")
    return model
model = get_llm_instance()  # Initialize global model instance based on DB config or default
llm = model

model_with_tools = model.bind_tools(tools)  # Bind tools to the model for agent use


# Initialize single shared DB instance (or None)
db = get_sql_database_instance()
DB_URI = None
DB_FILE_PATH = None

    # try to expose the uri and file path for backward compat if envs exist
    

# Initialize SQL Agent (Primary Method)
SQL_AGENT = None

if db:
    log_info(f"Dialect: {db.dialect}", GLOBAL_SCOPE, NO_CONVO)
    DB_URI, DB_FILE_PATH = _build_db_uri_from_env()

    # Get usable tables and log them
    try:
        usable_tables = db.get_usable_table_names()
        log_info(f"Available tables: {usable_tables}", GLOBAL_SCOPE, NO_CONVO)
    except Exception as e:
        log_warning(f"Could not retrieve usable table names: {e}", GLOBAL_SCOPE, NO_CONVO)
        usable_tables = []  # Ensure usable_tables is an empty list if there's an error
    # Dynamically run a sample query on the first available table
    if usable_tables:
        # Get the name of the first table
        first_table = usable_tables[0]
        sample_query = f"SELECT * FROM {first_table} LIMIT 5;"

        try:
            # Run the dynamic query and log the output
            log_info(
                f"Sample output (from {first_table}): {db.run(sample_query)}",
                GLOBAL_SCOPE,
                NO_CONVO,
            )
        except Exception as e:
            # Log a specific error if the dynamic query fails
            log_error(
                f"Error running sample query '{sample_query}': {e}",
                GLOBAL_SCOPE,
                NO_CONVO,
            )
    else:
        # Log if no usable tables were found
        log_warning(
            "No usable tables found in the database. Skipping sample query.",
            GLOBAL_SCOPE,
            NO_CONVO,
        )

    try:
        # Assuming SQLDatabaseToolkit and create_agent are correctly imported
        # from langchain_community.agent_toolkits import SQLDatabaseToolkit
        # from langchain.agents import create_agent

        toolkit = SQLDatabaseToolkit(db=db, llm=model)  # Use the model with tools for the agent
        tooly = toolkit.get_tools()

        # Change 1: Loop print changed to log_info
        for (tool_item ) in (tooly):  # Renamed 'tool' to 'tool_item' to avoid shadowing the imported 'tool' function/name
            log_info(f"{tool_item.name}: {tool_item.description}", GLOBAL_SCOPE, NO_CONVO )

        SQL_SYSTEM_PROMPT = """You are an agent designed to interact with a SQL database. Given an input question, create a syntactically correct {dialect} query, execute it, and return the answer.
        - You must query only the necessary columns.
        - You must double-check your query before execution.
        - DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP).
        - ALWAYS look at the tables first to understand the schema.
        - always limit your query to at most {top_k} results.
        """
        


        SQL_AGENT = create_agent(
            llm,
            tooly,
            system_prompt=SQL_SYSTEM_PROMPT.format(dialect=db.dialect, top_k=5),
        )

        # Change 2: Success print changed to log_info
        log_info("SQL Agent initialized successfullyyy.", GLOBAL_SCOPE, NO_CONVO)
        log_debug("ALUKE Agent initialized successfully.", GLOBAL_SCOPE, NO_CONVO)
    except Exception as e:
        # Change 3: Error print changed to log_error
        log_error( f"Error initializing SQL Agent: {e}. SQL query tool will not be available.", GLOBAL_SCOPE,NO_CONVO,)


# Dictionary to hold DB connections per tenant - Now imported from tools.py
# TENANT_DBS = {}
# TENANT_SQL_AGENTS = {}


# from ollama_service import OllamaService

# ==========================
# 🛠️ Tools
# ==========================

# tools_by_name = {tool.name: tool for tool in tools}
# model_with_tools = model.bind_tools(tools)
# NOTE: ChatOllama is now used for both chat and tool calling


# llm = llm.bind_tools(tools)
tools_by_name = {tool.name: tool for tool in tools}
# Ensure RunnableConfig is imported for the node signature


def should_continue(state: State) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    tenant_id = state.get("tenant_config", {}).get("tenant_id", "unknown")
    conversation_id = state.get("conversation_id", "unknown")
    log_info("Evaluating whether to continue or stop.", tenant_id, conversation_id)

    messages = state.get("messages", [])
    if not messages:
        return END
    # last_message = messages[-1]
    # FIX: Find the last AIMessage specifically
    last_message = next(
        (m for m in reversed(messages) if isinstance(m, AIMessage)), None
    )
    log_debug(f"Last LLM message: {last_message}", tenant_id, conversation_id)

    if not last_message or not getattr(last_message, "tool_calls", None):
        log_info("LLM made no tool calls. Ending workflow.", tenant_id, conversation_id)
        return END

    log_info(
        "LLM made tool calls. Continuing to tool node.", tenant_id, conversation_id
    )
    return "tool_node"



# config.py or constants.py

TOOL_INTENT_MAP = {
    "leave_management": {
        "tools": ["fetch_available_leave_types_tool", "prepare_leave_application_tool", 
                  "submit_leave_application_tool", "fetch_leave_status_tool", "calculate_num_of_days_tool"],
        "triggers": ["leave", "vacation", "sick leave", "day off", "approve", "leave balance", "resumption"]
    },
    "payslip_services": {
        "tools": ["get_payslip_tool"],
        "triggers": ["payslip", "salary", "pay statement", "earnings", "payroll"]
    },
    "hr_policy": {
        "tools": ["pdf_retrieval_tool"],
        "triggers": ["policy", "handbook", "benefits", "hr guide", "rules"]
    },
    "data_analysis": {
        "tools": ["sql_query_tool"],
        "triggers": ["report", "count", "average", "total", "statistics", "data"]
    },
    "visualization": {
        "tools": ["generate_visualization_tool"],
        "triggers": ["plot", "chart", "graph", "visualize", "show as a bar chart"]
    },
    "profile_updates": {
        "tools": ["update_employee_profile_tool", "create_customer_profile_tool", "get_customer_details_tool"],
        "triggers": ["update", "profile", "phone number", "bank account", "details"]
    },
    "recruitment": {
        "tools": ["search_job_opportunities_tool"],
        "triggers": ["job", "vacancy", "career", "hiring", "position"]
    },
    "travel_concierge": {
        "tools": ["search_travel_deals_tool"],
        "triggers": ["flight", "hotel", "travel", "booking", "trip"]
    },
    "general_inquiry": {
        "tools": ["web_search_tool"],
        "triggers": ["what is", "how to", "who is", "search"]
    }
}



def routing_guardrail_node(state: State):
    """
    Guardrail node: Validates tool calls and either allows them to proceed or
    sends them back to the assistant for correction.
    Returns a state dict indicating the next action.
    """
    logger.info("OYAS routing_guardrail_node  ")
    if not hasattr(state["messages"][-1], "tool_calls") or not state["messages"][-1].tool_calls:
        logger.info("OYAS jubilee")
        return {"next_node": END}

    user_input = next((m.content for m in reversed(state["messages"][:-1]) if hasattr(m, "content")), "").lower()

    for call in state["messages"][-1].tool_calls:
        tool_name = call["name"]
        is_allowed = False
        for intent, data in TOOL_INTENT_MAP.items():
            if tool_name in data["tools"]:
                if any(trigger in user_input for trigger in data["triggers"]):
                    is_allowed = True
                    break
    
        if not is_allowed:
            logger.warning(f"Guardrail blocked unauthorized tool call: {tool_name}")
            return {
                "messages": [SystemMessage(content=f"Unauthorized tool call: {tool_name}. Please re-evaluate.")], 
                "next_node": "assistant_node"
            }

    return {"next_node": "tool_node"}


def route_after_guardrail(state: State) -> str:
    """
    Routing function for guardrail conditional edges.
    Extracts the next_node from the guardrail node's state.
    """
    next_node = state.get("next_node")
    if next_node == END:
        return END
    return next_node or "tool_node"



def tool_node(state: State) -> dict:
    """Performs the tool call, injecting state for specific tools if required."""

    # 1. Extract context for logging
    tenant_config = state["tenant_config"]
    tenant_id = tenant_config.get("tenant_id", "unknown")
    conversation_id = state.get("conversation_id", "unknown")
    log_info("Tool node activated", tenant_id, conversation_id)

    # FIX: Find the AIMessage that actually contains the tool calls
    last_ai_message = next(
        (m for m in reversed(state["messages"]) if isinstance(m, AIMessage)), None
    )

    # result = []
    new_messages = []
    state_updates = {}

    if not last_ai_message:
        return {"messages": []}
    # 2. Iterate through all tool calls requested by the LLM
    for tool_call in state["messages"][-1].tool_calls:
        tool_name = tool_call.get("name")

        # Normalize tool name: strip non-ASCII / accidental unicode suffixes the LLM may add
        normalized_name = re.sub(r"[^\x00-\x7F]+", "", str(tool_name or "")).strip()
        if normalized_name != (tool_name or ""):
            log_warning(
                f"Normalizing tool name from {tool_name!r} to {normalized_name!r}",
                tenant_id,
                conversation_id,
            )

        # Try direct lookup with normalized name first, then original
        tool = tools_by_name.get(normalized_name) or tools_by_name.get(tool_name)

        # Fallback: fuzzy match by containment (covers small tokenization differences)
        if tool is None:
            for k in tools_by_name.keys():
                if k in normalized_name or normalized_name in k:
                    tool = tools_by_name[k]
                    log_info(f"Fuzzy-matched tool name {tool_name!r} -> {k!r}", tenant_id, conversation_id)
                    break

        if tool is None:
            # No usable tool found — surface a clear error for logging and upstream handling
            log_error(f"LangGraph execution failed: {tool_name!r}", tenant_id, conversation_id)
            raise Exception(f"Tool not found: {tool_name}")

        # tool_args = tool_call["args"].copy() # Get LLM's arguments and make a copy
        tool_args = (tool_call.get("args") or {}).copy()
        # Inject the full state into the tool arguments
        tool_args["state"] = state
        # Pass along the call identifier so tools can report it back
        tool_args["current_tool_id"] = tool_call.get("id")
        # Invoke the tool
        observation = tool.invoke(tool_args)

        # --- Handle Structured Tool Output ---
        # If the tool returned a dict, we extract content for the state and stringify for the LLM
        if isinstance(observation, dict):
            # Update specific state keys based on which tool was called
            if tool_name == "pdf_retrieval_tool":
                state_updates["pdf_content"] = observation.get("pdf_content")
                # Store sources in metadata or a dedicated source list if needed
                state_updates["type"] = "pdf"

            elif tool_name == "web_search_tool":
                state_updates["web_content"] = observation.get("web_content")
                state_updates["type"] = "web"

            # Convert dict to string for the ToolMessage so the LLM can read it
            content_for_llm = json.dumps(observation)
        else:
            content_for_llm = str(observation)

        new_messages.append(
            ToolMessage(content=content_for_llm, tool_call_id=tool_call["id"])
        )

        log_info( f"Executed {len(new_messages)} tool calls.", tenant_id, conversation_id)
        log_info( f"Executed {new_messages} tool calls.", tenant_id, conversation_id)

        # Return both the messages and the updated content fields
        return {"messages": new_messages, **state_updates}



def extract_final_answer(response):
    """
    Robustly extract the final text answer from an LLM response or structured object.
    """
    # Case 1: Structured Answer or dict
    if isinstance(response, dict):
        return response.get("answer") or json.dumps(response)
    
    # Case 2: AIMessage or object with .content
    if hasattr(response, "content") and response.content:
        content = response.content
    else:
        # Fallback if content is empty or response is not a message object
        if hasattr(response, "tool_calls") and response.tool_calls:
            return "Executing tools..."
        content = str(response) if response is not None else "LLM did not return a response"

    # Clean up markdown and extract JSON blocks if present
    content_clean = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.MULTILINE)
    
    # Try direct parse
    try:
        parsed = json.loads(content_clean)
        if isinstance(parsed, dict) and "answer" in parsed:
            return parsed["answer"]
    except:
        pass

    # Try searching for JSON-like blocks if direct parse failed
    json_blocks = re.findall(r"\{.*?\}", content_clean, flags=re.DOTALL)
    for block in json_blocks:
        try:
            obj = json.loads(block)
            if isinstance(obj, dict) and "answer" in obj:
                return obj["answer"]
        except:
            continue

    return content_clean or "LLM returned empty response"

def assistant_node(state: State, config: RunnableConfig):
    """
    Consolidated Assistant Node: HR Support, Data Analytics, and Customer Concierge.
    Handles multiple roles and tool calling.
    """
    tenant_id = config["configurable"].get("tenant_id", "unknown")
    conversation_id = config["configurable"].get("thread_id", "unknown")
    log_info(f"Assistant node triggered for tenant: {tenant_id}", tenant_id, conversation_id)

    # 1. DYNAMIC CONTEXT PREPARATION (HR/Leave Status)
    leave_app = state.get("leave_application")
    status_summary = "No active application."
    if leave_app:
        status = leave_app.get("status")
        if status == "success":
            status_summary = f"Application {leave_app.get('application_id')} completed."
        elif status == "prepared":
            resumption = leave_app.get("details", {}).get("resumptionDate", "TBD")
            status_summary = f"Application prepared. Action required: Confirm resumption date {resumption}."
        elif status == "error":
            status_summary = f"Process error: {leave_app.get('message')}"

    # 2. CONSOLIDATED SYSTEM PROMPT (Integrated from prompt.py)
    system_prompt = f"""
    {GLOBAL_FINAL_ANSWER_PROMPT}

    OPERATING PROTOCOLS:
    
    PROTOCOL 1: LEAVE REQUESTS
    - If the user wants to apply for leave, you MUST first call 'fetch_available_leave_types_tool'.
    - If the user specifies a leave type NOT in the list provided by 'fetch_available_leave_types_tool':
      1. Politely inform them that '[InvalidType]' is not available for their category.
      2. Re-list the valid options.
      3. Do NOT call 'prepare_leave_application_tool' until a valid type is selected.
    - LEAVE YEAR LOGIC: Ask the user: "Is this leave for the current year or your previous year's carry-over?"
      Current -> {current_year}, Previous -> {previous_year}.
    - SUCCESS: After 'submit_leave_application_tool' confirms success, if it was 'Vacation', offer help with travel via 'search_travel_deals_tool'.

    PROTOCOL 2: PAYSLIPS
    - Once 'get_payslip_tool' returns, inform the user: 'Your payslip has been sent to your email.'

    PROTOCOL 3: HR POLICIES & KNOWLEDGE
    - For policy questions, use 'pdf_retrieval_tool' to search HR handbooks.

    PROTOCOL 4: DATA ANALYTICS
    - Use 'sql_query_tool' for data inquiries. Provide actionable insights.
    - Use 'generate_visualization_tool' ONLY when explicitly asked to 'plot', 'chart', 'graph', or 'visualize'.

    PROTOCOL 5: PROFILE UPDATES
    - Use 'update_customer_tool' or 'update_employee_profile_tool'.
    - If bank name is missing for an account update, ask for it before calling the tool.

    PROTOCOL 6: LEAVE STATUS
    - Use 'fetch_leave_status_tool' for approvals and pending status.

    CONTEXT:
    - Employee ID: {state.get('employee_id')}
    - Current Date: {current_date_str}
    - Current Leave/Workflow Status: {status_summary}
    - Document Context: {state.get('pdf_content', 'None')}
    - Web Context: {state.get('web_content', 'None')}
    - SQL Result: {state.get('sql_result', 'None')}
    
    ### Output Format:
You MUST return ONLY a valid JSON object. Do not include any text outside the JSON block.
```json
{{
  "answer": "Your response to the user",
}}
```
    """

    # 3. LLM INVOCATION
    prompt_model = get_llm_instance()
    
    # If we are ready for a final answer (no more tool calls intended or last was a tool result)
    # we use structured output.
    messages = state["messages"]
    logger.info(f"Messages before assistant processing: {messages}")
    
    # Check if last message was a tool result
    if messages and isinstance(messages[-1], ToolMessage):
        logger.info("Last message was a tool result. Preparing to generate final answer with structured output.")
        # Generate structured final answer
        logger.info("Generating final structured answer.")
        structured_llm = prompt_model.with_structured_output(Answer)
        try:
            # final_answer_obj = structured_llm.invoke([SystemMessage(content=system_prompt)] + messages)
            unstructured_response = prompt_model.invoke([SystemMessage(content=system_prompt)] + messages)
            
            if hasattr(unstructured_response, "tool_calls") and unstructured_response.tool_calls:
                logger.info(f"Tool calls foundAtejjd: {unstructured_response.tool_calls}")
                return {"messages": [unstructured_response]}  # keep the AIMessage intact
            
        except Exception as e:
            log_error(f"Structured output generation failed: {e}", tenant_id, conversation_id)
            unstructured_response = None

        if unstructured_response:
            # Attach chart if present in state
            viz_result = state.get("visualization_result")
            if viz_result and "image_base64" in viz_result:
                unstructured_response.chart_base64 = viz_result["image_base64"]

            return {
                "messages": [AIMessage(content=unstructured_response.content)],
                # "leave_application": unstructured_response.dict(),
                # "metadata": {"sentiment": unstructured_response.sentiment, "sources": unstructured_response.source}
            }
        else:
            # Fallback to extract from raw invoke if structured fails
            logger.warning("Falling back to raw extraction in assistant_node.")
            response = prompt_model.invoke([SystemMessage(content=system_prompt)] + messages)
            final_answer = extract_final_answer(response)
            return {"messages": [AIMessage(content=final_answer)]}

    # Otherwise, regular tool-calling invoke
    llm_with_tools = prompt_model.bind_tools(tools)
    logger.info("Invoking LLM with tools for assistant response generation.")
    response = llm_with_tools.invoke([SystemMessage(content=system_prompt)] + messages)
    logger.info(f"LLM RAW ALukeee response Assitant Node: {response}")
    
    if hasattr(response, "tool_calls") and response.tool_calls:
        logger.info(f"Tool calls foundAtejjdy: {response.tool_calls}")
        return {"messages": [response]}  # keep the AIMessage intact
    

    # Check 2: JSON-wrapped Tool Calls (The "Ollama Fallback")
    if isinstance(response.content, str) and 'tool_calls' in response.content:

        try:
            logger.info(f"Tool calls foundAtejjdss: {response.tool_calls}")
            # Clean markdown if present
            clean_content = re.sub(r"^```json\s*|\s*```$", "", response.content.strip(), flags=re.MULTILINE)
            parsed = json.loads(clean_content)
            
            if "tool_calls" in parsed:
                # We manually reconstruct the tool_calls attribute so the rest of the graph works
                response.tool_calls = parsed["tool_calls"]
                # Ensure each call has an 'id' which LangGraph requires
                for call in response.tool_calls:
                    if 'id' not in call:
                        call['id'] = str(uuid.uuid4())
                    # Rename 'arguments' to 'args' if the LLM used the wrong key
                    if 'arguments' in call and 'args' not in call:
                        call['args'] = call.pop('arguments')
                
                return {"messages": [response]}
        except Exception as e:
            logger.error(f"Failed to manually parse tool calls: {e}")

    # --- END OF NEW PARSING ---

    final_answer = extract_final_answer(response)
    logger.info(f"LLM response Assitant Node: {final_answer}")
    return {"messages": [AIMessage(content=final_answer)]}




    # final_answer = extract_final_answer(response)
    # logger.info(f"LLM response Assitant Node: {final_answer}")
    # logger.info(f"Final Output Raw Aliko: {messages}")
    
    # return {"messages": [AIMessage(content=final_answer)]}


    # return {"messages": [final_answer]}


def build_graph(tenant_id: str, conversation_id: str, checkpointer=None):
    workflow = StateGraph(State)
    log_info("Building graph for tenant: {tenant_id}, conversation: {conversation_id}", tenant_id, conversation_id)

    # 1. Add Nodes
    workflow.add_node("assistant_node", assistant_node)
    log_info("Assistant node added to graph.", tenant_id, conversation_id)
    
    workflow.add_node("tool_node", tool_node)
    log_info("Tool node added to graph.", tenant_id, conversation_id)
    
    workflow.add_node("guardrail_node", routing_guardrail_node)
    log_info("Guardrail node added to graph.", tenant_id, conversation_id)

    # 2. Routing
    workflow.add_edge(START, "assistant_node")
    log_info("Edge added from START to assistant_node.", tenant_id, conversation_id)
    
    # Assistant decides if it needs a tool or should end
    workflow.add_conditional_edges(
        "assistant_node", 
        lambda x: "guardrail_node" if hasattr(x["messages"][-1], "tool_calls") and x["messages"][-1].tool_calls else END
    )
    log_info("Conditional edges added from assistant_node to guardrail_node and END.", tenant_id, conversation_id)
    
    
    # Guardrail decides if it passes to tool_node or rejects back to assistant
    workflow.add_conditional_edges(
    "guardrail_node",
    route_after_guardrail,  # Use the routing function
    {
        "tool_node": "tool_node",
        "assistant_node": "assistant_node",
        END: END
    }
)
    log_info("Conditional edges added from guardrail_node to tool_node and assistant_node.", tenant_id, conversation_id)
    
    # After tool execution, always return to assistant
    workflow.add_edge("tool_node", "assistant_node")
    log_info("Edge added from tool_node to assistant_node.", tenant_id, conversation_id)

    return workflow.compile(checkpointer=checkpointer)


def process_message(message_content: str,conversation_id: str,tenant_id: str,employee_id: str,file_path: Optional[str] = None,summarization_request: Any = None) -> dict:
    """Main function to process user messages using the LangGraph agent."""


    log_info("Starting message processing pipeline", tenant_id, conversation_id)
    log_info(f"Employee ID: {employee_id}-message Content: {message_content}", tenant_id, conversation_id)

    current_tenant = None
    user = None
    tenant_obj = None
    db_uri = None
    
    # --- 1. Tenant Configuration via Employee ID ---
    try:
        # Fetch user by employee_id (email)
        if employee_id:
            user = User.objects.filter(email=employee_id).first()
            if not user:
                log_warning(f"No user found for email: {employee_id}. Falling back to tenant_id.", tenant_id, conversation_id)
            else:
                # Get tenant from user
                tenant_obj = user.tenant
                if tenant_obj:
                    tenant_id = tenant_obj.code
                    log_info(f"Fetched tenant '{tenant_id}' from user {employee_id}", tenant_id, conversation_id)
        
        # Use Django ORM with select_related for better performance
        current_tenant = Tenant_AI.objects.select_related('prompt_template', 'tenant').filter(tenant__code=tenant_id).first()

        if not current_tenant:
            log_error(f"No Tenant_AI found for tenant_code={tenant_id}", tenant_id, conversation_id)
            return {"answer": "Error: Tenant config missing.", "metadata": {}}

            
        # Using db_uri if present (idle but still accessible)
        db_uri = current_tenant.db_uri
        if not db_uri and tenant_obj:
            # Fallback: try to get db_uri from Tenant_AI's tenant relationship
            db_uri = current_tenant.tenant.code if hasattr(current_tenant, 'tenant') else None
        if db_uri and db_uri.startswith("postgres://"):
            db_uri = db_uri.replace("postgres://", "postgresql://", 1)
        # --- Global LLM Configuration ---
        global_llm = LLM.objects.first()
        if global_llm:
            log_info(f"Using Global LLM Config: {global_llm.name} - {global_llm.model}", tenant_id, conversation_id)
            # Dynamic Configuration via Environment Variables (Thread-safety caveat applies)
            if global_llm.name.lower() == "gemini":
                    if global_llm.model: os.environ["GEMINI_MODEL"] = global_llm.model
            elif global_llm.name.lower() == "ollama":
                    if global_llm.model: os.environ["OLLAMA_MODEL"] = global_llm.model
        else:
            log_warning("No Global LLM found. Relying on default system environment.", tenant_id, conversation_id)

        # --- 2. Prompt Lookup Logic ---
        is_hum_agent_allow = getattr(current_tenant, "is_hum_agent_allow", True)
        requested_type = getattr(current_tenant, "prompt_type", "standard") or "standard"
        
        # Build tenant_config_dict for tools that need tenant information
        tenant_config_dict = {
            "tenant_id": tenant_id,
            "employee_id": employee_id,
            "db_uri": db_uri,
            "user": user
        }
        log_info(f"Tenant config prepared. DB URI present: {bool(db_uri)}", tenant_id, conversation_id)
        log_info(f"Fetching prompts for type: {requested_type}", tenant_id, conversation_id)
        
        # Try to fetch the specific prompt type using Django ORM
        prompt_tpl = Prompt.objects.filter(name=requested_type).first()
        
        # Fallback to 'standard' if not found
        if not prompt_tpl and requested_type != "standard":
            log_info(f"Prompt type '{requested_type}' not found. Falling back to 'standard'.", tenant_id, conversation_id)
            prompt_tpl = Prompt.objects.filter(name="standard").first()

        if prompt_tpl:
            final_answer_prompt = (
                prompt_tpl.is_hum_agent_allow_prompt 
                if is_hum_agent_allow 
                else prompt_tpl.no_hum_agent_allow_prompt
            )
            summary_prompt = prompt_tpl.summary_prompt
        else:
            # Absolute fallback to legacy fields on Tenant
            log_warning("No Prompt record found even for 'standard'. Using Tenant fallbacks.", tenant_id, conversation_id)
            final_answer_prompt = getattr(current_tenant, "final_answer_prompt", "")
            summary_prompt = getattr(current_tenant, "summary_prompt", "")

        log_info(f"Prompts resolved. Using Prompt ID: {prompt_tpl.id if prompt_tpl else 'N/A'}", tenant_id, conversation_id)
    except Exception as e:
        log_error(f"Database error in process_message: {e}", tenant_id, conversation_id)
        log_exception_auto(f"DB stack trace: {e}", tenant_id, conversation_id)
        return {"answer": "Error: Database failure.", "metadata": {}}

    # --- 2. Initialization & Vector Store ---
    persist_directory = os.path.join("faiss_dbs", tenant_id)

    # Updated: initialize_vector_store now handles text field + documents
    vector_store_result = initialize_vector_store(tenant_id)

    # Unpack based on your initialize_vector_store return (vector_store, info_dict)
    tenant_vector_store, vs_info = (
        vector_store_result
        if isinstance(vector_store_result, tuple)
        else (vector_store_result, {})
    )

    if tenant_vector_store is not None:
        try:
            document_count = tenant_vector_store.index.ntotal
            log_info(f"Vector store document count: {document_count}", tenant_id, conversation_id)
        except AttributeError:
            log_error("Unexpected vector store structure.", tenant_id, conversation_id)
    else:
        log_warning("Vector store is None.", tenant_id, conversation_id)

    # --- 3. Strict Summarization Flag ---
    # Normalizing: Only string "true" or True boolean is True. Everything else is False.
    if isinstance(summarization_request, str):
        summarization_flag = summarization_request.lower() == "true"
    else:
        summarization_flag = bool(summarization_request)

    log_info(
        f"Summarization request normalized: {summarization_flag}",
        tenant_id,
        conversation_id,
    )

    # --- 4. Attachment Processing (Vision Integrated) ---
    attached_content = None
    if file_path and os.path.exists(file_path):
        try:
            image = Image.open(file_path)
            image.thumbnail([512, 512])
            
            # Convert image to base64 for Vision analysis
            buffered = io.BytesIO()
            image_format = image.format if image.format else "PNG"
            image.save(buffered, format=image_format)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            vision_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
            msg = HumanMessage(
                content=[
                    {"type": "text", "text": "Describe this image in detail, focusing on any data, charts, or text."},
                    {"type": "image_url", "image_url": {"url": f"data:image/{image_format.lower()};base64,{img_str}"}},
                ]
            )
            response = vision_llm.invoke([msg])
            attached_content = response.content
            log_info(f"Vision analysis completed: {attached_content[:100]}...", tenant_id, conversation_id)
        except Exception as e:
            log_error(f"Vision processing failed: {e}", tenant_id, conversation_id)
            attached_content = f"[Attachment present but could not be processed: {e}]"

    # --- 5. Updated Tenant Config Dictionary ---
    if current_tenant:
        tenant_config_dict = {
            "tenant_id": tenant_id,
            "tenant_name": getattr(current_tenant, "tenant_name", "Bank"),
            "vector_store_path": persist_directory,
            "chatbot_greeting": getattr(current_tenant, "chatbot_greeting", ""),
            "agent_node_prompt": getattr(current_tenant, "agent_node_prompt", ""),
            "final_answer_prompt": final_answer_prompt,
            "summary_prompt": summary_prompt,
            "db_uri": db_uri,
            "tenant_website": getattr(current_tenant, "tenant_website", ""),
            "tenant_knowledge_base": getattr(current_tenant, "tenant_knowledge_base", ""),
            "sentiment_threshold": getattr(current_tenant, "sentiment_threshold", 0),
            "is_hum_agent_allow": is_hum_agent_allow,
            "conf_level": getattr(current_tenant, "conf_level", 40),
            "ticket_type": getattr(current_tenant, "ticket_type", []),
            "message_tone": getattr(current_tenant, "message_tone", "Professional"),
        }
    else:
        tenant_config_dict = {}

    # --- 6. SQL Agent Initialization ---
    if tenant_id not in TENANT_SQL_AGENTS:
        sql_agent = init_sql_agent(
            state={"tenant_id": tenant_id, "db_uri": db_uri},
            llm=llm,
        )
        if sql_agent:
            log_info("SQLs Agent initialized successfully.", tenant_id, conversation_id)
            TENANT_SQL_AGENTS[tenant_id] = sql_agent
        else:
            log_error("SQLs Agent initialization failed.", tenant_id, conversation_id)

    if TENANT_SQL_AGENTS.get(tenant_id):
        log_info("SQLY Agent is ready.", tenant_id, conversation_id)

    # --- 7. Graph State Preparation ---
    initial_state = {
        "messages": [HumanMessage(content=message_content)],
        "attached_content": attached_content,
        "user_query": message_content or "",
        "summarization_request": "true" if summarization_flag else "false",
        "conversation_id": conversation_id,
        "tenant_config": tenant_config_dict,
        "vector_store_path": persist_directory,
        "metadata": {},
        "employee_id":employee_id,
    }
    log_info("Initial state prepared", tenant_id, conversation_id)      
    # --- 8. Graph Execution ---
   
    with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        log_info("PostgresSaver initialized", tenant_id, conversation_id)
        checkpointer.setup()
        graph = build_graph(tenant_id, conversation_id, checkpointer=checkpointer)
        log_info("Graph built successfully", tenant_id, conversation_id)
        try:
            config_dict = {
                "configurable": {
                    "thread_id": conversation_id,
                    "employee_id": employee_id,
                    "tenant_id": tenant_id,
                    "db_uri": db_uri
                }
            }
            output = graph.invoke(State(**initial_state), config=config_dict) 
            log_error(f"grapuy Raw State: {output}", tenant_id, conversation_id)
            log_info("LangGraph execution completed", tenant_id, conversation_id)
        except Exception as e:
            log_error(f"LangGraph execution failed: {e}", tenant_id, conversation_id)
            raise

    # --- 9. Response Extraction ---
    current_answer = output.get("leave_application")
    
    # Updated extraction logic: ensure we get a string answer regardless of model behavior
    if isinstance(current_answer, dict) and "answer" in current_answer:
        current_answer = current_answer["answer"]
    
    if not current_answer:
        # Fallback to extracting from the last message in the graph state
        messages = output.get("messages", [])
        if messages:
            current_answer = extract_final_answer(messages[-1])
        else:
            current_answer = "I apologize, but I encountered an internal error processing your request."

    logger.info(f"LLM response Process message : {current_answer}")
    metadata = output.get("metadata", {})

    if current_answer:
        # If it's a dict (from our structured Answer model), extract the specific 'answer' string
        if isinstance(current_answer, dict) and "answer" in current_answer:
            current_answer = current_answer["answer"]
            
        return {
            "answer": current_answer,
            "metadata": metadata,
        }
    else:
        last_message = output.get("messages", [AIMessage(content="Internal error.")])[-1]

        if hasattr(last_message, "content"):
            # Only take the text content, not the whole object
            fallback = last_message.content
        else:
            fallback = str(last_message)

        logger.info(f"LLM Response Fallback: {fallback}")
        return {"answer": fallback, "metadata": {}}