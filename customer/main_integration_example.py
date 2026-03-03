# ==================================
# INTEGRATION EXAMPLES FOR main.py
# ==================================

"""
This file demonstrates how to integrate the refactored chatbot services
into your existing main.py FastAPI application.

Complete the steps below to fully integrate all services.
"""

# ==================================
# STEP 1: UPDATE IMPORTS IN main.py
# ==================================

"""
Replace or add the following imports to your main.py:
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
import logging
from typing import Optional, Any

# Existing imports (keep these)
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# New imports for refactored service
from customer.chatbot_config import (
    ServiceConfig,
    setup_main_app,
    get_service_config
)
from customer.extended_views import router as service_router
from customer.chat_bot_refactored import (
    process_message,
    initialize_vector_store,
    ServiceType,
    get_llm_instance,
    log_info,
    log_error,
)
from database import SessionLocal, Tenant, init_db, LLM

# Existing imports
load_dotenv()


# ==================================
# STEP 2: INITIALIZE FASTAPI APP
# ==================================

"""
Update your app initialization:
"""

app = FastAPI(
    title=ServiceConfig.API_TITLE,
    version=ServiceConfig.API_VERSION,
    description="Integrated HR & Customer Service Chatbot with CRM and Analytics",
    docs_url="/docs" if ServiceConfig.ENABLE_SWAGGER_UI else None,
    redoc_url="/redoc" if ServiceConfig.ENABLE_SWAGGER_UI else None,
)

# Setup the app with all configurations
setup_main_app(app)

# Include the service router with all endpoints
app.include_router(service_router, prefix=ServiceConfig.API_PREFIX)

# Store config in app state for later access
app.state.service_config = get_service_config()


# ==================================
# STEP 3: ENHANCE EXISTING ENDPOINTS
# ==================================

"""
Update the existing /chat endpoint to support service routing:
"""

@app.post("/chat/")
async def chat_endpoint_enhanced(
    message_content: str = Form(..., description="User message"),
    conversation_id: str = Form(..., description="Conversation ID"),
    tenant_id: str = Form(..., description="Tenant ID"),
    service_type: Optional[str] = Form(None, description="Service type: customer_service, hr_employee, crm, analytics"),
    summarization_request: bool = Form(False, description="Request conversation summary"),
    user_id: Optional[str] = Form(None, description="User ID"),
    user_msg_attach: Optional[UploadFile] = File(None, description="Optional file attachment")
):
    """
    Enhanced chat endpoint that supports multiple services.
    
    Service Types:
    - customer_service: For customer support inquiries
    - hr_employee: For HR-related requests
    - crm: For CRM operations
    - analytics: For analytics queries
    - general (default): For general chatbot interaction
    """
    try:
        file_path = None
        if user_msg_attach:
            file_path = f"chat_attachments/{user_msg_attach.filename}"
            os.makedirs("chat_attachments", exist_ok=True)
            with open(file_path, "wb") as buffer:
                buffer.write(await user_msg_attach.read())
        
        # Route to appropriate service
        response = await process_message(
            message_content=message_content,
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            service_type=service_type or ServiceType.GENERAL,
            file_path=file_path,
            user_id=user_id,
        )
        
        return response
    
    except Exception as e:
        log_error(f"Chat error: {str(e)}", tenant_id, conversation_id, user_id)
        raise HTTPException(status_code=500, detail=str(e))


# ==================================
# STEP 4: STARTUP AND SHUTDOWN EVENTS
# ==================================

"""
Add startup and shutdown events to properly initialize services:
"""

@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup."""
    try:
        log_info("Starting up chatbot services...", "GLOBAL", "N/A")
        
        # Initialize database
        init_db()
        
        # Initialize LLM
        get_llm_instance()
        
        # Log service configuration
        config = get_service_config()
        log_info(f"Services initialized: {list(config.keys())}", "GLOBAL", "N/A")
        
        # Initialize vector stores for all tenants
        db = SessionLocal()
        try:
            tenants = db.query(Tenant).all()
            for tenant in tenants:
                try:
                    await initialize_vector_store(tenant.tenant_id)
                except Exception as tenant_err:
                    log_error(f"Failed to initialize vector store for {tenant.tenant_id}: {str(tenant_err)}", 
                             tenant.tenant_id, "N/A")
        finally:
            db.close()
        
        log_info("Startup complete - all services initialized", "GLOBAL", "N/A")
    
    except Exception as e:
        log_error(f"Startup error: {str(e)}", "GLOBAL", "N/A")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        log_info("Shutting down chatbot services...", "GLOBAL", "N/A")
        # Perform any cleanup needed
        log_info("Shutdown complete", "GLOBAL", "N/A")
    except Exception as e:
        log_error(f"Shutdown error: {str(e)}", "GLOBAL", "N/A")


