# ==================================
# 📦 Standard Library Imports
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
from logging.handlers import RotatingFileHandler
from collections import UserDict
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from importlib import metadata
from io import BytesIO
from math import log
from pathlib import Path
from pdb import run
from typing import Any, Dict, List, Literal, Optional, Union, Annotated
from typing_extensions import TypedDict
from urllib.parse import urlparse
from xml.dom.minidom import Document
from langgraph.graph import END, START, MessagesState, StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
# ==================================
# 📦 Third-Party Libraries (General)
# ==================================
from dotenv import load_dotenv
from PIL import Image
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import Boolean, create_engine
from sqlalchemy.orm import Session

# ==================================
# 📦 PDF & Document Processing
# ==================================
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from bs4 import BeautifulSoup as soup

# ==================================
# 📦 Database & ORM
# ==================================
from database import SessionLocal, Tenant, Conversation, Message, Prompt, get_db, LLM
# from django.conf import settings # Removed Django dependency

# ==================================
# 📦 LangChain Core & Messages
# ==================================
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

# ==================================
# 📦 LangChain Document Loaders & Text Splitting
# ==================================
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredFileLoader,
    CSVLoader,
    RecursiveUrlLoader,
    WebBaseLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ==================================
# 📦 LangChain Vectorstores & Utilities
# ==================================
from langchain_community.vectorstores import FAISS, Chroma
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_tavily import TavilySearch

# ==================================
# 🤖 LangChain Agents & Tools
# ==================================
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from langchain.messages import RemoveMessage
from langchain.tools import tool, ToolRuntime

# ==================================
# 🚀 LLM Providers
# ==================================
# from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import GoogleGenerativeAIEmbeddings
# from langchain_groq import ChatGroq
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# ==================================
# 📊 LangGraph Core
# ==================================
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, Send
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
# from langchain_ollama import ChatOllama # Replaced by verified OllamaService
# from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.sqlite import SqliteStore

# ==================================
# 🎨 Display/Notebook Utilities
# ==================================
# from IPython.display import display
from pprint import pprint

# ==================================
# 🔧 Custom Imports
# ==================================
# from ollama_service import OllamaService # Replaced by ChatOllama

# Ensure UTF-8 output if possible
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# Ensure UTF-8 output if possible
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
try:
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Create logs directory if it doesn't exist
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "chatbot.log")

logging.captureWarnings(True)

logging.basicConfig(
    level=logging.DEBUG,  # keep DEBUG for your own app
    format="%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding="utf-8"),
    ],
    force=True,
)


logger = logging.getLogger(__name__)
logger.propagate = True # Flow to root logger for persistence

# Suppress noisy libraries
logging.getLogger("watchfiles").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.INFO)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("langsmith").setLevel(logging.INFO)

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


def normalize_answer_structure(ans: dict) -> dict:
    """Ensure the parsed answer dict uses lists for fields expected as lists.

    Particularly handles `source_type` which historically was a string.
    Modifies the dict in-place and returns it for convenience.
    """
    if ans is None:
        return ans
    st = ans.get("source_type")
    if not isinstance(st, list):
        ans["source_type"] = [str(st)] if st is not None else []
    # also ensure ticket is list
    t = ans.get("ticket")
    if t is None:
        ans["ticket"] = []
    elif isinstance(t, str):
        ans["ticket"] = [t]
    elif not isinstance(t, list):
        ans["ticket"] = [str(t)]
    return ans

## Configuration & Environment Variables

load_dotenv()
logger.info(f"DEBUG: GEMINI_API_KEY found in .env: {bool(os.getenv('GEMINI_API_KEY'))}")
logger.info(f"DEBUG: GOOGLE_API_KEY found in env: {bool(os.getenv('GOOGLE_API_KEY'))}")


# 1. API Keys (Load from environment)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
logger.info(f"DEBUG: Global GOOGLE_API_KEY initialized: {bool(GOOGLE_API_KEY)}")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Ensure this is set in .env if used

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = "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"
os.environ["LANGSMITH_PROJECT"] = "pr-loyal-retirement-94"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
# os.environ["GOOGLE_API_KEY"] = "AIzaSyAvickMfWOE8-GPch0NygEzFUu-oYoLWLo"
# os.environ["GOOGLE_API_KEY"] = "AIzaSyAd35RkDDAKTLZahU9AaOTUP0yxTrNqfsA"
# os.environ["GOOGLE_API_KEY"] = "AIzaSyA58JEIXummKfS0Ca2JzWf-F7slVjt5zzA"

os.environ["TAVILY_API_KEY"] = "lsv2_pt_b52435093087464baaba87923a5051c2_8b39a6c"


# 2. Model/Service Name Variables
OLLAMA_BASE_URL = "https://ai.notchhr.io/api/chat/local"
OLLAMA_USERNAME = "ai-user"
OLLAMA_PASSWORD = "x2GS7jEF@#2T"
OLLAMA_MODEL = "gpt-oss-safeguard:20b"

embeddings = None

# ==================================
# 🚀 LangChain/LangGraph Integrations (LLMs)
# ==================================

# ==================================
# 🛠️ LangChain Tools & Utilities
# ==================================

# ==================================
# 🎨 Display/Notebook Utilities
# ==================================

# ==================================
# 🌐 Django Configuration
# ==================================

# ==================================
# 🔧 Ollama Integration (Custom)
# ==================================
# 4. LLM Initialization
# Using verified OllamaService for reliable connectivity
from ollama_service import OllamaService
# from ollama_service import OllamaService

llm = OllamaService(
    base_url=OLLAMA_BASE_URL,
    username=OLLAMA_USERNAME,
    password=OLLAMA_PASSWORD,
    model=OLLAMA_MODEL
)
model = llm


# 5. Tool Initialization
# tavily_search = TavilySearch(max_results=2)

# Placeholders for global startup logs
GLOBAL_SCOPE = "GLOBAL"
NO_CONVO = "N/A"


# Connect to the checkpoint database using the file path
checkpoint_file = "langgraph_checkpoints.sqlite"
memorys = AsyncSqliteSaver.from_conn_string(checkpoint_file)

log_info(f"Using checkpoint file: {checkpoint_file}", GLOBAL_SCOPE, NO_CONVO)


# from langchain_community.utilities import SQLDatabase
# In your main config file (where you define global constants)



def _build_db_uri_from_envv1() -> tuple[str, str]:
    """Build a SQLAlchemy-compatible DB URI from available environment vars.

    Returns a tuple of (DB_URI, DB_FILE_PATH). DB_FILE_PATH is a best-effort
    local filename when using a sqlite file path.
    """
    raw_service = os.getenv("ServiceURIs") or os.getenv("DB_URI") or os.getenv("DATABASE_URL")
    log_info(f"Using DB URI: {raw_service}", GLOBAL_SCOPE, NO_CONVO)
    if not raw_service:
        # Default to a local sqlite file in the working directory
        raw_service = "sqlite:///ai_database.sqlite3"

    # If the raw_service looks like a bare filename (no scheme), turn it
    # into a sqlite file URI.
    if "://" in raw_service:
        db_uri = raw_service
    else:
        # Strip leading/trailing whitespace and ensure no accidental slashes
        db_uri = f"sqlite:///{raw_service.strip().lstrip('/') }"

    # Determine a sensible DB_FILE_PATH for sqlite fallback/debugging
    db_file_path = "ai_database.sqlite3"
    try:
        parsed = urlparse(db_uri)
        if parsed.scheme == "sqlite":
            # For sqlite, path contains the local file path
            db_file_path = parsed.path.lstrip("/") or db_file_path
    except Exception:
        # If parsing fails, leave defaults in place
        pass

    return db_uri, db_file_path
import os
from urllib.parse import urlparse
from sqlalchemy import create_engine
from langchain_community.utilities.sql_database import SQLDatabase

def _build_db_uri_from_env() -> tuple[str, str]:
    """Build a SQLAlchemy-compatible DB URI from available environment vars."""
    raw_service = os.getenv("SQL_URL") or os.getenv("DB_URI") or os.getenv("DATABASE_URL")
    if not raw_service:
        raw_service = "sqlite:///ai_database.sqlite3"

    # Normalize URI
    if "://" in raw_service:
        db_uri = raw_service
    else:
        db_uri = f"sqlite:///{raw_service.strip().lstrip('/') }"

    # Default file path for sqlite
    db_file_path = "ai_database.sqlite3"
    try:
        parsed = urlparse(db_uri)
        if parsed.scheme == "sqlite":
            db_file_path = parsed.path.lstrip("/") or db_file_path
    except Exception:
        pass

    return db_uri, db_file_path


def get_sql_database_instance():
    """Create and return a SQLDatabase instance or None on failure."""
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

def get_sql_database_instancev1():
    """Create and return a `SQLDatabase` instance or None on failure.

    This function centralizes DB URI construction and improves error logging
    so callers can understand why connection attempts fail.
    """
    db_uri, db_file = _build_db_uri_from_env()

    try:
        db_instance = SQLDatabase.from_uri(db_uri)
        log_info(f"SQLDatabase connected to {db_uri} successfully.", GLOBAL_SCOPE, NO_CONVO)
        return db_instance
    except Exception as e:
        # Provide actionable logging: raw URI and parsing components
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


# Initialize single shared DB instance (or None)
db = get_sql_database_instance()
DB_URI = None
DB_FILE_PATH = None
if db:
    # try to expose the uri and file path for backward compat if envs exist
    DB_URI, DB_FILE_PATH = _build_db_uri_from_env()


def safe_json(data):
    """Ensures safe JSON serialization to prevent errors."""
    import json  # Import json locally if it's not imported at the top-level

    try:
        return json.dumps(data)
    except (TypeError, ValueError):
        return json.dumps({})  # Returns an empty JSON object if serialization fails



def initialize_vector_store(tenant_id: str):
    persist_directory = os.path.join("faiss_dbs", tenant_id)
    conversation_id = ""

    # Ensure embeddings client is available and lazily initialized to avoid
    # making network calls at import time.
    global embeddings
    if embeddings is None:
        try:
            # Priority: os.environ then fallback to global constant
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or GOOGLE_API_KEY
            
            log_info(f"Initializing embeddings. Key source check: ENV={bool(os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY'))}, GLOBAL={bool(GOOGLE_API_KEY)}", tenant_id, conversation_id)
            
            if not api_key:
                raise ValueError("No API key found for embeddings. Set GEMINI_API_KEY or GOOGLE_API_KEY.")

            model = os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001")
            
            # Ensure it's in the environment as well for internal library fallbacks
            os.environ["GOOGLE_API_KEY"] = api_key
            
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

    db = SessionLocal()
    try:
        current_tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    finally:
        db.close()
        
    if not current_tenant:
        return None, {"error": "Tenant not found"}

    # Health check for embeddings (graceful fallback if embedding API fails)
    try:
        embeddings.embed_query("Health check")
    except Exception as e:
        log_warning(
            f"Embedding API unavailable (non-fatal): {str(e)}. Using RAG without embeddings.",
            tenant_id,
            conversation_id,
        )
        # Return None but as a non-fatal error — app will continue without vector store
        return None, {
            "status": "warning",
            "doc_count": 0,
            "embedding_disabled": True,
            "message": "Vector store skipped due to embedding API unavailability. RAG functionality limited."
        }

    all_docs = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    # 1. Process tenant_text (Direct String from DB)
    if current_tenant.tenant_text:
        log_info(
            "Processing raw tenant_text for vector store.", tenant_id, conversation_id
        )
        text_chunks = text_splitter.split_text(current_tenant.tenant_text)
        for chunk in text_chunks:
            all_docs.append(
                Document(page_content=chunk, metadata={"source": "tenant_text"})
            )

    # 2. Process tenant_knowledge_base (URL Crawling)
    # if current_tenant.tenant_knowledge_base:
    #     log_info(f"Crawling knowledge base: {current_tenant.tenant_knowledge_base}", tenant_id, conversation_id)
    #     try:

    #         loader = RecursiveUrlLoader(
    #         url=current_tenant.tenant_knowledge_base,
    #         max_depth=2,
    #         extractor=lambda x: soup(x, "html.parser").text,
    #         prevent_outside=True  # Strictly stays within the base domain
    #     )
    #         # load_and_split handles the splitting into chunks automatically
    #         web_docs = loader.load_and_split(text_splitter=text_splitter)
    #         for doc in web_docs:
    #             doc.metadata["source"] = "tenant_knowledge_base"
    #         all_docs.extend(web_docs)
    #     except Exception as e:
    #         log_error(f"Failed to crawl knowledge base URL: {e}", tenant_id, conversation_id)

    # 3. Process tenant_document (Physical File)
    if current_tenant.tenant_document and os.path.exists(str(current_tenant.tenant_document)):
        path = str(current_tenant.tenant_document)
        log_info(
            f"Processing knowledge file: {os.path.basename(path)}",
            tenant_id,
            conversation_id,
        )

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

    # 4. Finalizing the Vector Store
    if not all_docs:
        # Avoid empty index errors by providing a placeholder if no info exists
        log_warning(
            "No documentation found. Creating empty index.", tenant_id, conversation_id
        )
        vector_store = FAISS.from_texts([" "], embeddings)
    else:
        vector_store = FAISS.from_documents(all_docs, embeddings)

    # Persistence
    os.makedirs(persist_directory, exist_ok=True)
    vector_store.save_local(persist_directory)

    return vector_store, {"status": "success", "doc_count": len(all_docs)}


def initialize_vector_store1(tenant_id: str):
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
    persist_directory = os.path.join("faiss_dbs", tenant_id)
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


# --- Logging and Error Helpers ---
# NOTE: The implementation below relies on 'logger' and 'log_exception_auto' being defined


# Define the input schema for the multiplication tool
class MultiplicationInput(BaseModel):
    """Input for the multiplication tool."""

    a: Union[int, float] = Field(description="The first number to multiply.")
    b: Union[int, float] = Field(description="The second number to multiply.")
    # Add a simple string field if you need context from the state
    context_message: str = Field(
        description=" The exact value of   llm_calls in the state message eg '2' "
    )
    model_provider: str = Field(
        description=" The name of the model being used eg   eg 'chatgpt' "
    )


# ==========================
# 📊 Pydantic Schemas (Revised for Clarity)
# ==========================
class ToolInput(BaseModel):
    """Input for the multiplication tool."""

    conversation_id: str = Field(
        description="The value  convassociatied with conversation_id key  in the state meessage eg 'ers1'."
    )
    query: str = Field(
        description="TThe search workd suitable for  the user message context  ."
    )
    tenant_id: str = Field(
        description="The value  convassociatied with conversation_id key  in the state meessage eg '111'."
    )

    # # Add a simple string field if you need context from the state
    # context_message: str = Field(description=" The intt value of   llm_calls in the state message ")


