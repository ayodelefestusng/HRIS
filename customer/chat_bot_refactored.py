# ==================================
# REFACTORED CHATBOT MODULE
# Supports: Customer Service, HR Services, CRM, Analytics
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
import traceback
from logging.handlers import RotatingFileHandler
from collections import UserDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from importlib import metadata
from io import BytesIO
from math import log
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union, Annotated
from typing_extensions import TypedDict
from urllib.parse import urlparse
from xml.dom.minidom import Document

# Third-party imports
from dotenv import load_dotenv
from PIL import Image
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import Boolean, create_engine, Column, String, Integer, Float, DateTime
from sqlalchemy.orm import Session
import pandas as pd

# LangChain imports
from langchain_core.documents import Document as LangChainDocument
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    AnyMessage,
)
from langchain_core.tools import Tool
from langchain_core.vectorstores import VectorStore
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredFileLoader,
    CSVLoader,
    RecursiveUrlLoader,
    WebBaseLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS, Chroma
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_tavily import TavilySearch
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool, ToolRuntime
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# LangGraph imports
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, Send
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.sqlite import SqliteStore

from pprint import pprint

# Database imports
from database import SessionLocal, Tenant, Conversation, Message, Prompt, get_db, LLM

# Load environment variables
load_dotenv()

# ==================================
# LOGGING CONFIGURATION
# ==================================

# Create logs directory if it doesn't exist
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "chatbot_refactored.log")

# Configure UTF-8 encoding for stdout/stderr
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception as e:
    pass

try:
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception as e:
    pass

# Set up logging
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

logger = logging.getLogger(__name__)
logger.propagate = True

# Suppress noisy libraries
logging.getLogger("watchfiles").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.INFO)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("langsmith").setLevel(logging.INFO)

# ==================================
# LOGGING HELPER FUNCTIONS
# ==================================

def log_context(tenant_id: str, conversation_id: str, user_id: Optional[str] = None) -> str:
    """Create a consistent context string for logging."""
    context = f"[Tenant: {tenant_id} | Conversation: {conversation_id}"
    if user_id:
        context += f" | User: {user_id}"
    context += "]"
    return context

def log_info(msg: str, tenant_id: str, conversation_id: str, user_id: Optional[str] = None):
    """Log info message with context."""
    context = log_context(tenant_id, conversation_id, user_id)
    logger.info(f"{context} {msg}")

def log_error(msg: str, tenant_id: str, conversation_id: str, user_id: Optional[str] = None, exc_info: bool = False):
    """Log error message with context."""
    context = log_context(tenant_id, conversation_id, user_id)
    logger.error(f"{context} {msg}", exc_info=exc_info)

def log_warning(msg: str, tenant_id: str, conversation_id: str, user_id: Optional[str] = None):
    """Log warning message with context."""
    context = log_context(tenant_id, conversation_id, user_id)
    logger.warning(f"{context} {msg}")

def log_debug(msg: str, tenant_id: str, conversation_id: str, user_id: Optional[str] = None):
    """Log debug message with context."""
    context = log_context(tenant_id, conversation_id, user_id)
    logger.debug(f"{context} {msg}")

def log_exception(msg: str, tenant_id: str, conversation_id: str, user_id: Optional[str] = None):
    """Log exception with full traceback."""
    context = log_context(tenant_id, conversation_id, user_id)
    logger.error(f"{context} {msg}", exc_info=True)

# ==================================
# CONSTANTS & GLOBALS
# ==================================

GLOBAL_SCOPE = "GLOBAL"
NO_CONVO = "N/A"