# ==================================
# STEP 5: MIDDLEWARE CONFIGURATION
# ==================================

"""
Add middleware for logging and security:
"""

from fastapi.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

# Add middleware to track requests
@app.middleware("http")
async def add_request_logging(request, call_next):
    """Add request/response logging."""
    import time
    
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Log the request
    log_info(
        f"{request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration:.2f}s",
        "API",
        "N/A"
    )
    
    return response


# ==================================
# STEP 6: EXCEPTION HANDLERS
# ==================================

"""
Add global exception handlers:
"""

from fastapi import Request
from starlette.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging."""
    tenant_id = request.query_params.get("tenant_id", "UNKNOWN")
    conversation_id = request.query_params.get("conversation_id", "UNKNOWN")
    
    log_error(f"HTTP Exception: {exc.detail}", tenant_id, conversation_id)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": "HTTP_ERROR",
            "message": str(exc.detail),
            "path": str(request.url),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with proper logging."""
    tenant_id = request.query_params.get("tenant_id", "UNKNOWN")
    conversation_id = request.query_params.get("conversation_id", "UNKNOWN")
    
    log_error(f"Unhandled Exception: {str(exc)}", tenant_id, conversation_id)
    
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "path": str(request.url),
        },
    )


# ==================================
# STEP 7: UTILITY ENDPOINTS
# ==================================

"""
Add utility endpoints for service management:
"""

@app.get("/api/v1/service-config")
async def get_config_endpoint():
    """Get current service configuration."""
    try:
        return {
            "status": "success",
            "config": get_service_config(),
            "features": {
                "file_attachments": ServiceConfig.ENABLE_FILE_ATTACHMENTS,
                "real_time_notifications": ServiceConfig.ENABLE_REAL_TIME_NOTIFICATIONS,
                "advanced_analytics": ServiceConfig.ENABLE_ADVANCED_ANALYTICS,
            }
        }
    except Exception as e:
        log_error(f"Config endpoint error: {str(e)}", "API", "N/A")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/service-init/{tenant_id}")
async def initialize_service(tenant_id: str):
    """Initialize service for a specific tenant."""
    try:
        log_info(f"Initializing service for tenant {tenant_id}", tenant_id, "N/A")
        
        db = SessionLocal()
        try:
            tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")
        finally:
            db.close()
        
        vector_store, status = await initialize_vector_store(tenant_id)
        
        return {
            "status": status.get("status"),
            "message": f"Service initialization {status.get('status')}",
            "details": status,
            "tenant_id": tenant_id
        }
    
    except Exception as e:
        log_error(f"Service initialization error: {str(e)}", tenant_id, "N/A")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/service-stats")
async def get_service_stats():
    """Get service statistics and status."""
    try:
        db = SessionLocal()
        try:
            tenant_count = db.query(Tenant).count()
            llm_config = db.query(LLM).first()
        finally:
            db.close()
        
        return {
            "status": "operational",
            "services": {
                "customer_service": ServiceConfig.CUSTOMER_SERVICE_ENABLED,
                "hr_employee": ServiceConfig.HR_SERVICE_ENABLED,
                "crm": ServiceConfig.CRM_ENABLED,
                "analytics": ServiceConfig.ANALYTICS_ENABLED,
            },
            "statistics": {
                "total_tenants": tenant_count,
                "llm_configured": llm_config is not None,
                "llm_name": llm_config.name if llm_config else "None",
            },
            "timestamp": str(os.times())
        }
    except Exception as e:
        log_error(f"Stats endpoint error: {str(e)}", "API", "N/A")
        raise HTTPException(status_code=500, detail=str(e))