class Answer(BaseModel):
    """The final, structured answer for the user."""

    answer: str = Field(
        description="Clear, concise, polite response to the user's query."
    )
    sentiment: int = Field(description="User's sentiment score from -2 to +2.")
    confidence_score: int = Field(
        default=1, description="AI confidence level in the response from 0-100."
    )  # Added
    ticket: List[str] = Field(description="List of relevant service channels.")
    source: List[str] = Field(description="Names of the tools used.")
    human_assistant: bool = Field(description="True if human assistance is required.")
    source_type: List[str] = Field(description="Type of the source used to generate the answer")
    # source_type: str = Field(
    #     default="AI", description="Type of the source used to generate the answer."
    # )


class Summary(BaseModel):
    """Conversation summary schema."""

    summary: str = Field(description="A concise summary of the entire conversation.")
    sentiment: int = Field(
        description="Overall sentiment of the conversation from -2 to +2."
    )
    unresolved_tickets: List[str] = Field(
        description="A list of channels with unresolved issues."
    )
    all_sources: List[str] = Field(
        description="All the tools used in the entire conversation ."
    )
    summary_human_assistant: bool = Field(
        description="Set to True ONLY if human assistance is required, otherwise False."
    )


class State(MessagesState):
    """Manages the conversation state. Uses Pydantic models for structured data."""

    user_query: str
    attached_content: Optional[str]

    # Core identifiers
    conversation_id: str
    tenant_id: str

    # Tenant configuration and vector store
    tenant_config: Optional[Dict[str, Any]]
    vector_store_path: Optional[str]  # ✅ ADD THIS LINE

    summarization_request: bool
    # ✅ add this

    # vector_store: Optional[VectorStore]

    # Tool outputs
    pdf_content: Optional[str]
    web_content: Optional[str]
    ql_result: Optional[str]
    type: Optional[str]  # To indicate the type of last tool output

    # --- FINAL OUTPUTS ---
    # According to instructions, use leave_application for the structured result
    leave_application: Optional[Dict[str, Any]]  # ✅ Added as the primary state key
    current_answer: Optional[Answer]
    conversation_summary: Optional[Summary]
    metadata: Optional[Dict[str, Any]]
    human_assistant_required: bool

    # Utility

    next_node: Optional[str]
    tool_usage_log: Optional[List[str]]  # Optional tracking
    llm_calls: int
    
    source_documents: Optional[List[str]]  # Optional tracking


# ==========================
# 🛠️ Tools
# ==========================
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


def extract_answer_from_response(response) -> Answer:
    """
    Extracts JSON from AIMessage response and validates against Answer model.
    Handles list-of-dicts content and markdown fences.
    """
    raw_text = None

    # Case 1: response.content is a list of dicts
    if isinstance(response.content, list):
        for item in response.content:
            if isinstance(item, dict) and "text" in item:
                raw_text = item["text"]
                break
    # Case 2: response.content is a string
    elif isinstance(response.content, str):
        raw_text = response.content

    if not raw_text:
        raise ValueError("No text content found in response")

    # Strip markdown fences like ```json ... ```
    cleaned = re.sub(r"^```json|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()

    # Parse JSON
    parsed = json.loads(cleaned)

    # Fix typo if needed
    if "human_assistant" in parsed:
        parsed["human_assistant"] = parsed.pop("human_assistant")

    # Validate against Answer model
    return Answer(**parsed)


# Placeholders for global startup logs (assuming they are defined globally or locally)
GLOBAL_SCOPE = "GLOBAL"
NO_CONVO = "N/A"

# Assuming db (SQLDatabase object) is already initialized and connected
# from langchain_community.utilities import SQLDatabase
# db = SQLDatabase.from_uri(...)

if db:  # Only log this information if the connection was successful
    # print(f"Dialect: {db.dialect}")
    log_info(f"Dialect: {db.dialect}", GLOBAL_SCOPE, NO_CONVO)

    # print(f"Available tables: {db.get_usable_table_names()}")
    try:
        log_info(
            f"Available tables: {db.get_usable_table_names()}", GLOBAL_SCOPE, NO_CONVO
        )
    except Exception as e:
        log_warning(
            f"Could not retrieve usable table names: {e}", GLOBAL_SCOPE, NO_CONVO
        )

    # Guarded sample query: run only if the 'Artist' table actually exists
    try:
        usable = []
        try:
            usable = db.get_usable_table_names() or []
        except Exception:
            usable = []

        if "Artist" in usable:
            try:
                log_info(
                    f"Sample output: {db.run('SELECT * FROM Artist LIMIT 5;')}",
                    GLOBAL_SCOPE,
                    NO_CONVO,
                )
            except Exception as e:
                log_error(
                    f"Error running sample query 'SELECT * FROM Artist LIMIT 5;': {e}",
                    GLOBAL_SCOPE,
                    NO_CONVO,
                )
        else:
            log_info("Skipping sample 'Artist' query; table not present.", GLOBAL_SCOPE, NO_CONVO)
    except Exception:
        # Defensive: ensure startup doesn't fail for any unexpected reasons
        log_warning("Skipping guarded sample query due to unexpected error.", GLOBAL_SCOPE, NO_CONVO)

# Initialize SQL Agent (Primary Method)
SQL_AGENT = None

if db:
    log_info(f"Dialect: {db.dialect}", GLOBAL_SCOPE, NO_CONVO)

    # Get usable tables and log them
    try:
        usable_tables = db.get_usable_table_names()
        log_info(f"Available tables: {usable_tables}", GLOBAL_SCOPE, NO_CONVO)
    except Exception as e:
        log_warning(
            f"Could not retrieve usable table names: {e}", GLOBAL_SCOPE, NO_CONVO
        )
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

        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        tooly = toolkit.get_tools()

        # Change 1: Loop print changed to log_info
        for (
            tool_item
        ) in (
            tooly
        ):  # Renamed 'tool' to 'tool_item' to avoid shadowing the imported 'tool' function/name
            log_info(
                f"{tool_item.name}: {tool_item.description}", GLOBAL_SCOPE, NO_CONVO
            )

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
        log_info("SQL Agent initialized successfully.", GLOBAL_SCOPE, NO_CONVO)

    except Exception as e:
        # Change 3: Error print changed to log_error
        log_error(
            f"Error initializing SQL Agent: {e}. SQL query tool will not be available.",
            GLOBAL_SCOPE,
            NO_CONVO,
        )


# Dictionary to hold DB connections per tenant
TENANT_DBS = {}
TENANT_SQL_AGENTS = {}


def init_sql_agent(state: dict, llm):
    """Initialize SQLDatabase and SQL Agent using db_uri from state."""
    tenant_id = state.get("tenant_id", "default")
    conversation_id = state.get("conversation_id", "unknown")
    db_uri = state.get("db_uri")  # <-- fetch db_uri from state
    if db_uri == "ayuladb":
        db_uri = DB_URI # Fixed legacy reference
    log_info(f"The ule of sql {db_uri} ", tenant_id, conversation_id)

    if not db_uri:
        log_error(
            f"[{tenant_id}] No db_uri found in state.", tenant_id, conversation_id
        )
        return None

    try:
        db = SQLDatabase.from_uri(db_uri)
        log_info(
            f"[{tenant_id}] SQLDatabase connected to RE {db_uri} successfully.",
            tenant_id,
            conversation_id,
        )
        # --- Log dialect ---
        log_info(f"[{tenant_id}] Dialect RE: {db.dialect}", tenant_id, conversation_id)

        # --- Log usable tables ---
        try:
            usable_tables = db.get_usable_table_names()
            log_info(
                f"[{tenant_id}] Available tables RE: {usable_tables}",
                tenant_id,
                conversation_id,
            )
        except Exception as e:
            log_warning(
                f"[{tenant_id}] Could not retrieve usable tables: {e}",
                tenant_id,
                conversation_id,
            )
            usable_tables = []

        # --- Initialize toolkit and agent ---

        # Use a LangChain-compatible OllamaService for the SQL toolkit
        ollama_llm = OllamaService(
            base_url=OLLAMA_BASE_URL,
            username=OLLAMA_USERNAME,
            password=OLLAMA_PASSWORD,
            model=OLLAMA_MODEL
        )
        
        toolkit = SQLDatabaseToolkit(db=db, llm=ollama_llm)
        tools = toolkit.get_tools()
        for tool_item in tools:
            log_info(
                f"[{tenant_id}] Tool {tool_item.name}: {tool_item.description}",
                tenant_id,
                conversation_id,
            )

        # SQL_SYSTEM_PROMPT = f"""
        # You are an agent designed to interact with a SQL database. Given an input question,
        # create a syntactically correct {db.dialect} query, execute it, and return the answer.
        # - Query only necessary columns.
        # - Double-check your query before execution.
        # - DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP).
        # - ALWAYS look at the tables first to understand the schema.
        # - Limit your query to at most 5 results.
        # """

        SQL_SYSTEM_PROMPT = """
You are an agent designed to interact with a SQL database. Given an input question,
create a syntactically correct {db.dialect} query, execute it, and return the answer.

- Query only necessary columns.
- DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP).
- **CRITICAL**: ONLY query columns that contain simple text or numerical data. Avoid querying columns that contain complex types like JSON, JSONB, or Arrays, as they cause internal errors.
- Double-check your query before execution.
- ALWAYS look at the tables first to understand the schema.
- Limit your query to at most 5 results.
"""
        agent = create_agent(llm, tools, system_prompt=SQL_SYSTEM_PROMPT)
        log_info(
            f"[{tenant_id}] SQL Agent initialized successfully.",
            tenant_id,
            conversation_id,
        )
        # ==================================
        # 📦 Standard Library Imports
        # ==================================

        # ==================================
        # 📦 Third-Party Libraries (General)
        # ==================================

        # ==================================
        # 📦 PDF & Document Processing
        # ==================================

        # ==================================
        # 📦 Database & ORM
        # ==================================

        # ==================================
        # 🌐 Django Configuration
        # ==================================

        # ==================================
        # 📦 LangChain Core & Messages
        # ==================================
        from langchain_core.messages import (
            AIMessage,
            HumanMessage,
            SystemMessage,
            ToolMessage,
            AnyMessage,
        )

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

        # ==================================
        # 🤖 LangChain Agents & Tools
        # ==================================

        # ==================================
        # 🚀 LLM Providers
        # ==================================

        # ==================================
        # 📊 LangGraph Core
        # ==================================

        # ==================================
        # 🎨 Display/Notebook Utilities
        # ==================================

        # ==================================
        # 🔧 Custom Imports
        # ==================================

        load_dotenv()
        TENANT_SQL_AGENTS[tenant_id] = agent
        TENANT_DBS[tenant_id] = db
        return agent

    except Exception as e:
        log_error(
            f"[{tenant_id}] Error initializing SQL Agent: {e}",
            tenant_id,
            conversation_id,
        )
        return None


@tool(
    "sql_query_tool",
    description="Useful for answering questions requiring data from a SQL database (e.g., 'How many users are there?'). Input should be a natural language question.",
)
def sql_query_tool(query: str, state: dict) -> dict:
    """Executes a SQL query using the pre-initialized SQL agent and returns the result."""
    tenant_config = state.get("tenant_config", {})
    tenant_id = tenant_config.get("tenant_id", "unknown")
    conversation_id = state.get("conversation_id", "unknown")
    db_uri = state.get("db_uri")

    if not db_uri:
        log_warning(
            "DB URI is empty. Returning 'Db tool not available'.",
            tenant_id,
            conversation_id,
        )
        return {"sql_result": "Db tool not available"}

    log_info(f"sql_query_tool invoked with query {query}", tenant_id, conversation_id)

    agent = TENANT_SQL_AGENTS.get(tenant_id)
    if not agent:
        log_warning(
            f"Initializing SQL agent for tenant {tenant_id}", tenant_id, conversation_id
        )
        return {
            "sql_result": f"Error: SQL Agent not initialized for tenant {tenant_id}."
        }

    try:
        response_generator = agent.stream(
            {"messages": [HumanMessage(content=query)]}, stream_mode="values"
        )

        full_response_content = []
        for chunk in response_generator:
            if "messages" in chunk and chunk["messages"]:
                content = chunk["messages"][-1].content
                if content:
                    full_response_content.append(content)

        result = (
            "\n".join(full_response_content)
            if full_response_content
            else "No response from SQL agent."
        )
        log_info(f"SQL query result: {result}", tenant_id, conversation_id)
        return {"sql_result": result}

    except Exception as e:
        return {"sql_result": f"Error executing SQL query: {e}"}


@tool(
    "sql_query_tool",
    description="Useful for answering questions requiring data from a SQL database (e.g., 'How many users are there?'). Input should be a natural language question.",
    #   args_schema=ToolInput # Apply the schema
)
def sql_query_toolv1(query: str, state: dict) -> dict:
    """Executes a SQL query using the pre-initialized SQL agent and returns the result."""
    query = query
    if not SQL_AGENT:
        return {"sql_result": "Error: SQL Agent not initialized."}
    try:
        response_generator = SQL_AGENT.stream(
            {"messages": [HumanMessage(content=query)]}, stream_mode="values"
        )
        full_response_content = []
        for chunk in response_generator:
            if "messages" in chunk and chunk["messages"]:
                content = chunk["messages"][-1].content
                if content:
                    full_response_content.append(content)

        result = (
            "\n".join(full_response_content)
            if full_response_content
            else "No response from SQL agent."
        )
        # return {"sql_result": result}
        # return {"type": "sql_result", "content": result}
        return {"sql_result": result} # Changed from set to dict

    except Exception as e:
        return {"sql_result": f"Error executing SQL query: {e}"}


@tool(
    "pdf_retrieval_tool",
    description="Useful for answering questions from the orgabisation's internal knowledge base (PDFs). Input should be a specific question.",
    #  args_schema=ToolInput # Apply the schema
)
def pdf_retrieval_tool(query: str, state: dict) -> dict:
    """
    Performs a document query using the pre-initialized FAISS vector store.

    Returns:
        dict: A dictionary containing 'pdf_content'. This will hold the search
              results on success, or a structured error message on failure.
    """

    if "state" in state:
        state = state["state"]

    tenant_id = "unknown"
    conversation_id = "unknown"

    if isinstance(state, str):
        try:
            state = json.loads(state)
            log_info(
                "State JSON decoded for pdf_retrieval_tool successfully.",
                "unknown",
                "unknown",
            )

        except json.JSONDecodeError as e:
            log_error(
                f"Invalid input format. JSON decode failed: {e}",
                tenant_id,
                conversation_id,
            )
            return {
                "pdf_content": "!!ERROR!! CODE:PDF-4001 MESSAGE:Invalid input format (expected dictionary/JSON) for PDF search."
            }
    user_query = query.strip()
    # Extract Contextual IDs for Logging
    tenant_config = state.get("tenant_config", {})
    # user_query = state.get("user_query", "").strip()
    tenant_id = tenant_config.get("tenant_id", "unknown")
    conversation_id = state.get("conversation_id", "unknown")
    vector_store_path = state.get("vector_store_path")
    log_info(f"retrieve_from_pdf tool invoked with query {query}", tenant_id, tenant_id)
    # log_info("search_pdf tool invoked", tenant_id, conversation_id)

    # 2. Handle missing query
    if not user_query:
        log_warning(
            "No user query provided for PDF search.", tenant_id, conversation_id
        )
        return {
            "pdf_content": "!!ERROR!! CODE:PDF-4002 MESSAGE:No user query provided for PDF search."
        }

    # 3. Handle missing vector store path
    if not vector_store_path:
        log_error(
            "Missing vector_store_path in state. Cannot search.",
            tenant_id,
            conversation_id,
        )
        return {
            "pdf_content": "!!ERROR!! CODE:PDF-4003 MESSAGE:Vector store path not provided in state. Index is unreachable."
        }

    log_debug(f"Search Path: {vector_store_path}", tenant_id, conversation_id)

    try:
        # 4. LOAD FAISS Index
        log_info("Attempting to load FAISS index.", tenant_id, conversation_id)
        vector_store = FAISS.load_local(
            folder_path=vector_store_path,
            embeddings=embeddings,
            allow_dangerous_deserialization=True,
        )

        # 5. Check Index Count
        search_count = vector_store.index.ntotal
        log_info(
            f"FAISS index loaded successfully. Vector count: {search_count}",
            tenant_id,
            conversation_id,
        )

        if search_count == 0:
            log_warning(
                "Vector store is empty (0 documents).", tenant_id, conversation_id
            )
            return {
                "pdf_content": "!!ERROR!! CODE:PDF-4004 MESSAGE:Vector store loaded successfully but is empty (0 documents)."
            }

        # 6. Perform Similarity Search
        log_info(
            f"Performing similarity search for query: '{user_query[:50]}...'",
            tenant_id,
            conversation_id,
        )
        docs = vector_store.similarity_search(user_query, k=3)
        results_text = []
        sources = set()
        # content = "\n\n".join([doc.page_content for doc in results])
        log_info(
            f"Raw Output of Similarity Search : '{user_query[:50]}...'",
            tenant_id,
            conversation_id,
        )
        log_info(
            f"Full Raw Output of Similarity Search : '{user_query}...'",
            tenant_id,
            conversation_id,
        )
        for doc in docs:
            results_text.append(doc.page_content)
            source_file = os.path.basename(
                doc.metadata.get("source", "General Document")
            )
            sources.add(source_file)

        formatted_result = "\n\n".join(results_text)

        log_debug(
            f"PDF search returned {len(formatted_result)} results.",
            tenant_id,
            conversation_id,
        )
        # return {"pdf_content": formatted_content}
        # return {"type": "pdf_content", "content": formatted_content}
        # return {formatted_content}
        # We return a structured string that the LLM can easily see sources from
        return {"pdf_content": formatted_result, "source_documents": list(sources)}

    except Exception as e:
        log_error(f"PDF Retrieval Error: {str(e)}", tenant_id, conversation_id)
        return {"pdf_content": f"!!ERROR!! CODE:PDF-5001 MESSAGE: {str(e)}"}


@tool("web_search_tool")
def web_search_tool(query: str, state: dict) -> dict:
    """
    Performs web search using Tavily.

    Returns:
        dict: A dictionary containing 'web_content'. This will hold the search
              results on success, or a structured error message on failure.
    """

    log_info("retrieve_from_web tool invoked", "unknown", "unknown")
    if "state" in state:
        state = state["state"]
    user_query = state.get("user_query", "")
    tenant_config = state.get("tenant_config", {})
    tenant_id = tenant_config.get("tenant_id", "unknown")
    conversation_id = state.get("conversation_id", "unknown")

    log_info("search_web tool invoked", tenant_id, conversation_id)

    # 1. Collect priority domains from config
    priority_domains = []
    for field in ["tenant_knowledge_base", "tenant_website"]:
        url = tenant_config.get(field)
        if url:
            try:
                domain = urlparse(url).netloc
                if domain and domain not in priority_domains:
                    priority_domains.append(domain)
            except Exception:
                continue

    # 2. Step 1: Targeted Search (Restricted to priority domains)
    search_results = []
    source_label = "GENERAL SEARCH"  # Default label
    if priority_domains:
        log_info(
            f"Step 1: Searching priority domains {priority_domains}",
            tenant_id,
            conversation_id,
        )
        kb_tool = TavilySearch(
            max_results=5, include_domains=priority_domains, search_depth="advanced"
        )

        try:
            search_results = kb_tool.invoke({"query": user_query})
            if search_results:
                source_label = "TENANT WEBSITE/KNOWLEDGE_BASE"  # Tag as authoritative
        except Exception as e:
            log_warning(f"Priority search failed: {e}", tenant_id, conversation_id)

    # 3. Step 2: Fallback Logic (General search if zero results found)
    if not search_results:
        log_info(
            "Step 2: No results found in KB/Website. Falling back to general web search.",
            tenant_id,
            conversation_id,
        )
        general_tool = TavilySearch(max_results=5, search_depth="advanced")
        try:
            search_results = general_tool.invoke({"query": user_query})
            source_label = "GENERAL"  # Tag as external
        except Exception as e:
            log_error(f"Fallback search failed: {e}", tenant_id, conversation_id)

    # 4. Format Output
    # Extract results from Tavily response (handle both dict and error cases)
    if isinstance(search_results, dict) and "results" in search_results:
        results_list = search_results["results"]
    elif isinstance(search_results, list):
        results_list = search_results
    else:
        results_list = []
    
    # Format Output with Source Weighting Metadata
    formatted_parts = []
    for res in results_list:
        if isinstance(res, dict) and 'url' in res and 'content' in res:
            part = (
                f"--- SOURCE TYPE: {source_label} ---\n"
                f"URL: {res['url']}\n"
                f"CONTENT: {res['content']}\n"
            )
            formatted_parts.append(part)
    
    return {
        "web_content": "\n".join(formatted_parts) if formatted_parts else "!!ERROR!! CODE:WEB-4002 MESSAGE:No valid search results found.",
        "type": "web_search",
        "source_documents": source_label.lower(),
        "source_labels": [f"web_search_{source_label.lower()}"],
    }


tools = [sql_query_tool, pdf_retrieval_tool, web_search_tool]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)
# NOTE: ChatOllama is now used for both chat and tool calling