# Get API keys from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_USERNAME = os.getenv("OLLAMA_USERNAME", "")
OLLAMA_PASSWORD = os.getenv("OLLAMA_PASSWORD", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss-safeguard:20b")
GOOGLE_API_KEY = GEMINI_API_KEY

# Global embeddings instance (lazy-loaded)
embeddings = None

# ==================================
# DATABASE CONFIGURATION
# ==================================

def _build_db_uri_from_env() -> tuple[str, str]:
    """Build a SQLAlchemy-compatible DB URI from environment variables."""
    try:
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
        except Exception as parse_err:
            log_warning(f"Failed to parse DB URI: {parse_err}", GLOBAL_SCOPE, NO_CONVO)

        return db_uri, db_file_path
    except Exception as e:
        log_error(f"Error building DB URI: {e}", GLOBAL_SCOPE, NO_CONVO, exc_info=True)
        return "sqlite:///ai_database.sqlite3", "ai_database.sqlite3"


def get_sql_database_instance() -> Optional[SQLDatabase]:
    """Create and return a SQLDatabase instance or None on failure."""
    try:
        db_uri, db_file = _build_db_uri_from_env()
        log_info(f"Attempting to connect to database: {db_uri[:50]}...", GLOBAL_SCOPE, NO_CONVO)

        # Strip out unsupported query params
        if "ssl-mode" in db_uri:
            db_uri = db_uri.split("?")[0]

        # Build engine with SSL args if needed
        connect_args = {}
        if "mysql+pymysql" in db_uri:
            connect_args = {"ssl": {"ssl_mode": "REQUIRED"}}

        engine = create_engine(db_uri, connect_args=connect_args, pool_pre_ping=True)
        db_instance = SQLDatabase(engine)
        log_info(f"SQLDatabase connected successfully. Using: {db_uri[:50]}...", GLOBAL_SCOPE, NO_CONVO)
        return db_instance

    except Exception as e:
        log_error(f"Error connecting to SQLDatabase: {str(e)[:200]}", GLOBAL_SCOPE, NO_CONVO, exc_info=True)
        return None


# Initialize database
db = get_sql_database_instance()
DB_URI = None
DB_FILE_PATH = None
if db:
    try:
        DB_URI, DB_FILE_PATH = _build_db_uri_from_env()
        log_info(f"Database initialized. File path: {DB_FILE_PATH}", GLOBAL_SCOPE, NO_CONVO)
    except Exception as e:
        log_warning(f"Could not determine DB file path: {e}", GLOBAL_SCOPE, NO_CONVO)

# ==================================
# SERVICE DEFINITIONS
# ==================================

class ServiceType:
    """Enumeration of supported services."""
    CUSTOMER_SERVICE = "customer_service"
    HR_EMPLOYEE = "hr_employee"
    CRM = "crm"
    ANALYTICS = "analytics"
    GENERAL = "general"

class CustomerServiceRequest(BaseModel):
    """Schema for customer service requests."""
    customer_id: str = Field(..., description="Unique customer identifier")
    issue_type: str = Field(..., description="Type of issue: complaint, inquiry, transaction, account")
    priority: str = Field(default="normal", description="Priority level: low, normal, high, critical")
    description: str = Field(..., description="Detailed description of the issue")
    attachment: Optional[str] = Field(None, description="File path or URL of attachment")

class HREmployeeRequest(BaseModel):
    """Schema for HR employee service requests."""
    employee_id: str = Field(..., description="Unique employee identifier")
    request_type: str = Field(..., description="Type: leave, payroll, benefits, training, complaint")
    details: str = Field(..., description="Detailed request information")
    attachment: Optional[str] = Field(None, description="Supporting document path")

class CRMRequest(BaseModel):
    """Schema for CRM operations."""
    operation: str = Field(..., description="Type: create_account, create_lead, update_contact, update_opportunity")
    entity_type: str = Field(..., description="Entity: Account, Contact, Lead, Opportunity")
    data: Dict[str, Any] = Field(..., description="Entity data as key-value pairs")

class AnalyticsRequest(BaseModel):
    """Schema for analytics queries."""
    analysis_type: str = Field(..., description="Type: customer_metrics, sales_analytics, hr_analytics, transaction_analytics")
    date_range: Optional[Dict[str, str]] = Field(None, description="date_from and date_to in YYYY-MM-DD format")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")
    metrics: Optional[List[str]] = Field(None, description="Specific metrics to retrieve")

# ==================================
# CUSTOMER SERVICE MODULE
# ==================================

class CustomerServiceManager:
    """Manages customer service operations."""
    
    def __init__(self, tenant_id: str, conversation_id: str):
        self.tenant_id = tenant_id
        self.conversation_id = conversation_id
        self.db = SessionLocal()
    
    def __del__(self):
        """Ensure database session is closed."""
        try:
            if self.db:
                self.db.close()
        except Exception as e:
            log_warning(f"Error closing database session: {e}", self.tenant_id, self.conversation_id)
    
    def log_msg(self, msg: str, level: str = "info"):
        """Log message with service context."""
        func = {"info": log_info, "error": log_error, "warning": log_warning, "debug": log_debug}.get(level, log_info)
        func(f"[CustomerService] {msg}", self.tenant_id, self.conversation_id)
    
    async def handle_customer_service_request(self, request: CustomerServiceRequest, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle customer service requests with proper error handling."""
        try:
            self.log_msg(f"Processing customer service request: {request.issue_type}")
            
            # Validate customer exists
            from customer.models import Customer
            try:
                customer = self.db.query(Customer).filter(Customer.customer_id == request.customer_id).first()
                if not customer:
                    self.log_msg(f"Customer not found: {request.customer_id}", "warning")
                    return {
                        "status": "error",
                        "code": "CUSTOMER_NOT_FOUND",
                        "message": f"Customer {request.customer_id} not found in the system."
                    }
            except Exception as e:
                self.log_msg(f"Error querying customer: {str(e)}", "error")
                return {
                    "status": "error",
                    "code": "DB_ERROR",
                    "message": "Failed to verify customer information."
                }
            
            # Route based on issue type
            handler_map = {
                "complaint": self.handle_complaint,
                "inquiry": self.handle_inquiry,
                "transaction": self.handle_transaction_issue,
                "account": self.handle_account_issue,
            }
            
            handler = handler_map.get(request.issue_type, self.handle_generic_request)
            result = await handler(customer, request, user_id)
            
            self.log_msg(f"Customer service request completed with status: {result.get('status')}")
            return result
            
        except Exception as e:
            log_exception(f"Unexpected error in customer service handler: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {
                "status": "error",
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred processing your request."
            }
    
    async def handle_complaint(self, customer, request: CustomerServiceRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle customer complaints."""
        try:
            self.log_msg(f"Handling complaint for customer {customer.customer_id}")
            
            # Create a support ticket or log the complaint
            priority_level = {"low": 1, "normal": 2, "high": 3, "critical": 4}.get(request.priority, 2)
            
            return {
                "status": "success",
                "code": "COMPLAINT_LOGGED",
                "message": f"Your complaint has been logged with priority level {request.priority}. A support specialist will contact you soon.",
                "ticket_id": f"COMP-{int(time.time())}",
                "estimated_response_time": "24 hours"
            }
        except Exception as e:
            log_exception(f"Error handling complaint: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "COMPLAINT_HANDLER_ERROR", "message": str(e)}
    
    async def handle_inquiry(self, customer, request: CustomerServiceRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle customer inquiries."""
        try:
            self.log_msg(f"Handling inquiry for customer {customer.customer_id}")
            return {
                "status": "success",
                "code": "INQUIRY_RESPONSE",
                "message": f"Your inquiry about '{request.description}' has been received and will be answered within 2 hours.",
                "inquiry_id": f"INQ-{int(time.time())}"
            }
        except Exception as e:
            log_exception(f"Error handling inquiry: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "INQUIRY_HANDLER_ERROR", "message": str(e)}
    
    async def handle_transaction_issue(self, customer, request: CustomerServiceRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle transaction-related issues."""
        try:
            self.log_msg(f"Handling transaction issue for customer {customer.customer_id}")
            return {
                "status": "success",
                "code": "TRANSACTION_ISSUE_ESCALATED",
                "message": "Your transaction issue has been escalated to our transactions team. We will investigate and get back to you within 48 hours.",
                "reference_id": f"TXN-{int(time.time())}"
            }
        except Exception as e:
            log_exception(f"Error handling transaction issue: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "TRANSACTION_HANDLER_ERROR", "message": str(e)}
    
    async def handle_account_issue(self, customer, request: CustomerServiceRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle account-related issues."""
        try:
            self.log_msg(f"Handling account issue for customer {customer.customer_id}")
            return {
                "status": "success",
                "code": "ACCOUNT_ISSUE_LOGGED",
                "message": "Your account issue has been logged. Account specialists will review it and contact you shortly.",
                "reference_id": f"ACC-{int(time.time())}"
            }
        except Exception as e:
            log_exception(f"Error handling account issue: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "ACCOUNT_HANDLER_ERROR", "message": str(e)}
    
    async def handle_generic_request(self, customer, request: CustomerServiceRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle generic customer service requests."""
        try:
            self.log_msg(f"Handling generic request for customer {customer.customer_id}")
            return {
                "status": "success",
                "code": "REQUEST_RECEIVED",
                "message": "Your request has been received and will be processed by our service team.",
                "reference_id": f"REQ-{int(time.time())}"
            }
        except Exception as e:
            log_exception(f"Error handling generic request: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "GENERIC_HANDLER_ERROR", "message": str(e)}


# ==================================
# HR EMPLOYEE MODULE
# ==================================

class HREmployeeManager:
    """Manages HR employee service operations."""
    
    def __init__(self, tenant_id: str, conversation_id: str):
        self.tenant_id = tenant_id
        self.conversation_id = conversation_id
        self.db = SessionLocal()
    
    def __del__(self):
        """Ensure database session is closed."""
        try:
            if self.db:
                self.db.close()
        except Exception as e:
            log_warning(f"Error closing database session: {e}", self.tenant_id, self.conversation_id)
    
    def log_msg(self, msg: str, level: str = "info"):
        """Log message with service context."""
        func = {"info": log_info, "error": log_error, "warning": log_warning, "debug": log_debug}.get(level, log_info)
        func(f"[HREmployee] {msg}", self.tenant_id, self.conversation_id)
    
    async def handle_hr_request(self, request: HREmployeeRequest, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle HR employee requests."""
        try:
            self.log_msg(f"Processing HR request type: {request.request_type}")
            
            handler_map = {
                "leave": self.handle_leave_request,
                "payroll": self.handle_payroll_inquiry,
                "benefits": self.handle_benefits_inquiry,
                "training": self.handle_training_request,
                "complaint": self.handle_hr_complaint,
            }
            
            handler = handler_map.get(request.request_type, self.handle_generic_hr_request)
            result = await handler(request, user_id)
            
            self.log_msg(f"HR request completed with status: {result.get('status')}")
            return result
            
        except Exception as e:
            log_exception(f"Unexpected error in HR handler: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {
                "status": "error",
                "code": "INTERNAL_ERROR",
                "message": "An error occurred processing your HR request."
            }
    
    async def handle_leave_request(self, request: HREmployeeRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle leave requests."""
        try:
            self.log_msg(f"Processing leave request for employee {request.employee_id}")
            return {
                "status": "success",
                "code": "LEAVE_REQUEST_SUBMITTED",
                "message": "Your leave request has been submitted to your manager for approval.",
                "request_id": f"LEAVE-{int(time.time())}",
                "next_steps": "You will receive an email notification when your manager approves or rejects the request."
            }
        except Exception as e:
            log_exception(f"Error processing leave request: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "LEAVE_REQUEST_ERROR", "message": str(e)}
    
    async def handle_payroll_inquiry(self, request: HREmployeeRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle payroll inquiries."""
        try:
            self.log_msg(f"Handling payroll inquiry for employee {request.employee_id}")
            return {
                "status": "success",
                "code": "PAYROLL_INFO_RETRIEVED",
                "message": "Payroll information retrieved. Please contact HR Payroll team for detailed assistance.",
                "payroll_contact": "payroll@company.com"
            }
        except Exception as e:
            log_exception(f"Error handling payroll inquiry: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "PAYROLL_ERROR", "message": str(e)}
    
    async def handle_benefits_inquiry(self, request: HREmployeeRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle benefits inquiries."""
        try:
            self.log_msg(f"Handling benefits inquiry for employee {request.employee_id}")
            return {
                "status": "success",
                "code": "BENEFITS_INFO_PROVIDED",
                "message": "Benefits information has been retrieved from the system.",
                "benefits_portal": "https://benefits.company.com"
            }
        except Exception as e:
            log_exception(f"Error handling benefits inquiry: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "BENEFITS_ERROR", "message": str(e)}
    
    async def handle_training_request(self, request: HREmployeeRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle training requests."""
        try:
            self.log_msg(f"Processing training request for employee {request.employee_id}")
            return {
                "status": "success",
                "code": "TRAINING_REQUEST_LOGGED",
                "message": "Your training request has been logged. HR will review and contact you with available training options.",
                "request_id": f"TRAIN-{int(time.time())}"
            }
        except Exception as e:
            log_exception(f"Error processing training request: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "TRAINING_ERROR", "message": str(e)}
    
    async def handle_hr_complaint(self, request: HREmployeeRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle HR complaints."""
        try:
            self.log_msg(f"Processing HR complaint for employee {request.employee_id}")
            return {
                "status": "success",
                "code": "COMPLAINT_LOGGED",
                "message": "Your complaint has been confidentially logged with the HR complaints team.",
                "complaint_id": f"HRC-{int(time.time())}",
                "escalation_contact": "hr-escalations@company.com"
            }
        except Exception as e:
            log_exception(f"Error processing HR complaint: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "COMPLAINT_ERROR", "message": str(e)}
    
    async def handle_generic_hr_request(self, request: HREmployeeRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle generic HR requests."""
        try:
            self.log_msg(f"Processing generic HR request for employee {request.employee_id}")
            return {
                "status": "success",
                "code": "REQUEST_LOGGED",
                "message": "Your HR request has been logged and will be handled by the HR team.",
                "request_id": f"HR-{int(time.time())}"
            }
        except Exception as e:
            log_exception(f"Error processing generic HR request: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "HR_ERROR", "message": str(e)}


# ==================================
# CRM MODULE
# ==================================

class CRMManager:
    """Manages CRM operations."""
    
    def __init__(self, tenant_id: str, conversation_id: str):
        self.tenant_id = tenant_id
        self.conversation_id = conversation_id
        self.db = SessionLocal()
    
    def __del__(self):
        """Ensure database session is closed."""
        try:
            if self.db:
                self.db.close()
        except Exception as e:
            log_warning(f"Error closing database session: {e}", self.tenant_id, self.conversation_id)
    
    def log_msg(self, msg: str, level: str = "info"):
        """Log message with service context."""
        func = {"info": log_info, "error": log_error, "warning": log_warning, "debug": log_debug}.get(level, log_info)
        func(f"[CRM] {msg}", self.tenant_id, self.conversation_id)
    
    async def handle_crm_operation(self, request: CRMRequest, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle CRM operations."""
        try:
            self.log_msg(f"Processing CRM operation: {request.operation} on {request.entity_type}")
            
            handler_map = {
                "create_account": self.create_account,
                "create_lead": self.create_lead,
                "update_contact": self.update_contact,
                "update_opportunity": self.update_opportunity,
                "fetch_account": self.fetch_account,
                "fetch_leads": self.fetch_leads,
            }
            
            handler = handler_map.get(request.operation, self.handle_generic_crm_operation)
            result = await handler(request, user_id)
            
            self.log_msg(f"CRM operation completed with status: {result.get('status')}")
            return result
            
        except Exception as e:
            log_exception(f"Unexpected error in CRM handler: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {
                "status": "error",
                "code": "INTERNAL_ERROR",
                "message": "An error occurred processing your CRM request."
            }
    
    async def create_account(self, request: CRMRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Create a new CRM account."""
        try:
            self.log_msg(f"Creating account with data: {request.data.get('name')}")
            
            from customer.models import Account
            try:
                account = Account(
                    name=request.data.get("name"),
                    website=request.data.get("website"),
                    phone=request.data.get("phone"),
                    industry=request.data.get("industry"),
                    account_type=request.data.get("account_type"),
                    description=request.data.get("description"),
                    annual_revenue=request.data.get("annual_revenue"),
                    employees=request.data.get("employees"),
                    address_street=request.data.get("address_street"),
                    address_city=request.data.get("address_city"),
                    address_state=request.data.get("address_state"),
                    address_zipcode=request.data.get("address_zipcode"),
                    address_country=request.data.get("address_country"),
                )
                self.db.add(account)
                self.db.commit()
                self.db.refresh(account)
                
                return {
                    "status": "success",
                    "code": "ACCOUNT_CREATED",
                    "message": f"Account '{request.data.get('name')}' created successfully.",
                    "account_id": account.id
                }
            except Exception as db_err:
                self.db.rollback()
                log_exception(f"Database error creating account: {str(db_err)}", self.tenant_id, self.conversation_id, user_id)
                return {"status": "error", "code": "DB_ERROR", "message": "Failed to create account in database."}
        except Exception as e:
            log_exception(f"Error creating account: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "CREATE_ACCOUNT_ERROR", "message": str(e)}
    
    async def create_lead(self, request: CRMRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Create a new lead."""
        try:
            self.log_msg(f"Creating lead for company: {request.data.get('company')}")
            
            from customer.models import Lead
            try:
                lead = Lead(
                    first_name=request.data.get("first_name"),
                    last_name=request.data.get("last_name"),
                    email=request.data.get("email"),
                    phone=request.data.get("phone"),
                    company=request.data.get("company"),
                    title=request.data.get("title"),
                    lead_status=request.data.get("lead_status", "new"),
                    lead_source=request.data.get("lead_source", "web"),
                )
                self.db.add(lead)
                self.db.commit()
                self.db.refresh(lead)
                
                return {
                    "status": "success",
                    "code": "LEAD_CREATED",
                    "message": f"Lead '{request.data.get('first_name')} {request.data.get('last_name')}' created successfully.",
                    "lead_id": lead.id
                }
            except Exception as db_err:
                self.db.rollback()
                log_exception(f"Database error creating lead: {str(db_err)}", self.tenant_id, self.conversation_id, user_id)
                return {"status": "error", "code": "DB_ERROR", "message": "Failed to create lead."}
        except Exception as e:
            log_exception(f"Error creating lead: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "CREATE_LEAD_ERROR", "message": str(e)}
    
    async def update_contact(self, request: CRMRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Update contact information."""
        try:
            self.log_msg(f"Updating contact with ID: {request.data.get('id')}")
            
            from customer.models import Contact
            try:
                contact = self.db.query(Contact).filter(Contact.id == request.data.get("id")).first()
                if not contact:
                    return {"status": "error", "code": "CONTACT_NOT_FOUND", "message": "Contact not found."}
                
                for key, value in request.data.items():
                    if key != "id" and hasattr(contact, key):
                        setattr(contact, key, value)
                
                self.db.commit()
                
                return {
                    "status": "success",
                    "code": "CONTACT_UPDATED",
                    "message": "Contact updated successfully.",
                    "contact_id": contact.id
                }
            except Exception as db_err:
                self.db.rollback()
                log_exception(f"Database error updating contact: {str(db_err)}", self.tenant_id, self.conversation_id, user_id)
                return {"status": "error", "code": "DB_ERROR", "message": "Failed to update contact."}
        except Exception as e:
            log_exception(f"Error updating contact: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "UPDATE_CONTACT_ERROR", "message": str(e)}
    
    async def update_opportunity(self, request: CRMRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Update sales opportunity."""
        try:
            self.log_msg(f"Updating opportunity with ID: {request.data.get('id')}")
            
            from customer.models import Opportunity
            try:
                opportunity = self.db.query(Opportunity).filter(Opportunity.id == request.data.get("id")).first()
                if not opportunity:
                    return {"status": "error", "code": "OPPORTUNITY_NOT_FOUND", "message": "Opportunity not found."}
                
                for key, value in request.data.items():
                    if key != "id" and hasattr(opportunity, key):
                        setattr(opportunity, key, value)
                
                self.db.commit()
                
                return {
                    "status": "success",
                    "code": "OPPORTUNITY_UPDATED",
                    "message": "Opportunity updated successfully.",
                    "opportunity_id": opportunity.id
                }
            except Exception as db_err:
                self.db.rollback()
                log_exception(f"Database error updating opportunity: {str(db_err)}", self.tenant_id, self.conversation_id, user_id)
                return {"status": "error", "code": "DB_ERROR", "message": "Failed to update opportunity."}
        except Exception as e:
            log_exception(f"Error updating opportunity: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "UPDATE_OPPORTUNITY_ERROR", "message": str(e)}
    
    async def fetch_account(self, request: CRMRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Fetch account details."""
        try:
            self.log_msg(f"Fetching account with ID: {request.data.get('id')}")
            
            from customer.models import Account
            try:
                account = self.db.query(Account).filter(Account.id == request.data.get("id")).first()
                if not account:
                    return {"status": "error", "code": "ACCOUNT_NOT_FOUND", "message": "Account not found."}
                
                return {
                    "status": "success",
                    "code": "ACCOUNT_FETCHED",
                    "message": "Account retrieved successfully.",
                    "account": {
                        "id": account.id,
                        "name": account.name,
                        "industry": account.industry,
                        "type": account.account_type,
                        "website": account.website,
                        "phone": account.phone,
                    }
                }
            except Exception as db_err:
                log_exception(f"Database error fetching account: {str(db_err)}", self.tenant_id, self.conversation_id, user_id)
                return {"status": "error", "code": "DB_ERROR", "message": "Failed to fetch account."}
        except Exception as e:
            log_exception(f"Error fetching account: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "FETCH_ACCOUNT_ERROR", "message": str(e)}
    
    async def fetch_leads(self, request: CRMRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Fetch leads with filters."""
        try:
            self.log_msg(f"Fetching leads with filters: {request.data}")
            
            from customer.models import Lead
            try:
                query = self.db.query(Lead)
                
                # Apply filters
                if "status" in request.data:
                    query = query.filter(Lead.lead_status == request.data["status"])
                if "source" in request.data:
                    query = query.filter(Lead.lead_source == request.data["source"])
                
                leads = query.limit(10).all()
                
                return {
                    "status": "success",
                    "code": "LEADS_FETCHED",
                    "message": f"Retrieved {len(leads)} leads.",
                    "leads": [
                        {
                            "id": lead.id,
                            "name": f"{lead.first_name} {lead.last_name}",
                            "email": lead.email,
                            "company": lead.company,
                            "status": lead.lead_status,
                        } for lead in leads
                    ]
                }
            except Exception as db_err:
                log_exception(f"Database error fetching leads: {str(db_err)}", self.tenant_id, self.conversation_id, user_id)
                return {"status": "error", "code": "DB_ERROR", "message": "Failed to fetch leads."}
        except Exception as e:
            log_exception(f"Error fetching leads: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "FETCH_LEADS_ERROR", "message": str(e)}
    
    async def handle_generic_crm_operation(self, request: CRMRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle generic CRM operations."""
        try:
            self.log_msg(f"Processing generic CRM operation: {request.operation}")
            return {
                "status": "success",
                "code": "OPERATION_QUEUED",
                "message": f"CRM operation '{request.operation}' has been queued for processing.",
            }
        except Exception as e:
            log_exception(f"Error in generic CRM operation: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "CRM_ERROR", "message": str(e)}


# ==================================
# ANALYTICS MODULE
# ==================================

class AnalyticsManager:
    """Manages analytics and reporting."""
    
    def __init__(self, tenant_id: str, conversation_id: str):
        self.tenant_id = tenant_id
        self.conversation_id = conversation_id
        self.db = SessionLocal()
    
    def __del__(self):
        """Ensure database session is closed."""
        try:
            if self.db:
                self.db.close()
        except Exception as e:
            log_warning(f"Error closing database session: {e}", self.tenant_id, self.conversation_id)
    
    def log_msg(self, msg: str, level: str = "info"):
        """Log message with service context."""
        func = {"info": log_info, "error": log_error, "warning": log_warning, "debug": log_debug}.get(level, log_info)
        func(f"[Analytics] {msg}", self.tenant_id, self.conversation_id)
    
    async def handle_analytics_request(self, request: AnalyticsRequest, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle analytics requests."""
        try:
            self.log_msg(f"Processing analytics request: {request.analysis_type}")
            
            handler_map = {
                "customer_metrics": self.get_customer_metrics,
                "sales_analytics": self.get_sales_analytics,
                "hr_analytics": self.get_hr_analytics,
                "transaction_analytics": self.get_transaction_analytics,
            }
            
            handler = handler_map.get(request.analysis_type, self.get_generic_analytics)
            result = await handler(request, user_id)
            
            self.log_msg(f"Analytics request completed with status: {result.get('status')}")
            return result
            
        except Exception as e:
            log_exception(f"Unexpected error in analytics handler: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {
                "status": "error",
                "code": "INTERNAL_ERROR",
                "message": "An error occurred processing your analytics request."
            }
    
    async def get_customer_metrics(self, request: AnalyticsRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Get customer-related metrics."""
        try:
            self.log_msg("Retrieving customer metrics")
            
            from customer.models import Customer, Transaction
            
            total_customers = self.db.query(Customer).count()
            recent_customers = self.db.query(Customer).order_by(Customer.created_at.desc()).limit(5).count()
            
            return {
                "status": "success",
                "code": "CUSTOMER_METRICS_RETRIEVED",
                "message": "Customer metrics retrieved successfully.",
                "metrics": {
                    "total_customers": total_customers,
                    "recent_customers_7days": recent_customers,
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            log_exception(f"Error getting customer metrics: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "METRICS_ERROR", "message": str(e)}
    
    async def get_sales_analytics(self, request: AnalyticsRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Get sales-related analytics."""
        try:
            self.log_msg("Retrieving sales analytics")
            
            from customer.models import Opportunity
            
            total_opportunities = self.db.query(Opportunity).count()
            closed_opportunities = self.db.query(Opportunity).filter(Opportunity.stage == "closed_won").count()
            
            return {
                "status": "success",
                "code": "SALES_ANALYTICS_RETRIEVED",
                "message": "Sales analytics retrieved successfully.",
                "analytics": {
                    "total_opportunities": total_opportunities,
                    "closed_deals": closed_opportunities,
                    "win_rate": f"{((closed_opportunities / max(total_opportunities, 1)) * 100):.1f}%",
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            log_exception(f"Error getting sales analytics: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "ANALYTICS_ERROR", "message": str(e)}
    
    async def get_hr_analytics(self, request: AnalyticsRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Get HR-related analytics."""
        try:
            self.log_msg("Retrieving HR analytics")
            
            return {
                "status": "success",
                "code": "HR_ANALYTICS_RETRIEVED",
                "message": "HR analytics retrieved successfully.",
                "analytics": {
                    "total_employees": "Data from HR system",
                    "active_leaves": "Data from HR system",
                    "training_programs": "Data from HR system",
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            log_exception(f"Error getting HR analytics: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "HR_ANALYTICS_ERROR", "message": str(e)}
    
    async def get_transaction_analytics(self, request: AnalyticsRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Get transaction analytics."""
        try:
            self.log_msg("Retrieving transaction analytics")
            
            from customer.models import Transaction
            
            total_transactions = self.db.query(Transaction).count()
            
            # Apply date range filters if provided
            if request.date_range and request.date_range.get("date_from"):
                date_from = datetime.fromisoformat(request.date_range["date_from"])
                total_transactions = self.db.query(Transaction).filter(Transaction.timestamp >= date_from).count()
            
            return {
                "status": "success",
                "code": "TRANSACTION_ANALYTICS_RETRIEVED",
                "message": "Transaction analytics retrieved successfully.",
                "analytics": {
                    "total_transactions": total_transactions,
                    "period": f"{request.date_range.get('date_from', 'N/A')} to {request.date_range.get('date_to', 'N/A')}",
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            log_exception(f"Error getting transaction analytics: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "TRANSACTION_ANALYTICS_ERROR", "message": str(e)}
    
    async def get_generic_analytics(self, request: AnalyticsRequest, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle generic analytics requests."""
        try:
            self.log_msg(f"Processing generic analytics request")
            
            return {
                "status": "success",
                "code": "ANALYTICS_QUEUED",
                "message": "Analytics query has been queued for processing.",
                "request_id": f"ANALYTICS-{int(time.time())}"
            }
        except Exception as e:
            log_exception(f"Error in generic analytics: {str(e)}", self.tenant_id, self.conversation_id, user_id)
            return {"status": "error", "code": "ANALYTICS_ERROR", "message": str(e)}


# ==================================
# MAIN CHATBOT PROCESSOR
# ==================================

async def process_message(
    message_content: str,
    conversation_id: str,
    tenant_id: str,
    service_type: Optional[str] = None,
    file_path: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main message processor with service routing.
    Supports customer service, HR, CRM, and analytics.
    """
    start_time = time.time()
    
    try:
        log_info(f"Processing message for service: {service_type or 'GENERAL'}", tenant_id, conversation_id, user_id)
        
        # Store message in database
        try:
            db_session = SessionLocal()
            user_message = Message(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                content=message_content,
                message_type="user",
                user_id=user_id
            )
            db_session.add(user_message)
            db_session.commit()
            log_debug("Message stored in database", tenant_id, conversation_id, user_id)
        except Exception as db_err:
            log_warning(f"Failed to store message: {str(db_err)}", tenant_id, conversation_id, user_id)
        finally:
            db_session.close()
        
        # Route based on service type
        if service_type == ServiceType.CUSTOMER_SERVICE:
            cs_manager = CustomerServiceManager(tenant_id, conversation_id)
            # Parse the message to extract customer service details
            response = await cs_manager.handle_customer_service_request(
                CustomerServiceRequest(
                    customer_id=user_id or "unknown",
                    issue_type="inquiry",
                    priority="normal",
                    description=message_content
                ),
                user_id=user_id
            )
        elif service_type == ServiceType.HR_EMPLOYEE:
            hr_manager = HREmployeeManager(tenant_id, conversation_id)
            response = await hr_manager.handle_hr_request(
                HREmployeeRequest(
                    employee_id=user_id or "unknown",
                    request_type="inquiry",
                    details=message_content
                ),
                user_id=user_id
            )
        elif service_type == ServiceType.CRM:
            crm_manager = CRMManager(tenant_id, conversation_id)
            response = await crm_manager.handle_crm_operation(
                CRMRequest(
                    operation="fetch_account",
                    entity_type="Account",
                    data={"id": message_content}
                ),
                user_id=user_id
            )
        elif service_type == ServiceType.ANALYTICS:
            analytics_manager = AnalyticsManager(tenant_id, conversation_id)
            response = await analytics_manager.handle_analytics_request(
                AnalyticsRequest(
                    analysis_type="customer_metrics",
                    filters={}
                ),
                user_id=user_id
            )
        else:
            # Default: general chatbot response
            response = {
                "status": "success",
                "message": "I have received your message. How can I assist you further?",
                "service_type": "general"
            }
        
        duration = time.time() - start_time
        log_info(f"Message processed in {duration:.2f}s", tenant_id, conversation_id, user_id)
        
        return {
            **response,
            "metadata": {
                "processing_time": duration,
                "timestamp": datetime.now().isoformat(),
                "service": service_type or "general"
            }
        }
        
    except Exception as e:
        log_exception(f"Error processing message: {str(e)}", tenant_id, conversation_id, user_id)
        return {
            "status": "error",
            "code": "PROCESS_ERROR",
            "message": "An error occurred processing your message. Please try again.",
            "metadata": {
                "error_code": "PROCESS_ERROR",
                "timestamp": datetime.now().isoformat()
            }
        }


# ==================================
# VECTOR STORE FUNCTIONS
# ==================================

async def initialize_vector_store(tenant_id: str) -> tuple:
    """Initialize vector store for the tenant with proper error handling."""
    conversation_id = ""
    
    try:
        log_info("Initializing vector store", tenant_id, conversation_id)
        
        global embeddings
        
        # Initialize embeddings if not already done
        if embeddings is None:
            try:
                api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or GOOGLE_API_KEY
                log_debug("Initializing embeddings client", tenant_id, conversation_id)
                
                if not api_key:
                    raise ValueError("No API key found for embeddings")
                
                model = os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001")
                os.environ["GOOGLE_API_KEY"] = api_key
                
                embeddings = GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)
                log_info("Embeddings initialized successfully", tenant_id, conversation_id)
            except Exception as embed_err:
                log_warning(f"Failed to initialize embeddings: {str(embed_err)}", tenant_id, conversation_id)
                return None, {
                    "status": "warning",
                    "doc_count": 0,
                    "embedding_disabled": True,
                    "message": "Embeddings unavailable. RAG functionality limited."
                }
        
        # Get tenant configuration
        db_session = SessionLocal()
        try:
            tenant = db_session.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
            if not tenant:
                log_error(f"Tenant not found: {tenant_id}", tenant_id, conversation_id)
                return None, {"error": "Tenant not found"}
        finally:
            db_session.close()
        
        # Create vector store
        persist_directory = os.path.join("faiss_dbs", tenant_id)
        all_docs = []
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        
        # Process tenant text
        if tenant.tenant_text:
            log_debug("Processing tenant_text for vector store", tenant_id, conversation_id)
            text_chunks = text_splitter.split_text(tenant.tenant_text)
            for chunk in text_chunks:
                all_docs.append(
                    LangChainDocument(page_content=chunk, metadata={"source": "tenant_text"})
                )
        
        # Process tenant document
        if tenant.tenant_document and os.path.exists(str(tenant.tenant_document)):
            try:
                path = str(tenant.tenant_document)
                log_debug(f"Processing knowledge file: {os.path.basename(path)}", tenant_id, conversation_id)
                
                if path.lower().endswith(".pdf"):
                    loader = PyPDFLoader(path)
                elif path.lower().endswith(".txt"):
                    loader = TextLoader(path)
                elif path.lower().endswith(".csv"):
                    loader = CSVLoader(path)
                else:
                    loader = UnstructuredFileLoader(path)
                
                all_docs.extend(loader.load_and_split(text_splitter=text_splitter))
            except Exception as file_err:
                log_warning(f"Failed to process file: {str(file_err)}", tenant_id, conversation_id)
        
        # Create and save vector store
        if not all_docs:
            log_warning("No documentation found. Creating empty index.", tenant_id, conversation_id)
            vector_store = FAISS.from_texts([" "], embeddings)
        else:
            vector_store = FAISS.from_documents(all_docs, embeddings)
        
        os.makedirs(persist_directory, exist_ok=True)
        vector_store.save_local(persist_directory)
        
        log_info(f"Vector store initialized with {len(all_docs)} documents", tenant_id, conversation_id)
        return vector_store, {"status": "success", "doc_count": len(all_docs)}
        
    except Exception as e:
        log_exception(f"Error initializing vector store: {str(e)}", tenant_id, conversation_id)
        return None, {"status": "error", "message": str(e)}


# ==================================
# INITIALIZATION
# ==================================

def get_llm_instance(llm_config=None):
    """Get LLM instance from configuration."""
    try:
        if not llm_config:
            db_session = SessionLocal()
            try:
                llm_config = db_session.query(LLM).first()
            finally:
                db_session.close()
        
        if not llm_config:
            log_warning("No LLM configuration found. Using default.", GLOBAL_SCOPE, NO_CONVO)
            api_key = os.getenv("GEMINI_API_KEY")
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=api_key,
                temperature=0
            )
        
        name = (llm_config.name or "gemini").lower()
        
        if name == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            model_name = llm_config.model or "gemini-1.5-flash"
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0,
                convert_system_message_to_human=True
            )
        
        log_warning(f"Unknown LLM type: {name}. Using default.", GLOBAL_SCOPE, NO_CONVO)
        api_key = os.getenv("GEMINI_API_KEY")
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0
        )
    
    except Exception as e:
        log_exception(f"Error getting LLM instance: {str(e)}", GLOBAL_SCOPE, NO_CONVO)
        # Return a default instance
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0
        )


# Initialize LLM
llm = get_llm_instance()

# Log initialization completion
log_info("Chat bot module initialized successfully", GLOBAL_SCOPE, NO_CONVO)
