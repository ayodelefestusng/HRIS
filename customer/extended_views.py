# ==================================
# EXTENDED VIEWS WITH SERVICE ROUTING
# ==================================

import logging
import traceback
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Form, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel

from chat_bot_refactored import (
    process_message,
    initialize_vector_store,
    CustomerServiceManager,
    HREmployeeManager,
    CRMManager,
    AnalyticsManager,
    CustomerServiceRequest,
    HREmployeeRequest,
    CRMRequest,
    AnalyticsRequest,
    ServiceType,
    log_info,
    log_error,
    log_warning,
    log_exception,
    log_debug,
)
from database import SessionLocal, Tenant

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1", tags=["chat_services"])

# ==================================
# REQUEST/RESPONSE SCHEMAS
# ==================================

class ServiceMessageRequest(BaseModel):
    """Request for any service message."""
    message_content: str
    conversation_id: str
    tenant_id: str
    service_type: Optional[str] = None
    user_id: Optional[str] = None

class ServiceResponse(BaseModel):
    """Standard response for service requests."""
    status: str
    code: str
    message: str
    data: Optional[dict] = None
    metadata: Optional[dict] = None

# ==================================
# CUSTOMER SERVICE ENDPOINTS
# ==================================

@router.post("/customer-service/inquiry",
    summary="Customer Service Inquiry",
    description="Submit a customer service inquiry or complaint",
    response_model=ServiceResponse)
async def customer_service_inquiry(
    customer_id: str = Form(..., description="Customer ID"),
    conversation_id: str = Form(..., description="Conversation ID"),
    tenant_id: str = Form(..., description="Tenant ID"),
    issue_type: str = Form("inquiry", description="Type: complaint, inquiry, transaction, account"),
    priority: str = Form("normal", description="Priority: low, normal, high, critical"),
    description: str = Form(..., description="Issue description"),
    user_id: Optional[str] = Form(None, description="User ID"),
    attachment: Optional[UploadFile] = File(None, description="Optional attachment")
):
    """Handle customer service inquiries and complaints."""
    try:
        log_info(f"Customer service inquiry received: {issue_type}", tenant_id, conversation_id, user_id)
        
        # Handle file attachment if provided
        file_path = None
        if attachment:
            file_path = f"customer_service_attachments/{attachment.filename}"
            try:
                import os
                os.makedirs("customer_service_attachments", exist_ok=True)
                with open(file_path, "wb") as f:
                    f.write(await attachment.read())
            except Exception as e:
                log_warning(f"Failed to save attachment: {str(e)}", tenant_id, conversation_id, user_id)
        
        # Process request
        cs_manager = CustomerServiceManager(tenant_id, conversation_id)
        request = CustomerServiceRequest(
            customer_id=customer_id,
            issue_type=issue_type,
            priority=priority,
            description=description,
            attachment=file_path
        )
        
        result = await cs_manager.handle_customer_service_request(request, user_id)
        
        return ServiceResponse(
            status=result.get("status"),
            code=result.get("code"),
            message=result.get("message"),
            data=result,
            metadata={"timestamp": datetime.now().isoformat()}
        )
    
    except Exception as e:
        log_exception(f"Error in customer service endpoint: {str(e)}", tenant_id, conversation_id, user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/customer-service/message",
    summary="Send Customer Service Message",
    description="Send a general message to customer service",
    response_model=ServiceResponse)
async def send_customer_service_message(
    request: ServiceMessageRequest
):
    """Route message through customer service handler."""
    try:
        log_info("Customer service message request", request.tenant_id, request.conversation_id, request.user_id)
        
        response = await process_message(
            message_content=request.message_content,
            conversation_id=request.conversation_id,
            tenant_id=request.tenant_id,
            service_type=ServiceType.CUSTOMER_SERVICE,
            user_id=request.user_id
        )
        
        return ServiceResponse(
            status=response.get("status"),
            code=response.get("code", "CS_MESSAGE_PROCESSED"),
            message=response.get("message"),
            data=response,
            metadata=response.get("metadata")
        )
    
    except Exception as e:
        log_exception(f"Error in customer service message: {str(e)}", request.tenant_id, request.conversation_id, request.user_id)
        raise HTTPException(status_code=500, detail=str(e))


# ==================================
# HR EMPLOYEE ENDPOINTS
# ==================================