def get_llm_instancev1(llm_config=None):
    """
    Returns an LLM instance based on the provided configuration or global DB setting.
    """
    if not llm_config:
        db_temp = SessionLocal()
        try:
            llm_config = db_temp.query(LLM).first()
        finally:
            db_temp.close()

    # Default to initialized model_with_tools if no config found or name is unknown
    if not llm_config:
        return model_with_tools

    name = llm_config.name.lower()
    if name == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        model_name = llm_config.model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        
        # Instantiate Gemini
        llm_instance = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0,
            convert_system_message_to_human=True 
        )
        return llm_instance.bind_tools(tools)
    
    elif name == "ollama":
        model_name = llm_config.model or OLLAMA_MODEL
        llm_instance = OllamaService(
            base_url=OLLAMA_BASE_URL,
            username=OLLAMA_USERNAME,
            password=OLLAMA_PASSWORD,
            model=model_name
        )
        return llm_instance.bind_tools(tools)
    
    return model_with_tools


def get_llm_instance(llm_config=None):
    """
    Returns an LLM instance based on the provided configuration or global DB setting.
    
    Supported LLM types:
    - gemini: Google Gemini API
    - ollama: Local Ollama instance
    - ollama_cloud: Ollama Cloud API (requires OLLAMA_API_KEY)
    """
    # If explicit config passed, use it. Otherwise fetch global if needed.
    # Note: 'llm_config' here is expected to be an SQLAlchemy object or None.
    
    if not llm_config:
        db_temp = SessionLocal()
        try:
            llm_config = db_temp.query(LLM).first()
        finally:
            db_temp.close()

    # Default to initialized model_with_tools if no config found or name is unknown
    if not llm_config:
        return model_with_tools

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
        return llm_instance.bind_tools(tools)
    
    elif name == "ollama_cloud":
        # Use ollama_cloud as a special sentinel value
        logger.info("🌐 Initializing Ollama Cloud LLM instance")
        llm_instance = OllamaService(
            base_url=OLLAMA_BASE_URL,  # Not used for cloud, but required by constructor
            username=OLLAMA_USERNAME,  # Not used for cloud
            password=OLLAMA_PASSWORD,  # Not used for cloud
            model="ollama_cloud"  # Special sentinel value triggers cloud API
        )
        return llm_instance.bind_tools(tools)
    
    elif name == "ollama":
        model_name = llm_config.model or OLLAMA_MODEL
        llm_instance = OllamaService(
            base_url=OLLAMA_BASE_URL,
            username=OLLAMA_USERNAME,
            password=OLLAMA_PASSWORD,
            model=model_name
        )
        return llm_instance.bind_tools(tools)
    
    return model_with_tools


def decide(state: State) -> str:
    """
    Decides the next processing node based on the workflow state.

    This node typically handles explicit overrides or dynamic routing logic.
    """

    # Safely extract context IDs with fallbacks
    tenant_id = state.get("tenant_config", {}).get("tenant_id", "unknown")
    conversation_id = state.get("conversation_id", "unknown")

    log_info("Decide node activated", tenant_id, conversation_id)

    # 1. Check for a dedicated "next_node" override set by a previous step
    # NOTE: Assuming the correct intended string value was "summarize" or a flag.
    # If the logic is to check a specific value set in the state, use that value.
    # Based on the structure, we assume it checks a flag or the output of a prior router.

    summarization_flag = state.get("summarization_request", False)
    log_info(
        f"Payload of Summarization {summarization_flag}", tenant_id, conversation_id
    )

    # 1. Check for a dedicated "next_node" override set by a previous step
    # NOTE: Assuming the correct intended string value was "summarize" or a flag.
    # If the logic is to check a specific value set in the state, use that value.
    # Based on the structure, we assume it checks a flag or the output of a prior router.

    if summarization_flag != "false":  # ✅ clean boolean check
        log_info(
            "Condition met: Routing to summarize workflow.", tenant_id, conversation_id
        )
        # return {"type": "router", "next_node": "summarize"}
        return {"type": "router", "next_node": "summarize"}
    else:
        log_info(
            "No explicit routing override detected. Routing to RAG.",
            tenant_id,
            conversation_id,
        )
        return {"next_node": "llm_call"} # Removed 'type' key to match graph expectations if any


def should_continue(state: State) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    tenant_id = state.get("tenant_config", {}).get("tenant_id", "unknown")
    conversation_id = state.get("conversation_id", "unknown")
    log_info("Evaluating whether to continue or stop.", tenant_id, conversation_id)

    messages = state.get("messages", [])
    if not messages:
        return "review_node"
    # last_message = messages[-1]
    # FIX: Find the last AIMessage specifically
    last_message = next(
        (m for m in reversed(messages) if isinstance(m, AIMessage)), None
    )
    log_debug(f"Last LLM message: {last_message}", tenant_id, conversation_id)

    if not last_message or not getattr(last_message, "tool_calls", None):
        log_info("LLM made no tool calls. Ending workflow.", tenant_id, conversation_id)
        return "review_node"

    log_info(
        "LLM made tool calls. Continuing to tool node.", tenant_id, conversation_id
    )
    return "tool_node"

    # # If the LLM makes a tool call, then perform an action
    # if last_message.tool_calls:
    #     log_info( "LLM made tool calls. Continuing to tool node.",tenant_id, conversation_id, )
    #     return "tool_node"
    # else:
    #     log_info( "LLM made no tool calls. Ending workflow.",tenant_id, conversation_id, )
    #     return "review_node"


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

        log_info(
            f"Executed {len(new_messages)} tool calls.", tenant_id, conversation_id
        )

        # Return both the messages and the updated content fields
        return {"messages": new_messages, **state_updates}

    #     # --- FIX: Inject the required 'state' argument manually for the PDF tool ---
    #     if tool.name:
    #         # The tool function is expected to have been updated to accept 'state: dict'
    #         # as an argument alongside the LLM's arguments ('query').
    #         log_debug(f"Injecting current state into arguments for {tool.name}", tenant_id, conversation_id)
    #         tool_args['state'] = state  # Inject the full state dictionary
    #         log_debug(f"REvised tool arguments for {tool_args}", tenant_id, conversation_id)

    #         # Assuming 'pdf_retrieval_tool' now accepts (query: str, state: dict)

    #     # 3. Invoke the tool with the augmented arguments
    #     observation = tool.invoke(tool_args)
    #     log_debug(f"Injecting revised observation  state into arguments for {observation}", tenant_id, conversation_id)
    #     # 4. Append the result as a ToolMessage
    #     result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))

    # log_info("Tool calls executed", tenant_id, conversation_id)
    # log_debug(f"Tool results: {result}", tenant_id, conversation_id)
    # # log_debug(f"Full state after tool execution: {state}", tenant_id, conversation_id) # Removed for brevity/security

    # # 5. Return the list of ToolMessages to update the state
    # return {"messages": result}