# ==================================
# STEP 8: TESTING FUNCTIONS
# ==================================

"""
Test functions to verify integration:
"""

async def test_customer_service():
    """Test customer service integration."""
    from customer.chat_bot_refactored import CustomerServiceRequest, CustomerServiceManager
    
    try:
        manager = CustomerServiceManager("test_tenant", "test_conv")
        request = CustomerServiceRequest(
            customer_id="test_cust",
            issue_type="inquiry",
            priority="normal",
            description="Test inquiry"
        )
        result = await manager.handle_customer_service_request(request, "test_user")
        print("✓ Customer Service Test Passed:", result)
    except Exception as e:
        print("✗ Customer Service Test Failed:", str(e))


async def test_hr_service():
    """Test HR service integration."""
    from customer.chat_bot_refactored import HREmployeeRequest, HREmployeeManager
    
    try:
        manager = HREmployeeManager("test_tenant", "test_conv")
        request = HREmployeeRequest(
            employee_id="test_emp",
            request_type="inquiry",
            details="Test HR inquiry"
        )
        result = await manager.handle_hr_request(request, "test_user")
        print("✓ HR Service Test Passed:", result)
    except Exception as e:
        print("✗ HR Service Test Failed:", str(e))


async def test_crm_service():
    """Test CRM service integration."""
    from customer.chat_bot_refactored import CRMRequest, CRMManager
    
    try:
        manager = CRMManager("test_tenant", "test_conv")
        request = CRMRequest(
            operation="create_account",
            entity_type="Account",
            data={"name": "Test Account", "industry": "Tech"}
        )
        result = await manager.handle_crm_operation(request, "test_user")
        print("✓ CRM Service Test Passed:", result)
    except Exception as e:
        print("✗ CRM Service Test Failed:", str(e))


async def test_analytics_service():
    """Test analytics service integration."""
    from customer.chat_bot_refactored import AnalyticsRequest, AnalyticsManager
    
    try:
        manager = AnalyticsManager("test_tenant", "test_conv")
        request = AnalyticsRequest(
            analysis_type="customer_metrics",
            filters={}
        )
        result = await manager.handle_analytics_request(request, "test_user")
        print("✓ Analytics Service Test Passed:", result)
    except Exception as e:
        print("✗ Analytics Service Test Failed:", str(e))


@app.get("/api/v1/test-services")
async def test_all_services():
    """Test all services - development only."""
    if ServiceConfig.LOG_LEVEL.upper() != "DEBUG":
        raise HTTPException(status_code=403, detail="Test endpoint only available in debug mode")
    
    try:
        await test_customer_service()
        await test_hr_service()
        await test_crm_service()
        await test_analytics_service()
        
        return {
            "status": "success",
            "message": "All service tests completed",
            "check_console_output": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================================
# STEP 9: RUN THE APPLICATION
# ==================================

"""
Run the application with:

    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Test endpoints with:

    # Health check
    curl http://localhost:8000/api/v1/health
    
    # Service config
    curl http://localhost:8000/api/v1/service-config
    
    # Service stats
    curl http://localhost:8000/api/v1/service-stats
    
    # Customer service
    curl -X POST http://localhost:8000/api/v1/customer-service/inquiry \
      -F "customer_id=CUST001" \
      -F "conversation_id=CONV001" \
      -F "tenant_id=TENANT001" \
      -F "issue_type=complaint" \
      -F "priority=high" \
      -F "description=Test"
    
    # HR service
    curl -X POST http://localhost:8000/api/v1/hr/leave-request \
      -F "employee_id=EMP001" \
      -F "conversation_id=CONV001" \
      -F "tenant_id=TENANT001" \
      -F "leave_type=annual" \
      -F "start_date=2026-03-15" \
      -F "end_date=2026-03-20" \
      -F "reason=Vacation"
"""


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT", "development") == "development"
    )