@router.post("/hr/leave-request",
    summary="Submit Leave Request",
    description="Submit a leave or time-off request",
    response_model=ServiceResponse)
async def submit_leave_request(
    employee_id: str = Form(..., description="Employee ID"),
    conversation_id: str = Form(..., description="Conversation ID"),
    tenant_id: str = Form(..., description="Tenant ID"),
    leave_type: str = Form(..., description="Type: annual, sick, personal, unpaid"),
    start_date: str = Form(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Form(..., description="End date (YYYY-MM-DD)"),
    reason: str = Form(..., description="Reason for leave"),
    user_id: Optional[str] = Form(None, description="User ID")
):
    """Handle leave requests."""
    try:
        log_info(f"Leave request received: {leave_type}", tenant_id, conversation_id, user_id)
        
        hr_manager = HREmployeeManager(tenant_id, conversation_id)
        request = HREmployeeRequest(
            employee_id=employee_id,
            request_type="leave",
            details=f"Leave Type: {leave_type}\nStart: {start_date}\nEnd: {end_date}\nReason: {reason}"
        )
        
        result = await hr_manager.handle_hr_request(request, user_id)
        
        return ServiceResponse(
            status=result.get("status"),
            code=result.get("code"),
            message=result.get("message"),
            data=result,
            metadata={"timestamp": datetime.now().isoformat()}
        )
    
    except Exception as e:
        log_exception(f"Error in leave request: {str(e)}", tenant_id, conversation_id, user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hr/benefits-inquiry",
    summary="Benefits Inquiry",
    description="Inquire about employee benefits",
    response_model=ServiceResponse)
async def benefits_inquiry(
    employee_id: str = Form(..., description="Employee ID"),
    conversation_id: str = Form(..., description="Conversation ID"),
    tenant_id: str = Form(..., description="Tenant ID"),
    inquiry_topic: str = Form(..., description="Benefit topic to inquire about"),
    user_id: Optional[str] = Form(None, description="User ID")
):
    """Handle benefits inquiries."""
    try:
        log_info(f"Benefits inquiry: {inquiry_topic}", tenant_id, conversation_id, user_id)
        
        hr_manager = HREmployeeManager(tenant_id, conversation_id)
        request = HREmployeeRequest(
            employee_id=employee_id,
            request_type="benefits",
            details=inquiry_topic
        )
        
        result = await hr_manager.handle_hr_request(request, user_id)
        
        return ServiceResponse(
            status=result.get("status"),
            code=result.get("code"),
            message=result.get("message"),
            data=result,
            metadata={"timestamp": datetime.now().isoformat()}
        )
    
    except Exception as e:
        log_exception(f"Error in benefits inquiry: {str(e)}", tenant_id, conversation_id, user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hr/message",
    summary="Send HR Message",
    description="Send a general message to HR service",
    response_model=ServiceResponse)
async def send_hr_message(
    request: ServiceMessageRequest
):
    """Route message through HR handler."""
    try:
        log_info("HR message request", request.tenant_id, request.conversation_id, request.user_id)
        
        response = await process_message(
            message_content=request.message_content,
            conversation_id=request.conversation_id,
            tenant_id=request.tenant_id,
            service_type=ServiceType.HR_EMPLOYEE,
            user_id=request.user_id
        )
        
        return ServiceResponse(
            status=response.get("status"),
            code=response.get("code", "HR_MESSAGE_PROCESSED"),
            message=response.get("message"),
            data=response,
            metadata=response.get("metadata")
        )
    
    except Exception as e:
        log_exception(f"Error in HR message: {str(e)}", request.tenant_id, request.conversation_id, request.user_id)
        raise HTTPException(status_code=500, detail=str(e))


# ==================================
# CRM ENDPOINTS
# ==================================

@router.post("/crm/account",
    summary="Create/Update Account",
    description="Create or update CRM account",
    response_model=ServiceResponse)
async def manage_account(
    conversation_id: str = Form(..., description="Conversation ID"),
    tenant_id: str = Form(..., description="Tenant ID"),
    account_id: Optional[str] = Form(None, description="Account ID for updates"),
    account_name: str = Form(..., description="Account name"),
    industry: Optional[str] = Form(None, description="Industry"),
    website: Optional[str] = Form(None, description="Website URL"),
    phone: Optional[str] = Form(None, description="Phone"),
    user_id: Optional[str] = Form(None, description="User ID")
):
    """Manage CRM accounts."""
    try:
        log_info(f"CRM account operation: {account_name}", tenant_id, conversation_id, user_id)
        
        crm_manager = CRMManager(tenant_id, conversation_id)
        
        operation = "create_account" if not account_id else "update_account"
        data = {
            "name": account_name,
            "industry": industry,
            "website": website,
            "phone": phone,
        }
        if account_id:
            data["id"] = account_id
        
        request = CRMRequest(
            operation=operation,
            entity_type="Account",
            data=data
        )
        
        result = await crm_manager.handle_crm_operation(request, user_id)
        
        return ServiceResponse(
            status=result.get("status"),
            code=result.get("code"),
            message=result.get("message"),
            data=result,
            metadata={"timestamp": datetime.now().isoformat()}
        )
    
    except Exception as e:
        log_exception(f"Error managing CRM account: {str(e)}", tenant_id, conversation_id, user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crm/lead",
    summary="Create Lead",
    description="Create a new CRM lead",
    response_model=ServiceResponse)
async def create_lead(
    conversation_id: str = Form(..., description="Conversation ID"),
    tenant_id: str = Form(..., description="Tenant ID"),
    first_name: str = Form(..., description="First name"),
    last_name: str = Form(..., description="Last name"),
    email: str = Form(..., description="Email"),
    company: str = Form(..., description="Company"),
    phone: Optional[str] = Form(None, description="Phone"),
    user_id: Optional[str] = Form(None, description="User ID")
):
    """Create a new lead."""
    try:
        log_info(f"Creating lead: {first_name} {last_name}", tenant_id, conversation_id, user_id)
        
        crm_manager = CRMManager(tenant_id, conversation_id)
        request = CRMRequest(
            operation="create_lead",
            entity_type="Lead",
            data={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "company": company,
                "phone": phone,
                "lead_status": "new",
                "lead_source": "api"
            }
        )
        
        result = await crm_manager.handle_crm_operation(request, user_id)
        
        return ServiceResponse(
            status=result.get("status"),
            code=result.get("code"),
            message=result.get("message"),
            data=result,
            metadata={"timestamp": datetime.now().isoformat()}
        )
    
    except Exception as e:
        log_exception(f"Error creating lead: {str(e)}", tenant_id, conversation_id, user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/crm/leads",
    summary="Fetch Leads",
    description="Fetch leads with optional filters",
    response_model=ServiceResponse)
async def fetch_leads(
    conversation_id: str,
    tenant_id: str,
    status: Optional[str] = None,
    source: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Fetch leads with filters."""
    try:
        log_info("Fetching leads", tenant_id, conversation_id, user_id)
        
        crm_manager = CRMManager(tenant_id, conversation_id)
        request = CRMRequest(
            operation="fetch_leads",
            entity_type="Lead",
            data={"status": status, "source": source, "limit": 10}
        )
        
        result = await crm_manager.handle_crm_operation(request, user_id)
        
        return ServiceResponse(
            status=result.get("status"),
            code=result.get("code"),
            message=result.get("message"),
            data=result,
            metadata={"timestamp": datetime.now().isoformat()}
        )
    
    except Exception as e:
        log_exception(f"Error fetching leads: {str(e)}", tenant_id, conversation_id, user_id)
        raise HTTPException(status_code=500, detail=str(e))


# ==================================
# ANALYTICS ENDPOINTS
# ==================================

@router.get("/analytics/customer-metrics",
    summary="Customer Metrics",
    description="Get customer-related metrics and analytics",
    response_model=ServiceResponse)
async def get_customer_metrics(
    conversation_id: str,
    tenant_id: str,
    user_id: Optional[str] = None
):
    """Get customer metrics."""
    try:
        log_info("Fetching customer metrics", tenant_id, conversation_id, user_id)
        
        analytics_manager = AnalyticsManager(tenant_id, conversation_id)
        request = AnalyticsRequest(
            analysis_type="customer_metrics",
            filters={}
        )
        
        result = await analytics_manager.handle_analytics_request(request, user_id)
        
        return ServiceResponse(
            status=result.get("status"),
            code=result.get("code"),
            message=result.get("message"),
            data=result,
            metadata={"timestamp": datetime.now().isoformat()}
        )
    
    except Exception as e:
        log_exception(f"Error fetching customer metrics: {str(e)}", tenant_id, conversation_id, user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/sales",
    summary="Sales Analytics",
    description="Get sales-related analytics",
    response_model=ServiceResponse)
async def get_sales_analytics(
    conversation_id: str,
    tenant_id: str,
    user_id: Optional[str] = None
):
    """Get sales analytics."""
    try:
        log_info("Fetching sales analytics", tenant_id, conversation_id, user_id)
        
        analytics_manager = AnalyticsManager(tenant_id, conversation_id)
        request = AnalyticsRequest(
            analysis_type="sales_analytics",
            filters={}
        )
        
        result = await analytics_manager.handle_analytics_request(request, user_id)
        
        return ServiceResponse(
            status=result.get("status"),
            code=result.get("code"),
            message=result.get("message"),
            data=result,
            metadata={"timestamp": datetime.now().isoformat()}
        )
    
    except Exception as e:
        log_exception(f"Error fetching sales analytics: {str(e)}", tenant_id, conversation_id, user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/hr",
    summary="HR Analytics",
    description="Get HR-related analytics",
    response_model=ServiceResponse)
async def get_hr_analytics(
    conversation_id: str,
    tenant_id: str,
    user_id: Optional[str] = None
):
    """Get HR analytics."""
    try:
        log_info("Fetching HR analytics", tenant_id, conversation_id, user_id)
        
        analytics_manager = AnalyticsManager(tenant_id, conversation_id)
        request = AnalyticsRequest(
            analysis_type="hr_analytics",
            filters={}
        )
        
        result = await analytics_manager.handle_analytics_request(request, user_id)
        
        return ServiceResponse(
            status=result.get("status"),
            code=result.get("code"),
            message=result.get("message"),
            data=result,
            metadata={"timestamp": datetime.now().isoformat()}
        )
    
    except Exception as e:
        log_exception(f"Error fetching HR analytics: {str(e)}", tenant_id, conversation_id, user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/transactions",
    summary="Transaction Analytics",
    description="Get transaction analytics and insights",
    response_model=ServiceResponse)
async def get_transaction_analytics(
    conversation_id: str,
    tenant_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Get transaction analytics."""
    try:
        log_info("Fetching transaction analytics", tenant_id, conversation_id, user_id)
        
        analytics_manager = AnalyticsManager(tenant_id, conversation_id)
        request = AnalyticsRequest(
            analysis_type="transaction_analytics",
            date_range={"date_from": date_from, "date_to": date_to},
            filters={}
        )
        
        result = await analytics_manager.handle_analytics_request(request, user_id)
        
        return ServiceResponse(
            status=result.get("status"),
            code=result.get("code"),
            message=result.get("message"),
            data=result,
            metadata={"timestamp": datetime.now().isoformat()}
        )
    
    except Exception as e:
        log_exception(f"Error fetching transaction analytics: {str(e)}", tenant_id, conversation_id, user_id)
        raise HTTPException(status_code=500, detail=str(e))


# ==================================
# UTILITY ENDPOINTS
# ==================================

@router.post("/service-initialize/{tenant_id}",
    summary="Initialize Service for Tenant",
    description="Initialize vector store and services for a tenant",
    response_model=ServiceResponse)
async def initialize_tenant_service(
    tenant_id: str
):
    """Initialize tenant service."""
    try:
        log_info(f"Initializing service for tenant", tenant_id, "N/A")
        
        vector_store, status = await initialize_vector_store(tenant_id)
        
        return ServiceResponse(
            status=status.get("status"),
            code=status.get("status"),
            message=f"Service initialization {status.get('status')}",
            data=status,
            metadata={"timestamp": datetime.now().isoformat()}
        )
    
    except Exception as e:
        log_exception(f"Error initializing tenant service: {str(e)}", tenant_id, "N/A")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health",
    summary="Health Check",
    description="Check service health status")
async def health_check():
    """Service health check."""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "customer_service": "operational",
                "hr_employee": "operational",
                "crm": "operational",
                "analytics": "operational"
            }
        }
    except Exception as e:
        log_error(f"Health check failed: {str(e)}", "GLOBAL", "N/A")
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "error": str(e)}
        )