async def llm_call(state: State) -> dict:
    """LLM decides whether to call a tool or not"""
    log_info(
        f"LLM call/AGENT NODE initiated:{state.get('llm_calls')}.", "unknown", "unknown"
    )
    if "tenant_config" not in state:
        log_error(
            "Critical state error: 'tenant_config' is missing.", "unknown", "unknown"
        )
        return {
            "error": "!!ERROR!! CODE:GEN-4001 MESSAGE:Missing critical configuration data in state.",
            "http_status": 400,
        }

    # --- Extract Configuration ---
    tenant_config = state["tenant_config"]
    tenant_id = tenant_config.get("tenant_id", "unknown")
    tenant_name = tenant_config.get("tenant_name", "the Bank")
    conversation_id = state.get("conversation_id", "unknown")

    # New Dynamic Fields including Threshold
    is_handoff_allowed = tenant_config.get("is_hum_agent_allow", True)
    conf_level = tenant_config.get("conf_level", 40)
    ticket_type = tenant_config.get("ticket_type", ["email", "live chat"])
    message_tone = tenant_config.get("message_tone", "Professional")
    sentiment_threshold = tenant_config.get("sentiment_threshold", 0)  # Default 0
    prompt_template = tenant_config.get("final_answer_prompt", {})

    user_query = state.get("user_query", "").strip()
    context_str = state.get("context", "No additional context provided.")

    tool_context = state.get(
        "context_data", {}
    )  # Assuming a previous node formatted the tool output
    source_files = tool_context.get("source_documents", [])

    # --- Prompt Templates ---

    # Template 1: Human Handoff Allowed

    # --- Prompt Templates ---
    # Enhanced prompt to inform LLM about sentiment scoring
    sentiment_directive = f"Score sentiment from -2 (angry/frustrated) to +2 (very happy). Note: any score below {sentiment_threshold} triggers human intervention."
    # 2. Add specific instructions to the prompt regarding sources
    source_directive = "In your JSON output, populate the 'source' list with the document names provided in the context."
    agent_prompt_handoff = """
You are an AI-powered virtual assistant for {name}. Your goal is to deliver {message_tone}, final, and helpful responses.
Respond with empathy, clarity, and professionalism.




### Directives:
- **Sentiment Analysis**: {sentiment_directive}
- **Source **: {source_directive}
- **Customer Info Queries**: For account balance, address, or transaction history, you MUST first ask the customer to provide their **10-digit NUBAN** account number before proceeding.
- **Tool Usage**: You may call tools when needed:
  * `pdf_retrieval_tool` → bank policies, products, internal knowledge.
  * `sql_query_tool` → customer data, user counts, transaction volumes.
  * `web_search_tool` → general knowledge or up-to-date information.
- **Human Handoff**: If your confidence level is below {conf_level} or context is insufficient, set `"human_assistant": true`.
- **Channels**: Available service channels for this tenant: {ticket_type}.
-confidence_directive = f"Assess your confidence in this answer from 0-100. If it is below {conf_level}, set 'human_assistant' to true."

### Context:
User Question: "{user_query}"
Available Context: {context}

### Output Format:
Return ONLY JSON:
```json
{{
  "answer": "string",
  "sentiment": int,
  "confidence_score": int,
  "ticket": {ticket_type},
  "source": [],
  "human_assistant": bool
}}
    """

    agent_prompt_no_handoff = """
You are an AI assistant for {name}. Tone: {message_tone}. NOTE: No human handoff is allowed. You are the final point of resolution. If your confidence is below {conf_level}, do your best to assist based on tools, but stay polite.


### Directives:
- **Sentiment Analysis**: {sentiment_directive}.
- **Source **: {source_directive}.
- **Customer Info**: For account/transaction history, you MUST ask for a **10-digit NUBAN**.
- **Channels**: Available service channels for this tenant: {ticket_type}.
- **Confidence Scoring**: {confidence_directive}. Even if confidence is low, provide the best possible help.
Context:
User Question: "{user_query}" Available Context: {context}

Output Format:


Return ONLY JSON:
```json
{{
  "answer": "string",
  "sentiment": int,
  "confidence_score": int,
  "ticket": {ticket_type},
  "source": [],
  "human_assistant": false
}}
```
"""

    # --- JSON Output Instructions ---
    json_instructions = f"""
### Output Format:
You MUST return ONLY a valid JSON object. Do not include any text outside the JSON block.
```json
{{
  "answer": "Your response to the user",
  "sentiment": int (-2 to 2),
  "confidence_score": int (0-100),
  "ticket": {ticket_type},
  "source": ["file1.pdf", "file2.pdf"],
  "human_assistant": bool
}}
```
"""

    # --- Logical Selection of Base Template ---
    # Default to schema-aware template
    template = agent_prompt_handoff if is_handoff_allowed else agent_prompt_no_handoff
    
    # If a specific prompt template is provided in the DB, use it, but we'll still append JSON instructions
    if prompt_template and isinstance(prompt_template, str) and prompt_template.strip():
        template = prompt_template
        # Check if the custom template already has JSON instructions; if not, append them
        if '"answer":' not in template:
            template += "\n" + json_instructions

    try:
        # Pre-format directives
        cf_directive = f"Assess your confidence in this answer from 0-100. If it is below {conf_level}, set 'human_assistant' to true."
        log_info(f"Formatting  system prompt template: {template} with tenant configuration", tenant_id, conversation_id)
        SYSTEM_PROMPT = template.format(
            name=tenant_name,
            message_tone=message_tone,
            conf_level=conf_level,
            ticket_type=ticket_type,
            user_query=user_query,
            context=context_str,
            sentiment_directive=sentiment_directive,
            source_directive=source_directive,
            confidence_directive=cf_directive,
        )

        # Final safety check: if JSON instructions aren't in the final prompt, prepend them
        if '"answer":' not in SYSTEM_PROMPT:
            SYSTEM_PROMPT = json_instructions + "\n" + SYSTEM_PROMPT

    except Exception as e:
        log_exception_auto(f"Prompt formatting failed: {e}", tenant_id, conversation_id)
        SYSTEM_PROMPT = f"You are a helpful assistant for {tenant_name}. Answer the user query: {user_query}"

    try:
        # Resolve LLM model dynamically

        prompt_model = get_llm_instance()
        log_info(f"Using LLM model: {type(prompt_model).__name__}", tenant_id, conversation_id)


        # Use prompt_model to allow tool calling

        # Force JSON format for the final answer via prompt + potentially kwargs if supported

        response = await prompt_model.ainvoke(

            [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

        )
        log_info("LLM response received", tenant_id, conversation_id)
        log_debug(f"Raw LLM response: {response}", tenant_id, conversation_id)
    except Exception as e:
        log_exception_auto(f"LLM invocation failed: {e}", tenant_id, conversation_id)
        return {
            "messages": [AIMessage(content="I'm sorry, I'm having trouble connecting to my brain right now.")],
            "leave_application": {
                "answer": "Connection error to AI service.",
                "human_assistant": True
            }
        }

    # --- Tool Call Handling ---
    if response.tool_calls:
        log_info("LLM made tool calls. Routing to tool node.", tenant_id, conversation_id)
        return {"messages": [response]}

    leave_app_data = None
    raw_text = ""
    try:
        content = response.content
        raw_text = content if isinstance(content, str) else str(content)

        # Extract JSON blocks using regex for robustness
        # Handle multiple JSON objects by finding all and attempting the last one first
        json_matches = list(re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", raw_text, re.DOTALL))
        
        cleaned = None
        parsed = None
        
        # Try to parse JSON objects in reverse order (last first, as it's the final answer)
        if json_matches:
            for json_match in reversed(json_matches):
                cleaned = json_match.group(0)
                try:
                    parsed = json.loads(cleaned)
                    # Verify it has expected Answer fields
                    if "answer" in parsed:
                        log_debug(f"Successfully parsed JSON object (attempt {len(json_matches) - json_matches.index(json_match)})", tenant_id, conversation_id)
                        break
                    parsed = None  # Reset if it doesn't look like an answer
                except Exception as e:
                    log_debug(f"Failed to parse JSON object: {e}", tenant_id, conversation_id)
                    parsed = None
                    continue
        
        # Fallback: if no valid JSON with 'answer' found, try markdown fence extraction
        if parsed is None:
            cleaned = raw_text.strip().replace("```json", "").replace("```", "").strip()
            if cleaned and cleaned[0] in ("{", "["):
                try:
                    parsed = json.loads(cleaned)
                except Exception as e:
                    log_error(f"JSON parsing failed despite JSON-like input: {e}. Raw: {repr(cleaned)[:1000]}", tenant_id, conversation_id)
                    parsed = None

        if parsed is None:
            # Fallback: LLM returned plain text or invalid JSON. Wrap it into the
            # expected schema so processing can continue without crashing.
            parsed = {
                "answer": cleaned or raw_text,
                "sentiment": 0.0,
                "confidence_score": 100,
                # ensure we always produce a list for source_type
                "source_type": source_files if source_files else ["GENERAL"],
                "ticket": state.get("ticket_type", []),
                "source": [],
                "human_assistant": False,
            }

        # Standardize fields
        # ensure source_type is a list of uppercase strings
        if source_files:
            parsed["source_type"] = source_files
        else:
            st = parsed.get("source_type", "GENERAL")
            if isinstance(st, list):
                parsed["source_type"] = [str(x).upper() for x in st]
            else:
                parsed["source_type"] = [str(st).upper()]
        
        parsed["sentiment"] = float(parsed.get("sentiment", 0))
        parsed["confidence_score"] = int(parsed.get("confidence_score", 100))
        
        # Ensure ticket is always a list (LLM sometimes returns string like "undefined")
        ticket_value = parsed.get("ticket", [])
        if isinstance(ticket_value, str) or ticket_value == "undefined":
            parsed["ticket"] = state.get("ticket_type", [])
        elif not isinstance(ticket_value, list):
            parsed["ticket"] = state.get("ticket_type", [])
        
        # Apply your Guardrails (Capping confidence, Force handoff)
        if parsed["source_type"] == "GENERAL" and parsed["confidence_score"] > 75:
            parsed["confidence_score"] = 75

        if is_handoff_allowed and (parsed["sentiment"] < sentiment_threshold or parsed["confidence_score"] < conf_level):
            parsed["human_assistant"] = True
            if "connecting you with a human" not in parsed["answer"]:
                parsed["answer"] += " I am connecting you with a human colleague to better assist you."

        leave_app_data = Answer(**parsed).dict()
        log_info("LLM Answer parsed successfully ", tenant_id, conversation_id)
        log_debug(f"Parsed Answer: {leave_app_data}", tenant_id, conversation_id)

    except Exception as e:
        log_error(f"Failed to parse Answer: {e}. Raw Text: {repr(raw_text)[:1000]}", tenant_id, conversation_id)
        leave_app_data = {
            "answer": "I'm having trouble processing that right now. Let me get a human to help.",
            "sentiment": 0.0,
            "confidence_score": 0,
            "source_type": "ERROR",
            "ticket": state.get("ticket_type", []),
            "source": [],
            "human_assistant": True,
        }

    # IMPORTANT: We save the processed dict into leave_application here
    return {
        "messages": [AIMessage(content=leave_app_data["answer"])],
        "leave_application": leave_app_data,
    }


# Removed legacy llm_callv1 and tool_nodev1


# return {
#         "messages": response,
#         "llm_calls": state.get("llm_calls", 0) + 1,
#         "current_answer": answer_obj
#     }


# return {"messages": response,
#         "llm_calls": state.get("llm_calls", 0) + 1,}


def review_node(state: State) -> dict:
    """
    Acts as a bridge. The data is already parsed in llm_call.
    We just ensure leave_application is populated.
    """
    
    
    tenant_id = state.get("tenant_id", "unknown")
    conversation_id = state.get("conversation_id", "unknown")
    messages = state.get("messages", [])
    
    data = state.get("leave_application")
    if not data:
        # Fallback if somehow llm_call skipped the parsing logic
        return {"leave_application": {"answer": "Manual Handoff", "human_assistant": True}, "next_node": "summarize", "type": "router",}
    return {"leave_application": data, "next_node":  END, "type": "router",}


    # if not messages:
    #     log_error(
    #         "No messages found in state during review node.", tenant_id, conversation_id
    #     )
    #     return {"leave_application": {"answer": "Error", "human_assistant": True}}

    # last_msg = messages[-1]
    # raw_text = (
    #     last_msg.content[0]["text"]
    #     if isinstance(last_msg.content, list)
    #     else last_msg.content
    # )
    # log_info(
    #     f"Review node processing last message: {raw_text}", tenant_id, conversation_id
    # )

    # leave_app_data = None
    # try:
    #     # Attempt to parse JSON
    #     cleaned = re.sub(
    #         r"^```json|```$", "", raw_text.strip(), flags=re.MULTILINE
    #     ).strip()
    #     parsed = json.loads(cleaned)
    #     parsed.setdefault("confidence_score", 100)
    #     parsed.setdefault("source_type", "GENERAL")
    #     leave_app_data = Answer(**parsed).dict()
    #     log_info(
    #         f"Parsed leave application data: {leave_app_data}",
    #         tenant_id,
    #         conversation_id,
    #     )
    #     if human_assistant := leave_app_data.get("human_assistant", False):
    #         next_node = "summarize"
    #         log_info(
    #             "Human assistant flag detected in parsed data.",
    #             tenant_id,
    #             conversation_id,
    #         )
    #         log_info(f"Next node determined: {next_node}", tenant_id, conversation_id)
    #     else:
    #         next_node = END
    #         log_info(
    #             "No human assistant flag detected; ending workflow.",
    #             tenant_id,
    #             conversation_id,
    #         )

    # except (json.JSONDecodeError, ValidationError, Exception) as e:
    #     log_error(
    #         f"Failed to parse response into Answer model: {e}",
    #         tenant_id,
    #         conversation_id,
    #     )
    #     # fallback Answer
    #     leave_app_data = Answer(
    #         answer="Sorry, I could not process your request. A human assistant will follow up.",
    #         sentiment=0,
    #         ticket=[],
    #         source=[],
    #         human_assistant=True,
    #     )
    #     next_node = "summarize"

    # return {
    #     "leave_application": leave_app_data,
    #     "next_node": next_node,
    #     "type": "router",
    # }


def extract_message_text(msg):
    # Try to get the content attribute, defaulting to the full string representation of the message
    content = getattr(msg, "content", str(msg))

    if isinstance(content, str):
        # Case 1: Simple string content (most common)
        return content

    elif isinstance(content, list):
        # Case 2: Multimodal content (list of text/image parts)
        text_parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))
            # You may want to log or handle image parts here, e.g., appending a token like "[IMAGE ATTACHED]"
        return " ".join(text_parts)

    else:
        # Case 3: Other unexpected types (e.g., pydantic object, etc.)
        return str(content)


