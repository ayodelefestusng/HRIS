# ==================================
# CHATBOT SERVICE CONFIGURATION
# ==================================

"""
This module provides configuration settings for the refactored chatbot system.
It integrates with main.py and ensures proper initialization of all services.
"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseModel

# ==================================
# SERVICE CONFIGURATION
# ==================================

class ServiceConfig:
    """Central configuration for all chatbot services."""
    
    # Customer Service Settings
    CUSTOMER_SERVICE_ENABLED = os.getenv("CUSTOMER_SERVICE_ENABLED", "true").lower() == "true"
    CUSTOMER_SERVICE_PRIORITY_LEVELS = ["low", "normal", "high", "critical"]
    CUSTOMER_SERVICE_ISSUE_TYPES = ["complaint", "inquiry", "transaction", "account"]
    CUSTOMER_SERVICE_ESCALATION_WAIT_MINUTES = int(os.getenv("CUSTOMER_SERVICE_ESCALATION_WAIT_MINUTES", "30"))
    
    # HR Employee Service Settings
    HR_SERVICE_ENABLED = os.getenv("HR_SERVICE_ENABLED", "true").lower() == "true"
    HR_REQUEST_TYPES = ["leave", "payroll", "benefits", "training", "complaint"]
    HR_LEAVE_TYPES = ["annual", "sick", "personal", "unpaid"]
    HR_APPROVAL_WAIT_HOURS = int(os.getenv("HR_APPROVAL_WAIT_HOURS", "48"))
    
    # CRM Settings
    CRM_ENABLED = os.getenv("CRM_ENABLED", "true").lower() == "true"
    CRM_OPERATIONS = ["create_account", "create_lead", "update_contact", "update_opportunity", "fetch_account", "fetch_leads"]
    CRM_ENTITY_TYPES = ["Account", "Contact", "Lead", "Opportunity"]
    
    # Analytics Settings
    ANALYTICS_ENABLED = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"
    ANALYTICS_TYPES = ["customer_metrics", "sales_analytics", "hr_analytics", "transaction_analytics"]
    ANALYTICS_DEFAULT_DAYS = int(os.getenv("ANALYTICS_DEFAULT_DAYS", "30"))
    
    # Database Settings
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///ai_database.sqlite3")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "hr_chatbot_db")
    
    # Redis Cache Settings (optional)
    REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_CACHE_TTL_SECONDS = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "3600"))
    
    # Logging Settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    LOG_FILE = os.getenv("LOG_FILE", "chatbot_refactored.log")
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "5242880"))  # 5MB
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    # API Settings
    API_PREFIX = os.getenv("API_PREFIX", "/api/v1")
    API_TITLE = os.getenv("API_TITLE", "HR & Customer Service Chatbot API")
    API_VERSION = os.getenv("API_VERSION", "1.0.0")
    
    # LLM Settings
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Vector Store Settings
    VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE_TYPE", "faiss")
    VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", "./faiss_dbs")
    
    # Security Settings
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
    ENABLE_SWAGGER_UI = os.getenv("ENABLE_SWAGGER_UI", "true").lower() == "true"
    
    # Feature Flags
    ENABLE_FILE_ATTACHMENTS = os.getenv("ENABLE_FILE_ATTACHMENTS", "true").lower() == "true"
    MAX_ATTACHMENT_SIZE_MB = int(os.getenv("MAX_ATTACHMENT_SIZE_MB", "10"))
    ENABLE_REAL_TIME_NOTIFICATIONS = os.getenv("ENABLE_REAL_TIME_NOTIFICATIONS", "false").lower() == "true"
    ENABLE_ADVANCED_ANALYTICS = os.getenv("ENABLE_ADVANCED_ANALYTICS", "true").lower() == "true"


# ==================================
# INTEGRATION WITH MAIN.PY
# ==================================

def get_service_config() -> Dict[str, Any]:
    """
    Returns the complete service configuration for main.py integration.
    
    Usage in main.py:
    ```python
    from customer.chatbot_config import get_service_config
    
    service_config = get_service_config()
    app.state.config = service_config
    ```
    """
    return {
        "customer_service": {
            "enabled": ServiceConfig.CUSTOMER_SERVICE_ENABLED,
            "priority_levels": ServiceConfig.CUSTOMER_SERVICE_PRIORITY_LEVELS,
            "issue_types": ServiceConfig.CUSTOMER_SERVICE_ISSUE_TYPES,
            "escalation_wait_minutes": ServiceConfig.CUSTOMER_SERVICE_ESCALATION_WAIT_MINUTES,
        },
        "hr_service": {
            "enabled": ServiceConfig.HR_SERVICE_ENABLED,
            "request_types": ServiceConfig.HR_REQUEST_TYPES,
            "leave_types": ServiceConfig.HR_LEAVE_TYPES,
            "approval_wait_hours": ServiceConfig.HR_APPROVAL_WAIT_HOURS,
        },
        "crm": {
            "enabled": ServiceConfig.CRM_ENABLED,
            "operations": ServiceConfig.CRM_OPERATIONS,
            "entity_types": ServiceConfig.CRM_ENTITY_TYPES,
        },
        "analytics": {
            "enabled": ServiceConfig.ANALYTICS_ENABLED,
            "types": ServiceConfig.ANALYTICS_TYPES,
            "default_days": ServiceConfig.ANALYTICS_DEFAULT_DAYS,
        },
        "database": {
            "primary_url": ServiceConfig.DATABASE_URL,
            "mongodb_uri": ServiceConfig.MONGO_URI,
            "mongodb_db": ServiceConfig.MONGO_DB_NAME,
        },
        "cache": {
            "redis_enabled": ServiceConfig.REDIS_ENABLED,
            "redis_url": ServiceConfig.REDIS_URL,
            "ttl_seconds": ServiceConfig.REDIS_CACHE_TTL_SECONDS,
        },
        "api": {
            "prefix": ServiceConfig.API_PREFIX,
            "title": ServiceConfig.API_TITLE,
            "version": ServiceConfig.API_VERSION,
        },
    }


def setup_main_app(app):
    """
    Setup function to call from main.py to configure the app with all services.
    
    Usage in main.py:
    ```python
    from fastapi import FastAPI
    from customer.chatbot_config import setup_main_app
    from customer.extended_views import router
    
    app = FastAPI(title=ServiceConfig.API_TITLE, version=ServiceConfig.API_VERSION)
    setup_main_app(app)
    app.include_router(router, prefix=ServiceConfig.API_PREFIX)
    ```
    """
    from fastapi.middleware.cors import CORSMiddleware
    
    # Configure CORS
    cors_origins = ServiceConfig.CORS_ORIGINS.split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Store configuration in app state
    app.state.config = get_service_config()
    
    # Set up logging
    import logging
    from logging.handlers import RotatingFileHandler
    import os
    
    os.makedirs(ServiceConfig.LOG_DIR, exist_ok=True)
    log_path = os.path.join(ServiceConfig.LOG_DIR, ServiceConfig.LOG_FILE)
    
    handler = RotatingFileHandler(
        log_path,
        maxBytes=ServiceConfig.LOG_MAX_BYTES,
        backupCount=ServiceConfig.LOG_BACKUP_COUNT
    )
    
    logger = logging.getLogger("chatbot_services")
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, ServiceConfig.LOG_LEVEL))
    
    return app


# ==================================
# ENVIRONMENT VARIABLES TEMPLATE
# ==================================

"""
Copy this to your .env file and fill in the values:

# Customer Service Settings
CUSTOMER_SERVICE_ENABLED=true
CUSTOMER_SERVICE_ESCALATION_WAIT_MINUTES=30

# HR Service Settings
HR_SERVICE_ENABLED=true
HR_APPROVAL_WAIT_HOURS=48

# CRM Settings
CRM_ENABLED=true

# Analytics Settings
ANALYTICS_ENABLED=true
ANALYTICS_DEFAULT_DAYS=30

# Database Settings
DATABASE_URL=sqlite:///ai_database.sqlite3
# or for PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/hr_db

# MongoDB Settings (optional)
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=hr_chatbot_db

# Redis Settings (optional)
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL_SECONDS=3600

# Logging Settings
LOG_LEVEL=INFO
LOG_DIR=logs
LOG_FILE=chatbot_refactored.log
LOG_MAX_BYTES=5242880
LOG_BACKUP_COUNT=5

# API Settings
API_PREFIX=/api/v1
API_TITLE=HR & Customer Service Chatbot API
API_VERSION=1.0.0

# LLM Settings
GEMINI_API_KEY=your-gemini-api-key
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL=gemini-1.5-flash
OLLAMA_BASE_URL=http://localhost:11434

# Vector Store Settings
VECTOR_STORE_TYPE=faiss
VECTOR_STORE_PATH=./faiss_dbs

# Security Settings
SECRET_KEY=your-secret-key-change-in-production
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
ENABLE_SWAGGER_UI=true

# Feature Flags
ENABLE_FILE_ATTACHMENTS=true
MAX_ATTACHMENT_SIZE_MB=10
ENABLE_REAL_TIME_NOTIFICATIONS=false
ENABLE_ADVANCED_ANALYTICS=true

# Tenant and Application Settings
FALLBACK_LLM_NAME=ollama_cloud
FALLBACK_LLM_MODEL=gpt-oss:120b
"""


# ==================================
# INTEGRATION CHECKLIST
# ==================================

"""
INTEGRATION CHECKLIST for main.py
==================================

1. Import Configuration
   [ ] from customer.chatbot_config import ServiceConfig, setup_main_app
   [ ] from customer.extended_views import router as service_router

2. Create FastAPI App
   [ ] app = FastAPI(
         title=ServiceConfig.API_TITLE,
         version=ServiceConfig.API_VERSION
       )

3. Setup Services
   [ ] setup_main_app(app)

4. Include Router
   [ ] app.include_router(service_router, prefix=ServiceConfig.API_PREFIX)

5. Startup Events
   [ ] Add @app.on_event("startup") to initialize services
   [ ] Initialize vector stores for tenants
   [ ] Load LLM configurations

6. Health Check
   [ ] Test GET /api/v1/health

7. Test Endpoints
   [ ] Test customer service endpoints
   [ ] Test HR endpoints
   [ ] Test CRM endpoints
   [ ] Test analytics endpoints

8. Monitor Logs
   [ ] Check logs/chatbot_refactored.log for errors
   [ ] Verify all services initialized correctly
   [ ] Monitor performance metrics

9. Database Setup
   [ ] Ensure database migrations are applied
   [ ] Verify MongoDB collections created (if using)
   [ ] Verify all indexes created

10. Production Deployment
    [ ] Update SECRET_KEY in environment
    [ ] Configure proper CORS_ORIGINS
    [ ] Set LOG_LEVEL appropriately
    [ ] Configure database connection pooling
    [ ] Enable Redis caching (optional but recommended)
    [ ] Set up monitoring and alerts
    [ ] Configure backup and disaster recovery
"""