async def summarize_conversation(state: State) -> dict:
    """
    Generates a structured summary of the conversation using an LLM.
    Uses the unified messages list (Human + AI) instead of DB lookup.
    """

    tenant_config = state.get("tenant_config", {})
    tenant_id = tenant_config.get("tenant_id", "unknown")
    conversation_id = state.get("conversation_id", "unknown")

    log_info("Summarize node activated", tenant_id, conversation_id)

    # --- 1. Check for Messages ---
    messages = state.get("messages", [])
    if not messages:
        log_warning("No messages available to summarize.", tenant_id, conversation_id)
        return {
            "error": "!!ERROR!! CODE:SUM-4002 MESSAGE:No messages found in state to summarize.",
            "http_status": 400,
        }

    # --- 2. Build Conversation History ---
    try:
        conversation_history = " ".join(extract_message_text(msg) for msg in messages)
    except Exception as e:
        log_exception_auto(
            f"Failed to flatten messages: {e}", tenant_id, conversation_id
        )
        conversation_history = str(messages)

    log_debug(
        f"Conversation history prepared: {conversation_history}",
        tenant_id,
        conversation_id,
    )

    # --- 3. Prepare Prompt ---
    summarize_prompt_template = tenant_config.get(
        "summary_prompt",
        (
            "Summarize the conversation below, determining sentiment, unresolved issues, "
            "and whether human assistance is required. "
            "Return ONLY using the structured output schema:\n\n"
            "Conversation:\n{conversation_history}\n\n"
            "Schema:\n"
            "- summary: str (concise summary of the conversation)\n"
            "- sentiment: int (-2 very negative to +2 very positive)\n"
            "- unresolved_tickets: List[str] (any unresolved issues)\n"
            "- all_sources: List[str] (sources referenced)\n"
            "- human_assistant: bool (True if escalation to human is required, else False)"
        ),
    )

    try:
        summarize_prompt = summarize_prompt_template.format(
            conversation_history=conversation_history
        )
    except Exception as e:
        log_exception_auto(
            f"Summary prompt format failed: {e}. Falling back to default.",
            tenant_id,
            conversation_id,
        )
        summarize_prompt = (
            f"Summarize the following raw history: {conversation_history}"
        )

    log_debug("Summarization prompt prepared.", tenant_id, conversation_id)

    # --- 4. Invoke LLM ---
    try:
        log_info(
            "Invoking LLM for structured summary generation.",
            tenant_id,
            conversation_id,
        )
        # Use ainvoke for async and ensure content is a string
        # Force JSON format for the summary
        response = await llm.ainvoke(summarize_prompt, format="json")
        content = response.content
        raw_text = content if isinstance(content, str) else str(content)
        cleaned_json_str = raw_text.strip().replace("```json", "").replace("```", "").strip()
        summary_obj = Summary.model_validate_json(cleaned_json_str)

        log_info(
            "LLM successfully returned structured summary.", tenant_id, conversation_id
        )
    except Exception as e:
        log_exception_auto(
            f"LLM invocation failed or structured parsing error: {e}",
            tenant_id,
            conversation_id,
        )
        return {
            "error": "!!ERROR!! CODE:SUM-5002 MESSAGE:LLM failed to generate a valid structured summary response.",
            "http_status": 500,
        }

    # --- 5. Build Metadata ---
    current_answer = state.get("current_answer")
    user_query = state.get("user_query")

    def _get_field(obj, field, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(field, default)
        if hasattr(obj, field):
            return getattr(obj, field, default)
        if hasattr(obj, "model_dump"):
            return obj.model_dump().get(field, default)
        if hasattr(obj, "dict"):
            return obj.dict().get(field, default)
        return default

    metadata = {
        "question": user_query,
        "answer": _get_field(current_answer, "answer", "N/A"),
        "sentiment": _get_field(current_answer, "sentiment", 0),
        "ticket": _get_field(current_answer, "ticket", []),
        "source": _get_field(current_answer, "source", []),
        "human_assistant": _get_field(current_answer, "human_assistant", False),
        "summary": _get_field(summary_obj, "summary", None),
        "summary_sentiment": _get_field(summary_obj, "sentiment", None),
        "summary_unresolved_tickets": _get_field(summary_obj, "unresolved_tickets", None),
        "summary_sources": _get_field(summary_obj, "all_sources", None),
        "summary_human_assistant": _get_field(summary_obj, "human_assistant", None),
    }
    log_debug(f"Summary metadata compiled: {metadata}", tenant_id, conversation_id)
    return {
        "conversation_summary": summary_obj,
        "metadata": metadata,
        "leave_application": metadata,
    }


def build_graph(tenant_id: str, conversation_id: str, checkpointer=None):
    """Builds and compiles the LangGraph workflow for a given tenant and conversation."""

    workflow = StateGraph(State)
    logger.info(f"Building LangGraph for tenant: {tenant_id}, conversation: {conversation_id}")

    # --- Nodes ---
    workflow.add_node("decide", decide)
    workflow.add_node("llm_call", llm_call)
    workflow.add_node("tool_node", tool_node)
    workflow.add_node("review_node", review_node)
    workflow.add_node("summarize", summarize_conversation)

    # --- Routing ---
    workflow.add_edge(START, "decide")
    logger.info(f"Adding edges to LangGraph for tenant: {tenant_id}, conversation: {conversation_id}")
    
    
    workflow.add_conditional_edges(
        "decide",
        lambda state: state.get("next_node"),
        {"summarize": "summarize", "llm_call": "llm_call"},
    )
    logger.info(f"Adding edges to LangGraph for tenant: {tenant_id}, conversation: {conversation_id}")
    workflow.add_conditional_edges(
        "llm_call", should_continue, ["tool_node", "review_node"]
    )
    logger.info(f"Adding edges to LangGraph for tenant: {tenant_id}, conversation: {conversation_id}")
    workflow.add_edge("tool_node", "llm_call")

    logger.info(f"Adding edges to LangGraph for tenant: {tenant_id}, conversation: {conversation_id}")
    workflow.add_conditional_edges(
        "review_node",
        lambda state: state.get("next_node"),
        {"summarize": "summarize", END: END},
    )
    logger.info(f"Adding edges to LangGraph for tenant: {tenant_id}, conversation: {conversation_id}")
    workflow.add_edge("summarize", END)
    logger.info(f"Adding edges to LangGraph for tenant: {tenant_id}, conversation: {conversation_id}")

    logger.info("LangGraph workflow compiled successfully", tenant_id, conversation_id)
    return workflow.compile(checkpointer=checkpointer)


async def process_message(
    message_content: str,
    conversation_id: str,
    tenant_id: str,
    file_path: Optional[str] = None,
    summarization_request: Any = None,
) -> dict:
    """Main function to process user messages using the LangGraph agent."""

    log_info("Starting message processing pipeline", tenant_id, conversation_id)

    db = SessionLocal()
    current_tenant = None
    
    # --- 1. Tenant Configuration ---
    try:
        from sqlalchemy.orm import joinedload
        current_tenant = (
            db.query(Tenant)
            .options(joinedload(Tenant.prompt_template))
            .filter(Tenant.tenant_id == tenant_id)
            .first()
        )
        if not current_tenant:
            log_error("Tenant not found", tenant_id, conversation_id)
            return {"answer": "Error: Tenant config missing.", "metadata": {}}
            
        # Using db_uri if present (idle but still accessible)
        db_url = current_tenant.db_uri

        # --- Global LLM Configuration ---
        global_llm = db.query(LLM).first()
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
        
        log_info(f"Fetching prompts for type: {requested_type}", tenant_id, conversation_id)
        
        # Try to fetch the specific prompt type
        prompt_tpl = db.query(Prompt).filter(Prompt.name == requested_type).first()
        
        # Fallback to 'standard' if not found
        if not prompt_tpl and requested_type != "standard":
            log_info(f"Prompt type '{requested_type}' not found. Falling back to 'standard'.", tenant_id, conversation_id)
            prompt_tpl = db.query(Prompt).filter(Prompt.name == "standard").first()

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
    finally:
        db.close()

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
            logger.info(
                f"Vector store document count: {document_count}",
                tenant_id,
                conversation_id,
            )
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

    # --- 4. Attachment Processing ---
    attached_content = None
    if file_path:
        # (Image and PDF processing logic remains the same as your snippet)
        # ... [Keep your existing PDF/OCR/Image logic here] ...
        pass

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
            "db_uri": db_url,
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
            state={"tenant_id": tenant_id, "db_uri": db_url},
            llm=llm,
        )
        TENANT_SQL_AGENTS[tenant_id] = sql_agent

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
    }

    # --- 8. Graph Execution ---
    async with AsyncSqliteSaver.from_conn_string(checkpoint_file) as saver:
        graph = build_graph(tenant_id, conversation_id, checkpointer=saver)
        try:
            config_dict = {"configurable": {"thread_id": conversation_id}}
            output = await graph.ainvoke(State(**initial_state), config=config_dict)    
            log_info("LangGraph execution completed", tenant_id, conversation_id)
        except Exception as e:
            log_error(f"LangGraph execution failed: {e}", tenant_id, conversation_id)
            raise

    # --- 9. Response Extraction ---
    current_answer = output.get("leave_application")
    # Updated key per your requirement: leave_application instead of submission_result
    metadata = output.get("metadata")

    if current_answer:
        return {
            "answer": current_answer,
            "metadata": metadata,
        }
    else:
        last_message = output.get("messages", [AIMessage(content="Internal error.")])[
            -1
        ]
        fallback = (
            last_message.content
            if isinstance(last_message, AIMessage)
            else str(last_message)
        )
        return {"answer": fallback, "metadata": {}}


def search_pdfv1(state: State):
    """
    Performs a document query using the pre-initialized FAISS vector store.

    Returns:
        dict: A dictionary containing 'pdf_content'. This will hold the search
              results on success, or a structured error message on failure.
    """

    tenant_id = "unknown"
    conversation_id = "unknown"

    # 1. Normalize input and handle JSON decode errors
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except json.JSONDecodeError as e:
            log_error(
                f"Invalid input format. JSON decode failed: {e}",
                tenant_id,
                conversation_id,
            )
            return {
                "pdf_content": "!!ERROR!! CODE:PDF-4001 MESSAGE:Invalid input format (expected dictionary/JSON) for PDF search."
            }

    # Extract Contextual IDs for Logging
    tenant_config = state.get("tenant_config", {})
    user_query = state.get("user_query", "").strip()
    tenant_id = tenant_config.get("tenant_id", "unknown")
    conversation_id = state.get("conversation_id", "unknown")
    vector_store_path = state.get("vector_store_path")

    log_info("search_pdf tool invoked", tenant_id, conversation_id)

    # 2. Handle missing query
    if not user_query:
        log_warning(
            "No user query provided for PDF search.", tenant_id, conversation_id
        )
        return {
            "pdf_content": "!!ERROR!! CODE:PDF-4002 MESSAGE:No user query provided for PDF search."
        }

    # 3. Handle missing vector store path
    if not vector_store_path:
        log_error(
            "Missing vector_store_path in state. Cannot search.",
            tenant_id,
            conversation_id,
        )
        return {
            "pdf_content": "!!ERROR!! CODE:PDF-4003 MESSAGE:Vector store path not provided in state. Index is unreachable."
        }

    log_debug(f"Search Path: {vector_store_path}", tenant_id, conversation_id)

    try:
        # 4. LOAD FAISS Index
        log_info("Attempting to load FAISS index.", tenant_id, conversation_id)
        vector_store = FAISS.load_local(
            folder_path=vector_store_path,
            embeddings=embeddings,
            allow_dangerous_deserialization=True,
        )

        # 5. Check Index Count
        search_count = vector_store.index.ntotal
        log_info(
            f"FAISS index loaded successfully. Vector count: {search_count}",
            tenant_id,
            conversation_id,
        )

        if search_count == 0:
            log_warning(
                "Vector store is empty (0 documents).", tenant_id, conversation_id
            )
            return {
                "pdf_content": "!!ERROR!! CODE:PDF-4004 MESSAGE:Vector store loaded successfully but is empty (0 documents)."
            }

        # 6. Perform Similarity Search
        log_info(
            f"Performing similarity search for query: '{user_query[:50]}...'",
            tenant_id,
            conversation_id,
        )
        results = vector_store.similarity_search(user_query, k=3)
        content = "\n\n".join([doc.page_content for doc in results])

        formatted_content = (
            "--- PDF DOCUMENT CONTEXT START ---\n"
            f"{content}\n"
            "--- PDF DOCUMENT CONTEXT END ---"
        )

        log_debug(
            f"PDF search returned {len(results)} results.", tenant_id, conversation_id
        )
        return {"pdf_content": formatted_content}

    except FileNotFoundError:
        log_error(
            f"FAISS index files not found at {vector_store_path}.",
            tenant_id,
            conversation_id,
        )
        return {
            "pdf_content": "!!ERROR!! CODE:VEC-5002 MESSAGE:FAISS index files not found. The index may not have been created."
        }
    except Exception as e:
        # Catch any other exception (e.g., corrupted index, embedding error during load)
        log_exception_auto(
            f"An unexpected error occurred during FAISS loading or search: {e}",
            tenant_id,
            conversation_id,
        )
        return {
            "pdf_content": "!!ERROR!! CODE:VEC-5003 MESSAGE:Critical error during vector store retrieval or similarity search."
        }


def search_webv1(state: State) -> dict:
    """
    Performs web search using Tavily.

    Returns:
        dict: A dictionary containing 'web_content'. This will hold the search
              results on success, or a structured error message on failure.
    """

    tenant_id = "unknown"
    conversation_id = "unknown"

    # 1. Extract Contextual IDs for Logging
    tenant_config = state.get("tenant_config", {})
    tenant_id = tenant_config.get("tenant_id", "unknown")
    conversation_id = state.get("conversation_id", "unknown")

    log_info("search_web tool invoked", tenant_id, conversation_id)

    try:
        # Determine the primary user query
        # Prioritize 'messages' array (typical LangChain/Agent state), fallback to raw '__arg1'
        user_query = ""
        if "messages" in state and state["messages"]:
            # Get content from the last message
            user_query = state["messages"][-1].content
        elif state.get("__arg1"):
            user_query = state.get("__arg1")

        user_query = user_query.strip()
        attached_content = (state.get("attached_content") or "").strip()

        # 2. Handle missing query
        if not user_query:
            log_warning(
                "No user query provided for web search.", tenant_id, conversation_id
            )
            return {
                "web_content": "!!ERROR!! CODE:WEB-4001 MESSAGE:No user query provided for web search."
            }

        # Construct the final query sent to the search engine
        query = f"User Query: {user_query}"
        if attached_content:
            query += f" | Attached File Content: {attached_content[:100]}..."

        log_debug(
            f"Executing web search with structured query: {query}",
            tenant_id,
            conversation_id,
        )

        # 3. Execute Search
        search = TavilySearch(max_results=2)
        search_docs = search.invoke(input=query)

        if isinstance(search_docs, str):
            try:
                search_docs = json.loads(search_docs)
            except json.JSONDecodeError as e:
                log_exception_auto(
                    f"Web search response is a string but not valid JSON: {e}",
                    tenant_id,
                    conversation_id,
                )
                return {
                    "web_content": "!!ERROR!! CODE:WEB-5002 MESSAGE:Web search tool returned an invalid response format (non-JSON string)."
                }

        # 4. Validate Response Format
        if not isinstance(search_docs, dict) or "results" not in search_docs:
            log_error(
                f"Web search response format is unexpected. Keys found: {list(search_docs.keys()) if isinstance(search_docs, dict) else 'N/A'}",
                tenant_id,
                conversation_id,
            )
            return {
                "web_content": "!!ERROR!! CODE:WEB-5002 MESSAGE:Unexpected response format from web search tool (missing 'results' key)."
            }

        # 5. Format Results
        formatted_docs = "\n\n---\n\n".join(
            f'<Document href="{doc["url"]}">\n{doc["content"]}\n</Document>'
            for doc in search_docs["results"]
        )

        log_tool_usage(state, "search_web")
        log_debug(
            f"Web Search returned {len(search_docs['results'])} documents.",
            tenant_id,
            conversation_id,
        )

        return {"web_content": formatted_docs}

    except Exception as e:
        log_exception_auto(
            f"Critical web search exception: {e}", tenant_id, conversation_id
        )
        return {
            "web_content": "!!ERROR!! CODE:WEB-5001 MESSAGE:Internal error while performing web search."
        }


def rag(state: State) -> State:
    """
    The Retrieval-Augmented Generation (RAG) primary workflow node.

    In a complete implementation, this node would orchestrate the steps:
    1. Retrieve context (via search_pdf or search_web).
    2. Format the prompt with the retrieved context.
    3. Call the Large Language Model (LLM).
    4. Store the response and update conversation history.

    Currently serves as a logging entry point and simply passes the state forward.
    """

    # Safely extract context IDs with fallbacks
    tenant_id = state.get("tenant_config", {}).get("tenant_id", "unknown")
    conversation_id = state.get("conversation_id", "unknown")

    # 1. Log activation
    log_info("RAG node activated", tenant_id, conversation_id)

    # 2. Log full state for debugging initial inputs
    # log_debug(f"State entering RAG: {state}", tenant_id, conversation_id)

    # 3. No operation is performed, so we return the state unchanged.
    return state


def landing(state: State) -> dict:
    tenant_id = state.get("tenant_config", {}).get("tenant_id", "unknown")
    conversation_id = state.get("conversation_id", "unknown")
    summarization_flag = state.get("summarization_request", False)
    log_info(
        f"Payload of Summarization {summarization_flag}", tenant_id, conversation_id
    )

    if summarization_flag != "false":  # ✅ clean boolean check
        log_info(
            "Condition met: Routing to summarize workflow.", tenant_id, conversation_id
        )
        return {"next_node": "summarize"}

    summarization_flag = state.get("summarization_request")
    log_info(
        f"Payload of Summarization {summarization_flag}", tenant_id, conversation_id
    )

    # if summarization_flag != "false":  # ✅ clean boolean check
    if summarization_flag:  # ✅ clean boolean check
        log_info(
            "Condition met: Routing to summarize workflow.", tenant_id, conversation_id
        )
        return {"next_node": "summarize"}
    else:
        log_info(
            "Condition not met: Routing to RAG workflow.", tenant_id, conversation_id
        )
        return {"next_node": "rag"}


# Assuming 'State', 'HumanMessage', 'AIMessage', 'llm', and 'Answer' (the Pydantic schema for structured output)
# and logging functions are imported and available.
async def generate_final_answer(state: State) -> dict:
    """
    Generates the final structured answer using retrieved context and user query.
    """

    if "tenant_config" not in state:
        log_error(
            "Critical state error: 'tenant_config' is missing.", "unknown", "unknown"
        )
        return {
            "error": "!!ERROR!! CODE:GEN-4001 MESSAGE:Missing critical configuration data in state.",
            "http_status": 400,
        }

    tenant_config = state["tenant_config"]
    tenant_id = tenant_config.get("tenant_id", "unknown")
    conversation_id = state.get("conversation_id", "unknown")

    log_info("Final answer node activated", tenant_id, conversation_id)

    # --- Normalize messages list ---
    messages = state.get("messages", [])

    # --- Determine user query ---
    user_query = state.get("user_query")
    if not user_query and messages:
        try:
            user_query = next(
                (
                    msg.content
                    for msg in reversed(messages)
                    if isinstance(msg, HumanMessage)
                ),
                None,
            )
            if not user_query:
                user_query = "The user asked an unrecoverable question."
                log_warning(
                    "No human message found in state history.",
                    tenant_id,
                    conversation_id,
                )
        except Exception:
            user_query = "The user asked an unrecoverable question."
            log_warning(
                "Failed to parse messages history for user_query.",
                tenant_id,
                conversation_id,
            )

    if not user_query:
        log_error(
            "Failed to determine a user query from state.", tenant_id, conversation_id
        )
        return {
            "error": "!!ERROR!! CODE:GEN-4002 MESSAGE:Cannot identify user query from state for final answer generation.",
            "http_status": 400,
        }

    log_debug(f"User query finalized: {user_query}", tenant_id, conversation_id)

    # --- Aggregate context ---
    context_parts = []
    for key, label in [
        ("pdf_content", "PDF Content"),
        ("web_content", "Web Content"),
        ("attached_content", "Attached Content"),
    ]:
        content = state.get(key)
        if isinstance(content, str) and content.startswith("!!ERROR!!"):
            log_warning(
                f"Skipping failed context: {key} reported an error.",
                tenant_id,
                conversation_id,
            )
            continue
        if content:
            context_parts.append(f"{label}:\n{content}")

    context = (
        "\n\n".join(context_parts)
        if context_parts
        else "No additional context was retrieved."
    )

    # --- Prepare prompt ---
    default_prompt = (
        "You are a polite, professional AI assistant. Respond to the user's question using ONLY the provided context if available.\n"
        "User Question: {user_query}\nContext: {context}\nReturn the answer in the required JSON schema."
    )

    prompt_template = tenant_config.get("final_answer_prompt", default_prompt)
    tenant_name = tenant_config.get("tenant_name", "ATB")

    try:
        prompt = prompt_template.format(
            user_query=user_query, context=context, name=tenant_name
        )
    except Exception as e:
        log_exception_auto(
            f"Custom prompt formatting failed: {e}", tenant_id, conversation_id
        )
        try:
            prompt = default_prompt.format(user_query=user_query, context=context)
            log_warning(
                "Custom prompt formatting failed; fell back to default prompt.",
                tenant_id,
                conversation_id,
            )
        except Exception:
            log_exception_auto(
                "FATAL: Default prompt formatting also failed.",
                tenant_id,
                conversation_id,
            )
            return {
                "error": "!!ERROR!! CODE:GEN-5001 MESSAGE:Critical failure during prompt template formatting.",
                "http_status": 500,
            }

    # --- Invoke LLM ---
    try:
        log_info(
            "Invoking LLM for structured final answer generation.",
            tenant_id,
            conversation_id,
        )
        # Fix: Use manual parsing as with_structured_output is not supported
        # Use ainvoke for async and ensure content is a string
        response = await llm.ainvoke(prompt)
        content = response.content
        raw_text = content if isinstance(content, str) else str(content)
        cleaned_json_str = raw_text.strip().replace("```json", "").replace("```", "").strip()
        final_answer_obj = Answer.model_validate_json(cleaned_json_str)

        if final_answer_obj and hasattr(final_answer_obj, "answer"):
            ai_msg = AIMessage(content=final_answer_obj.answer)
            # messages.append(ai_msg)
            messages = state["messages"] + [AIMessage(content=final_answer_obj.answer)]
            log_info(
                f"Final Answer re oh {final_answer_obj.answer}.",
                tenant_id,
                conversation_id,
            )
            log_info(
                f"Successfully appended state message{messages}.",
                tenant_id,
                conversation_id,
            )

    except Exception as e:
        log_exception_auto(
            f"LLM invocation failed or structured parsing error: {e}",
            tenant_id,
            conversation_id,
        )
        # fallback Answer
        final_answer_obj = Answer(
            answer="Sorry, I could not process your request. A human assistant will follow up.",
            sentiment=0,
            ticket=[],
            source=[],
            human_assistant=True,
        )
        messages = state["messages"] + [AIMessage(content=final_answer_obj.answer)]
        error_code = (
            "GEN-5003"
            if "parser" in str(e).lower() or "json" in str(e).lower()
            else "GEN-5002"
        )
        error_message = "LLM failed to generate a valid structured response."
        return {
            "error": f"!!ERROR!! CODE:{error_code} MESSAGE:{error_message}",
            "http_status": 500,
        }

    # --- Success return ---
    log_info(
        "Successfully generated final structured answer.", tenant_id, conversation_id
    )
    return {"final_answer": final_answer_obj, "messages": messages}








async def llm_callv2(state: State) -> dict:
    """LLM decides whether to call a tool or not"""
    log_info(
        f"LLM call/AGENT NODE initiated:{state.get('llm_calls')}.", "unknown", "unknown"
    )
    if "tenant_config" not in state:
        log_error(
            "Critical state error: 'tenant_config' is missing.", "unknown", "unknown"
        )
        return {
            "error": "!!ERROR!! CODE:GEN-4001 MESSAGE:Missing critical configuration data in state.",
            "http_status": 400,
        }

    # --- Extract Configuration ---
    tenant_config = state["tenant_config"]
    tenant_id = tenant_config.get("tenant_id", "unknown")
    tenant_name = tenant_config.get("tenant_name", "the Bank")
    conversation_id = state.get("conversation_id", "unknown")

    # New Dynamic Fields including Threshold
    is_handoff_allowed = tenant_config.get("is_hum_agent_allow", True)
    conf_level = tenant_config.get("conf_level", 40)
    ticket_type = tenant_config.get("ticket_type", ["email", "live chat"])
    message_tone = tenant_config.get("message_tone", "Professional")
    sentiment_threshold = tenant_config.get("sentiment_threshold", 0)  # Default 0
    prompt_template = tenant_config.get("final_answer_prompt", {})

    user_query = state.get("user_query", "").strip()
    context_str = state.get("context", "No additional context provided.")

    tool_context = state.get(
        "context_data", {}
    )  # Assuming a previous node formatted the tool output
    source_files = tool_context.get("source_documents", [])

    # --- Prompt Templates ---

    # Template 1: Human Handoff Allowed

    # --- Prompt Templates ---
    # Enhanced prompt to inform LLM about sentiment scoring
    sentiment_directive = f"Score sentiment from -2 (angry/frustrated) to +2 (very happy). Note: any score below {sentiment_threshold} triggers human intervention."
    # 2. Add specific instructions to the prompt regarding sources
    source_directive = "In your JSON output, populate the 'source' list with the document names provided in the context."
    agent_prompt_handoff = """
You are an AI-powered virtual assistant for {name}. Your goal is to deliver {message_tone}, final, and helpful responses.
Respond with empathy, clarity, and professionalism.




### Directives:
- **Sentiment Analysis**: {sentiment_directive}
- **Source **: {source_directive}
- **Customer Info Queries**: For account balance, address, or transaction history, you MUST first ask the customer to provide their **10-digit NUBAN** account number before proceeding.
- **Tool Usage**: You may call tools when needed:
  * `pdf_retrieval_tool` → bank policies, products, internal knowledge.
  * `sql_query_tool` → customer data, user counts, transaction volumes.
  * `web_search_tool` → general knowledge or up-to-date information.
- **Human Handoff**: If your confidence level is below {conf_level} or context is insufficient, set `"human_assistant": true`.
- **Channels**: Available service channels for this tenant: {ticket_type}.
-confidence_directive = f"Assess your confidence in this answer from 0-100. If it is below {conf_level}, set 'human_assistant' to true."

### Context:
User Question: "{user_query}"
Available Context: {context}

### Output Format:
Return ONLY JSON:
```json
{{
  "answer": "string",
  "sentiment": int,
  "confidence_score": int,
  "ticket": {ticket_type},
  "source": [],
  "human_assistant": bool
}}
    """

    agent_prompt_no_handoff = """
You are an AI assistant for {name}. Tone: {message_tone}. NOTE: No human handoff is allowed. You are the final point of resolution. If your confidence is below {conf_level}, do your best to assist based on tools, but stay polite.


### Directives:
- **Sentiment Analysis**: {sentiment_directive}.
- **Source **: {source_directive}.
- **Customer Info**: For account/transaction history, you MUST ask for a **10-digit NUBAN**.
- **Channels**: Available service channels for this tenant: {ticket_type}.
- **Confidence Scoring**: {confidence_directive}. Even if confidence is low, provide the best possible help.
Context:
User Question: "{user_query}" Available Context: {context}

Output Format:


Return ONLY JSON:
```json
{{
  "answer": "string",
  "sentiment": int,
  "confidence_score": int,
  "ticket": {ticket_type},
  "source": [],
  "human_assistant": false
}}
```
"""

    # --- JSON Output Instructions ---
    json_instructions = f"""
### Output Format:
You MUST return ONLY a valid JSON object. Do not include any text outside the JSON block.
```json
{{
  "answer": "Your response to the user",
  "sentiment": int (-2 to 2),
  "confidence_score": int (0-100),
  "ticket": {ticket_type},
  "source": ["file1.pdf", "file2.pdf"],
  "human_assistant": bool
}}
```
"""

    # --- Logical Selection of Base Template ---
    # Default to schema-aware template
    template = agent_prompt_handoff if is_handoff_allowed else agent_prompt_no_handoff
    
    # If a specific prompt template is provided in the DB, use it, but we'll still append JSON instructions
    if prompt_template and isinstance(prompt_template, str) and prompt_template.strip():
        template = prompt_template
        # Check if the custom template already has JSON instructions; if not, append them
        if '"answer":' not in template:
            template += "\n" + json_instructions

    try:
        # Pre-format directives
        cf_directive = f"Assess your confidence in this answer from 0-100. If it is below {conf_level}, set 'human_assistant' to true."

        SYSTEM_PROMPT = template.format(
            name=tenant_name,
            message_tone=message_tone,
            conf_level=conf_level,
            ticket_type=ticket_type,
            user_query=user_query,
            context=context_str,
            sentiment_directive=sentiment_directive,
            source_directive=source_directive,
            confidence_directive=cf_directive,
        )

        # Final safety check: if JSON instructions aren't in the final prompt, prepend them
        if '"answer":' not in SYSTEM_PROMPT:
            SYSTEM_PROMPT = json_instructions + "\n" + SYSTEM_PROMPT

    except Exception as e:
        log_exception_auto(f"Prompt formatting failed: {e}", tenant_id, conversation_id)
        SYSTEM_PROMPT = f"You are a helpful assistant for {tenant_name}. Answer the user query: {user_query}"

    try:
        # Resolve LLM model dynamically

        prompt_model = get_llm_instance()
        log_info(f"LLM instance resolved for final answer generation: {type(prompt_model).__name__}", tenant_id, conversation_id)


        # Use prompt_model to allow tool calling

        # Force JSON format for the final answer via prompt + potentially kwargs if supported

        response = await prompt_model.ainvoke(

            [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

        )
        log_info("LLM response received", tenant_id, conversation_id)
        log_debug(f"Raw LLM response: {response}", tenant_id, conversation_id)
    except Exception as e:
        log_exception_auto(f"LLM invocation failed: {e}", tenant_id, conversation_id)
        return {
            "messages": [AIMessage(content="I'm sorry, I'm having trouble connecting to my brain right now.")],
            "leave_application": {
                "answer": "Connection error to AI service.",
                "human_assistant": True
            }
        }

    # --- Tool Call Handling ---
    if response.tool_calls:
        log_info("LLM made tool calls. Routing to tool node.", tenant_id, conversation_id)
        return {"messages": [response]}

    leave_app_data = None
    raw_text = ""
    try:
        content = response.content
        raw_text = content if isinstance(content, str) else str(content)

        # Extract JSON block using regex for robustness
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if json_match:
            cleaned = json_match.group(0)
        else:
            cleaned = raw_text.strip().replace("```json", "").replace("```", "").strip()
            
        parsed = json.loads(cleaned)

        # Standardize fields
        # convert source_type to list of uppercase values
        st = parsed.get("source_type", "GENERAL")
        if isinstance(st, list):
            parsed["source_type"] = [str(x).upper() for x in st]
        else:
            parsed["source_type"] = [str(st).upper()]
        parsed["sentiment"] = float(parsed.get("sentiment", 0))
        parsed["confidence_score"] = int(parsed.get("confidence_score", 100))
        
        # Apply your Guardrails (Capping confidence, Force handoff)
        if "GENERAL" in parsed.get("source_type", []) and parsed["confidence_score"] > 75:
            parsed["confidence_score"] = 75

        if is_handoff_allowed and (parsed["sentiment"] < sentiment_threshold or parsed["confidence_score"] < conf_level):
            parsed["human_assistant"] = True
            if "connecting you with a human" not in parsed["answer"]:
                parsed["answer"] += " I am connecting you with a human colleague to better assist you."

        leave_app_data = Answer(**parsed).dict()
        log_info("LLM Answer parsed successfully ", tenant_id, conversation_id)
        log_debug(f"Parsed Answer: {leave_app_data}", tenant_id, conversation_id)

    except Exception as e:
        log_error(f"Failed to parse Answer: {e}. Raw Text: {repr(raw_text)[:1000]}", tenant_id, conversation_id)
        leave_app_data = {
            "answer": "I'm having trouble processing that right now. Let me get a human to help.",
            "sentiment": 0.0,
            "confidence_score": 0,
            "source_type": "ERROR",
            "ticket": state.get("ticket_type", []),
            "source": [],
            "human_assistant": True,
        }

    # IMPORTANT: We save the processed dict into leave_application here
    return {
        "messages": [AIMessage(content=leave_app_data["answer"])],
        "leave_application": leave_app_data,
    }



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


# @tool("fetch_exit_policy_tool", args_schema=ExitPolicyRequest)
# def fetch_exit_policy_tool(config: RunnableConfig, **kwargs):
#     """Retrieves the company's exit and resignation policies, including notice periods and leave monetization."""
    
#     tid = kwargs.get('current_tool_id')
#     tenant_id = config["configurable"].get("tenant_id")

#     HRLogger.info(f"Retrieves exit policy for Tenant: {tenant_id}", config)

#     try:
#         # Filter for the specific company and general employee policies
#         query = {
#             "companyID": ObjectId(tenant_id),
#             "appliesTo": "all-employees"
#         }
#         if db_mongo is None:
#                 return "Database connection lost."

         
#         policies_collection = db_mongo["approvalworkflowleaverequests"]
#         policies = []
#         cursor = policies_collection.find(query)

#         for doc in cursor:
#             notice = doc.get("noticePeriod", {})
#             notice_str = "No notice required"
#             if notice.get("enforce"):
#                 notice_str = f"{notice.get('length')} {notice.get('time')}(s) required"

#             policy_summary = (
#                 f"### Policy: {doc.get('name')}\n"
#                 f"* **Notice Period:** {notice_str}\n"
#                 f"* **Contract Enforcement:** {'Yes' if doc.get('checkAgreements') else 'No'}\n"
#                 f"* **Use Unused Leave during exit:** {'Yes' if doc.get('includeUnusedLeave') else 'No'}\n"
#                 f"* **Monetize Unused Leave:** {'Yes' if doc.get('monetizeUnusedLeave') else 'No'}\n"
#                 f"* **Exit Interview Required:** {'Yes' if doc.get('checkExitInterview') else 'No'}"
#             )
#             policies.append(policy_summary)

#         if not policies:
#             result_text = "I couldn't find a specific exit policy for your department. Please contact HR for the employee handbook."
#         else:
#             result_text = "Here are the details of the company exit policy:\n\n" + "\n\n".join(policies)

#         return ToolMessage(
#             content=result_text,
#             tool_call_id=tid
#         )

#     except Exception as e:
#         HRLogger.error(f"Exit policy fetch failed: {str(e)}", config)
#         return f"Error retrieving exit policy: {str(e)}"    
    

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
    
    
def execute_sql_query_func(query: str) -> str:
    """Executes a SQL query using the pre-initialized SQL agent and returns the result."""
    if not SQL_AGENT:
        return {"sql_result": "Error: SQL Agent not initialized."}
    try:
        response_generator = SQL_AGENT.stream(
            {"messages": [HumanMessage(content=query)]}, stream_mode="values"
        )
        full_response_content = []
        for chunk in response_generator:
            if 'messages' in chunk and chunk['messages']:
                content = chunk['messages'][-1].content
                if content:
                    full_response_content.append(content)
        
        result = "\n".join(full_response_content) if full_response_content else "No response from SQL agent."
        return {"sql_result": result}
    except Exception as e:
        return {"sql_result": f"Error executing SQL query: {e}"}

sql_query_tool = Tool(
    name="sql_query_tool",
    description="Useful for answering questions requiring data from a SQL database (e.g., 'How many users are there?'). Input should be a natural language question.",
    func=execute_sql_query_func,
    args_schema=SQLQueryInput,
)





def get_column_types(df: pd.DataFrame):
    """Helper function to identify column types for plotting."""
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    date_cols = df.select_dtypes(include=['datetime', 'datetimetz']).columns.tolist()
    return numeric_cols, categorical_cols, date_cols




# --- FULLY ENHANCED VISUALIZATION TOOL ---
def generate_visualization_func(query: str) -> dict:
    """
    Generates a data visualization based on a natural language query.
    """
    logging.info(f"--- Generating Visualization for query: '{query}' ---")
    analysis_text = "" # Initialize in case of early failure
    try:
        # Step 1: Generate SQL from the natural language query (with few-shot prompt)
        sql_generation_prompt = f"""Given the user's question, create a single, syntactically correct SQL query to retrieve the data needed for a chart.
Do not include any other text or explanation, just the SQL query itself.

Tables available: {db.get_table_info()}

### Example ###
User question: "Show me the total transaction value for each month this year."
SQL Query:
```sql
SELECT
  STRFTIME('%Y-%m', timestamp) AS month,
  SUM(amount) AS total_value
FROM
  ai_transaction
WHERE
  STRFTIME('%Y', timestamp) = STRFTIME('%Y', 'now')
GROUP BY
  month
ORDER BY
  month;
```
### End Example ###

User question: "{query}"
SQL Query:
"""
        raw_sql_query = llm.invoke(sql_generation_prompt).content.strip()

        match = re.search(r"```(?:sql)?\s*(.*?)\s*```", raw_sql_query, re.DOTALL)
        if match:
            sql_query = match.group(1).strip()
        else:
            sql_query = raw_sql_query
        
        logging.info(f"Generated SQL: {sql_query}")

        # Step 2: Execute the query with Pandas
        engine = create_engine(DB_URI)
        df = pd.read_sql_query(sql_query, con=engine)
        
        if df.empty:
            logging.warning("Query returned no data.")
            return {"visualization_result": {"analysis": "I found no data to visualize for your request.", "image_base64": None}}

        # --- ENHANCED LOGGING: Log DataFrame details ---
        buffer = io.StringIO()
        df.info(buf=buffer)
        df_info_str = buffer.getvalue()
        logging.info(f"--- DataFrame Details ---\nHead:\n{df.head().to_string()}\nInfo:\n{df_info_str}")

        # Step 3: Determine the best chart type
        df_info_for_prompt = f"Data Columns: {df.columns.tolist()}\nData Head:\n{df.head().to_string()}"
        chart_selection_prompt = f"""
        Given the user's original query '{query}' and the following data summary, what is the best chart type to use?
        Your answer must be a single word from this list: 'bar', 'line', 'scatter', 'pie'.

        Data Summary:\n{df_info_for_prompt}
        """
        chart_type = llm.invoke(chart_selection_prompt).content.strip().lower()
        logging.info(f"LLM chose chart type: '{chart_type}'")

        # Step 4: Get textual analysis from the LLM
        analysis_prompt = f"Analyze this data and provide a brief, insightful summary based on the user's original request: '{query}'.\n\nData:\n{df.to_csv(index=False)}"        
        analysis_text = llm.invoke(analysis_prompt).content
        logging.info(f"Generated Analysis: {analysis_text[:200]}...") # Log a snippet

        # Step 5: Generate the plot using intelligent chart selection
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(10, 6))
        numeric, categorical, dates = get_column_types(df)
        
        if chart_type == 'bar' and categorical and numeric:
            x_col = categorical[0]
            if len(numeric) > 1: # Handle multi-series bar charts
                df.set_index(x_col)[numeric].plot(kind='bar', ax=ax, figsize=(12, 7))
                ax.set_ylabel("Values")
                ax.legend(title='Metrics')
            else: # Handle single-series bar charts
                y_col = numeric[0]
                df.plot(kind='bar', x=x_col, y=y_col, ax=ax, legend=False)
                ax.set_ylabel(y_col.replace('_', ' ').title())
            ax.set_xlabel(x_col.replace('_', ' ').title())
            plt.xticks(rotation=45, ha='right')

        elif chart_type == 'line' and (dates or numeric):
            x_col = dates[0] if dates else numeric[0]
            y_cols = [c for c in numeric if c != x_col]
            if not y_cols: y_cols = numeric # Fallback if x is also the only numeric
            df.plot(kind='line', x=x_col, y=y_cols, ax=ax, marker='o')
            ax.set_xlabel(x_col.replace('_', ' ').title())
            ax.set_ylabel("Value")
            plt.xticks(rotation=45, ha='right')

        elif chart_type == 'scatter' and len(numeric) >= 2:
            x_col, y_col = numeric[0], numeric[1]
            df.plot(kind='scatter', x=x_col, y=y_col, ax=ax)
            ax.set_xlabel(x_col.replace('_', ' ').title())
            ax.set_ylabel(y_col.replace('_', ' ').title())

        elif chart_type == 'pie' and categorical and numeric:
            df.set_index(categorical[0])[numeric[0]].plot(
                kind='pie', ax=ax, autopct='%1.1f%%', startangle=90
            )
            ax.set_ylabel('')
        
        else: # Fallback
            logging.warning(f"Could not find a perfect chart match for type '{chart_type}'. Using generic plot.")
            df.plot(ax=ax)
       
        # Formatting common to all charts
        ax.set_title(query.title())
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:,.0f}'))
        plt.tight_layout()
        
        # Step 6: Convert plot to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close(fig)
        logging.info(f"Successfully generated plot image (Base64 length: {len(image_base64)}).")

        return {
            "visualization_result": {
                "analysis": analysis_text,
                "image_base64": image_base64
            }
        }
    
    except Exception as e:
        # --- ENHANCED LOGGING: Log the full exception traceback ---
        logging.error("Error in visualization tool", exc_info=True)
        analysis_text_on_error = analysis_text if analysis_text else f"Sorry, I encountered an unrecoverable error: {e}"
        return {"visualization_result": {"analysis": analysis_text_on_error, "image_base64": None}}




generate_visualization_tool = Tool(
    name="generate_visualization_tool",
    description="Use this tool to create charts, graphs, plots, or any data visualizations. This is the best tool when the user asks to 'plot', 'chart', 'visualize', or 'draw' data.",
    func=generate_visualization_func,
    args_schema=VisualizationInput,
)

# tools = [pdf_retrieval_tool, tavily_search_tool, sql_query_tool, generate_visualization_tool]


# Combine all tools (Corrected logic)
tools = [pdf_retrieval_tool, tavily_search_tool,generate_visualization_tool]
if SQL_AGENT:
    tools.append(sql_query_tool)






# Updated `update_state_after_tool_call` function
def update_state_after_tool_call(state: State) -> dict:
    """
    Updates the specific state field with the output from the last tool call.
    """
    print("--- UPDATING STATE FROM TOOL OUTPUT ---")
    last_message = state["messages"][-1]
    
    # Ensure the last message is a ToolMessage
    if not isinstance(last_message, ToolMessage):
        return {}

    tool_name = state.get("last_tool_name")
    tool_output = last_message.content
    
    print(f"Tool '{tool_name}' returned: {tool_output[:200]}...")

    if tool_name == "pdf_retrieval_tool":
        return {"pdf_content": tool_output}
    elif tool_name == "tavily_search_tool":
        return {"web_content": tool_output}
    elif tool_name == "sql_query_tool":
        return {"sql_result": tool_output}
    elif tool_name == "generate_visualization_tool":
        # The tool's output is a stringified JSON. We need to parse it.

        try:
            # Find the start and end of the JSON object in the raw output
            start_index = tool_output.find('{')
            end_index = tool_output.rfind('}') + 1
            if start_index != -1 and end_index != -1:
                json_string = tool_output[start_index:end_index]
                parsed_output = json.loads(json_string)
                viz_data = parsed_output.get("visualization_result")
                if viz_data:
                    return {"visualization_result": viz_data}
            return {} # Return empty dict if no valid JSON is found
        except json.JSONDecodeError as e:
            print(f"Error parsing visualization tool output: {e}")
            return {}
        # try:
        #     parsed_output = json.loads(tool_output)
        #     # The tool returns a dictionary with one key: "visualization_result"
        #     viz_data = parsed_output.get("visualization_result")
        #     if viz_data:
        #         return {"visualization_result": viz_data}
        # except json.JSONDecodeError as e:
        #     print(f"Error parsing visualization tool output: {e}")
        #     return {}
    
    return {}


def agent_node(state: State):
    """
    The Router Node: Decides whether to call a tool or generate a final answer.
    """
    print("--- AGENT NODE (ROUTER) ---")
    messages = state["messages"]
    
    # Handle the very first message with a greeting
    if len(messages) == 1:
        return {"messages": [AIMessage(content=f"{get_time_based_greeting()}! I am Damilola... How can I help?")]}
    
    # REVISED PROMPT: More specific on tool usage
    system_prompt = SystemMessage(
        content=f"""You are a helpful AI assistant for ATB Bank. Your task is to analyze the user's request and decide if a tool is needed to answer it.
        
        You have access to the following tools:
        - `pdf_retrieval_tool`: For questions about bank policies, products, or internal knowledge.
        - `tavily_search_tool`: For general knowledge or up-to-date information.
        - `sql_query_tool`: For questions about specific data, like user counts or transaction volumes.
        - **`generate_visualization_tool`**: **Use this tool ONLY when the user explicitly asks to 'plot', 'chart', 'graph', or 'visualize' data. This is your primary tool for creating visual representations from database data.**
        
        Based on the conversation history, either call the most appropriate tool to gather information or, if you have enough information already, prepare to answer the user directly.
        """
    )
    
    llm_with_tools = llm.bind_tools(tools)
    response = llm_with_tools.invoke([system_prompt] + messages)
    
    last_tool_name = None
    if response.tool_calls:
        last_tool_name = response.tool_calls[0]['name']
        print(f"LLM decided to call tool: {last_tool_name}")
        
    return {"messages": [response], "last_tool_name": last_tool_name}

def build_graph():
    """Builds and compiles the LangGraph workflow."""
    workflow = StateGraph(State)
    
    workflow.add_node("agent_node", agent_node)
    workflow.add_node("tools", ToolNode(tools=tools))
    workflow.add_node("update_state", update_state_after_tool_call)

    workflow.add_node("generate_final_answer", generate_final_answer_node)
    workflow.add_node("summarize", summarize_conversation)

    workflow.set_entry_point("agent_node")

    workflow.add_conditional_edges("agent_node", tools_condition, {"tools": "tools",END: "generate_final_answer",})
    


    # workflow.add_conditional_edges("agent_node", should_continue)
    workflow.add_edge("tools", "update_state")
    workflow.add_edge("update_state", "agent_node")
    # workflow.add_edge("tools", "agent_node")
    workflow.add_edge("generate_final_answer", "summarize")
    workflow.add_edge("summarize", END)
    
    # Initialize checkpointing with a robust fallback
    memory = None
    try:
        # Create a path for the checkpointing database
        checkpoint_dir = os.path.dirname(settings.DATABASES['default']['NAME'])
        checkpoint_db = os.path.join(checkpoint_dir, 'checkpoints.sqlite')
        
        # Ensure the directory exists
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        # Connect to the SQLite database
        conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
        memory = SqliteSaver(conn=conn)
        print("SQLite checkpointing connected successfully.")
    except Exception as e:
        # from langgraph.checkpoint.memory import InMemorySaver
        print(f"Error connecting to SQLite for checkpointing: {e}. Using in-memory saver.")
        # memory = InMemorySaver()
    return workflow.compile(checkpointer=memory)

# Main processing function
def process_message(message_content: str, session_id: str, file_path: Optional[str] = None):
    """Main function to process user messages using the LangGraph agent."""
    graph = build_graph()
    config = {"configurable": {"thread_id": session_id}}
    
    attached_content = None # Simplified for this example
    # Image processing logic can be added here as in the original code
    if file_path:
        try:
            image = Image.open(file_path)
            image.thumbnail([512, 512]) # Resize for efficiency
            
             # Detect format and set MIME type
            image_format = image.format.upper()
            if image_format not in ["PNG", "JPEG", "JPG"]:
                raise ValueError(f"Unsupported image format: {image_format}")

            mime_type = "jpeg" if image_format in ["JPEG", "JPG"] else "png"

            # Convert image to base64
            buffered = io.BytesIO()
            image.save(buffered, format=image_format)
            
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            image_uri = f"data:image/{mime_type};base64,{img_str}"
            
            if image_uri:
                # prompt = "Describe the content of the picture in detail."
                os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
                llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")
                
                prompt = "Generate the message in the content of the picture."
                message = HumanMessage(
                content=[
                {"type": "text", "text": prompt, },
                { "type": "image_url","image_url": {"url": image_uri}},])
                # Invoke the model with the message
                response = llm.invoke([message])
                
     
            # configure(api_key=GOOGLE_API_KEY)
            # genai.configure(api_key=GOOGLE_API_KEY)  # Configure the API key
            # modelT = genai.GenerativeModel('gemini-pro-vision') # Specify the vision model
            # modelT = GenerativeModel(model_name="gemini-2.0-flash", generation_config={"temperature": 0.7,"max_output_tokens": 512 })
            # response = modelT.generate_content([image, prompt])
            # attached_content = response.text
            # Extract the text content from the response
        
                # Invoke the model
                response = llm.invoke([message])
                attached_content = response.content

                print("Attached content from image:", attached_content)

# except FileNotFoundError:
#     print(f"Error: File not found at {file_path}")

# except Exception as e:
#     print(f"Error processing image: {e}")
            

        except Exception as e:
            print(f"Error processing image attachment: {e}")
            attached_content = f"Error: Could not process attached file ({e})"
    elif file_path:
        print(f"Warning: Attached file not found at {file_path}. Skipping image processing.")
    
    initial_state = {"messages": [HumanMessage(content=message_content)], "attached_content": attached_content}
    output = graph.invoke(initial_state, config)
    print("--- LangGraph workflow completed ---")
    
    # Extract final answer from the structured Pydantic object
    final_answer_obj = output.get('final_answer')
    final_answer_content = final_answer_obj.answer if final_answer_obj else "No final answer was generated."
    if final_answer_obj:
        return {
            "answer": final_answer_content,
            "chart": final_answer_obj.chart_base64, # <-- Pass chart data to the view
            "metadata": output.get("metadatas", {})
        }
    # return {
    #     "answer": final_answer_content,
    #     "metadata": output.get("metadatas", {})
    # }
    else:
        return {
            "answer": "I'm sorry, I could not generate a response.",
            "chart": None,
            "metadata": {}
        }



def generate_final_answer_node(state: State):
    """
    The Generator Node: Creates the final structured answer after gathering all necessary context from tools.
    """
    print("--- GENERATE FINAL ANSWER NODE ---")
    user_query = state["messages"][-1].content
    print ("Lemu",state.get("pdf_content"))

    
    context_parts = []
    if state.get("pdf_content"): context_parts.append(f"PDF Content:\n{state['pdf_content']}")
    if state.get("web_content"): context_parts.append(f"Web Content:\n{state['web_content']}")
    if state.get("sql_result"): context_parts.append(f"SQL Database Result:\n{state['sql_result']}")




    # # NEW: Handle visualization result
    # viz_result = state.get("visualization_result")
    # chart_base64 = None
    # if viz_result:
    #     analysis = viz_result.get('analysis', 'Chart analysis is not available.')   
    #     chart_base64 = viz_result.get('image_base64')
    #     context_parts.append(f"Visualization Analysis:\n{analysis}")

    # --- THE FIX: PART 1 ---
    # Store the chart data in a variable, but only put the TEXT analysis in the LLM context.
    viz_result = state.get("visualization_result")
    chart_base64_data = None # Initialize
    if viz_result:
        analysis = viz_result.get('analysis', 'Chart analysis is not available.')   
        chart_base64_data = viz_result.get('image_base64') # Store the data here
        context_parts.append(f"Visualization Analysis:\n{analysis}") # Add ONLY analysis to context


    # if state.get("attached_content"): context_parts.append(f"Attached Content:\n{state['attached_content']}")
    # context = "\n\n".join(context_parts) if context_parts else "No additional context was retrieved."

    if state.get("attached_content"): context_parts.append(f"Attached Content:\n{state['attached_content']}")
    context = "\n\n".join(context_parts) if context_parts else "No additional context was retrieved."

    # Prompt designed to generate a structured JSON output based on the Answer schema
    # prompt = f"""You are Damilola, the AI-powered virtual assistant for ATB Bank.
    # Your goal is to provide a final, comprehensive, and empathetic answer based on the user's question and the context gathered from your tools.
    
    # User Question: "{user_query}"
    
    # Available Context:
    # ---
    # {context}
    # ---
    
    # Based on all the information above, generate a structured response. You MUST format your response as a JSON object that strictly follows the schema below.
    
    #     Generate a structured JSON response. 
    # - The 'answer' field should summarize the findings. If a chart was generated, describe what the chart shows.
    # - If a chart was generated (indicated by 'Visualization Analysis' in the context), copy the provided chart data into the 'chart_base64' field. Otherwise, leave it as null.
    #     Schema:
    # {{
    #   "answer": "str: A clear, concise, empathetic, and polite response directly addressing the user's question. Use straightforward language.",
    #   "sentiment": "int: An integer rating of the user's sentiment, from -2 (very negative) to +2 (very positive).",
    #   "ticket": "List[str]: A list of service channels relevant to any unresolved issue. Possible values: ['POS', 'ATM', 'Web', 'Mobile App', 'Branch', 'Call Center', 'Other']. Leave empty if not applicable.",
    #   "source": "List[str]: A list of sources used. Possible values: ['PDF Content', 'Web Search', 'SQL Database', 'User Provided Context', 'Internal Knowledge']. Leave empty if no specific source was used."
    # }}
    # """
    

 # --- THE FIX: PART 2 ---
    # Simplify the prompt. The LLM should NOT handle the chart_base64 data.
    prompt1 = f"""You are Damilola, the AI-powered virtual assistant for ATB .
    Your goal is to provide a final, comprehensive, and empathetic answer based on the user's question and the context gathered from your tools.
    
    User Question: "{user_query}"
    
    Available Context:
    ---
    {context}
    ---
    
    Based on all the information above, generate a structured response. If the context includes 'Visualization Analysis', your answer should describe what the chart shows.
    You MUST format your response as a JSON object that strictly follows this schema, omitting the 'chart_base64' field as it will be handled separately.
    
    Schema:
    {{
      "answer": "str: Your clear, concise, and polite response.",
      "sentiment": "int: An integer rating of the user's sentiment (-2 to +2).",
      "ticket": "List[str]: Relevant service channels. Empty list if not applicable.",
      "source": "List[str]: Sources used. Empty list if not applicable."
    }}
    """

    prompt = f"""You are Damilola, the AI-powered virtual assistant for ATB. Your role is to deliver professional customer service and insightful data analysis, depending on the user's needs.

You operate in two modes:
1. **Customer Support**: Respond with empathy, clarity, and professionalism. Your goal is to resolve issues, answer questions, and guide users to helpful resources — without technical jargon or internal system references.
2. **Data Analyst**: Interpret data, explain trends, and offer actionable insights. When visualizations are included, describe what the chart shows and what it means for the user.

Your response must be:
- **Final**: No follow-up questions or uncertainty.
- **Clear and Polite**: Use emotionally intelligent language, especially if the user expresses frustration or confusion.
- **Context-Aware**: Avoid mentioning internal systems (e.g., database names or SQL sources) unless explicitly requested.
- **Structured**: Always return your answer in the following JSON format.

User Question:
"{user_query}"

Available Context:
---
{context}
---

If the context includes 'Visualization Analysis', describe the chart’s content and implications.

Format your response as a JSON object using this schema (omit 'chart_base64'):

Schema:
{{
  "answer": "str: Your clear, concise, and polite response.",
  "sentiment": "int: An integer rating of the user's sentiment (-2 to +2).",
  "ticket": "List[str]: Relevant service channels (e.g., 'email', 'live chat', 'support portal'). Empty list if not applicable.",
  "source": "List[str]: Sources used to generate the answer. Empty list if not applicable."
}}
   """



    structured_llm = llm.with_structured_output(Answer)
    final_answer_obj = structured_llm.invoke(prompt)
    if chart_base64_data:
        final_answer_obj.chart_base64 = chart_base64_data
    
    # Append the human-readable part of the answer to the message history
    new_messages = state["messages"] + [AIMessage(content=final_answer_obj.answer)]
    return {
        "final_answer": final_answer_obj,
        "messages": new_messages
    }


    
    # return {
    #     "final_answer": final_answer_obj,
    #     "messages": new_messages
    # }

def summarize_conversation(state: State):
    """Generates a final summary of the conversation.
     
    Generates a final summary of the conversation after the answer has been provided.

    This node:
    1. Takes the complete message history from the state.
    2. Uses an LLM with structured output to generate a Summary object.
    3. Compiles a comprehensive 'metadatas' dictionary for logging, combining
       information from the final answer and the new summary.
    4. Updates the state with the 'conversation_summary' and 'metadatas'.
    """
    print("--- SUMMARIZE CONVERSATION NODE ---")
    
    messages = state.get("messages", [])
 
    
    # 1. Prepare the conversation history for the LLM
    # Using .get() provides a default empty list if 'messages' is not in the state
     
    if not messages:
        # If there are no messages, we can't summarize. Return an empty update.
        return {
            "conversation_summary": None,
            "metadatas": {"error": "No messages to summarize."}
        }



    conversation_history = "\n".join([f"{msg.type}: {msg.content}" for msg in state["messages"]])
    
    summarize_prompt = f"""Please provide a structured summary of the following conversation.
    
    Conversation History:
    {conversation_history}
    
    Provide the output in a JSON format matching this schema:
    {{
        "summary": "A concise summary of the entire conversation.",
        "sentiment": "Overall sentiment score of the conversation (-2 to +2).",
        "unresolved_tickets": ["List of channels with unresolved issues."],
        "all_sources": ["All unique sources referenced in the conversation."]
    }}
    """
    
    structured_llm = llm.with_structured_output(Summary)
    summary_obj = structured_llm.invoke(summarize_prompt)
    
    # Create the final metadata dictionary for logging
    final_answer = state.get("final_answer")
    last_user_question = ""
    if len(messages) > 1:
        # The last message is the AI's answer, the one before is the user's prompt for that turn
        last_user_question = messages[-2].content

    metadata_dict = {
        "question": state["messages"][-2].content if len(state["messages"]) > 1 else "",
        "answer": final_answer.answer if final_answer else "N/A",
        "sentiment": final_answer.sentiment if final_answer else 0,
        "ticket": final_answer.ticket if final_answer else [],
        "source": final_answer.source if final_answer else [],
        "chart_base64": final_answer.chart_base64 if final_answer else None,
        "summary": summary_obj.summary,
        "summary_sentiment": summary_obj.sentiment,
        "summary_unresolved_tickets": summary_obj.unresolved_tickets,
        "summary_sources": summary_obj.all_sources,
    }

    return {
        "conversation_summary": summary_obj,
        "metadatas": metadata_dict
    }

# Define the condition to check if a tool was called
def should_continue(state: State) -> str:
    """Determines the next step: call a tool or generate the final answer."""
    if state["messages"][-1].tool_calls:
        return "tools"
    return "generate_final_answer"

