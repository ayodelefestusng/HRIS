# ==================================
# EXTENDED URL CONFIGURATION
# ==================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the extended views router
from .extended_views import router as service_router
from .views import CRMPipelineView

app_name = "customer"

# Django URL patterns
django_urlpatterns = [
    # CRM Pipeline View
    path('crm/pipeline/', CRMPipelineView.as_view(), name='crm_pipeline'),
]

# FastAPI integration routes (if using FastAPI alongside Django)
# These would be integrated into a FastAPI app instance in main.py

fastapi_routes = {
    "customer_service": [
        "POST /api/v1/customer-service/inquiry",
        "POST /api/v1/customer-service/message",
    ],
    "hr_employee": [
        "POST /api/v1/hr/leave-request",
        "POST /api/v1/hr/benefits-inquiry",
        "POST /api/v1/hr/message",
    ],
    "crm": [
        "POST /api/v1/crm/account",
        "POST /api/v1/crm/lead",
        "GET /api/v1/crm/leads",
    ],
    "analytics": [
        "GET /api/v1/analytics/customer-metrics",
        "GET /api/v1/analytics/sales",
        "GET /api/v1/analytics/hr",
        "GET /api/v1/analytics/transactions",
    ],
    "utility": [
        "POST /api/v1/service-initialize/{tenant_id}",
        "GET /api/v1/health",
    ]
}

# URL configuration documentation
"""
CUSTOMER SERVICE ROUTES:
========================
1. POST /api/v1/customer-service/inquiry
   - Submit customer service inquiry or complaint
   - Parameters: customer_id, conversation_id, tenant_id, issue_type, priority, description
   - Response: ServiceResponse with status and reference_id

2. POST /api/v1/customer-service/message
   - Send general customer service message
   - Parameters: message_content, conversation_id, tenant_id, service_type, user_id
   - Response: ServiceResponse with processed message

HR EMPLOYEE ROUTES:
===================
1. POST /api/v1/hr/leave-request
   - Submit leave/time-off request
   - Parameters: employee_id, conversation_id, tenant_id, leave_type, start_date, end_date, reason
   - Response: ServiceResponse with request_id

2. POST /api/v1/hr/benefits-inquiry
   - Inquire about employee benefits
   - Parameters: employee_id, conversation_id, tenant_id, inquiry_topic
   - Response: ServiceResponse with benefits information

3. POST /api/v1/hr/message
   - Send general HR message
   - Parameters: message_content, conversation_id, tenant_id, service_type, user_id
   - Response: ServiceResponse with processed message

CRM ROUTES:
===========
1. POST /api/v1/crm/account
   - Create or update CRM account
   - Parameters: conversation_id, tenant_id, account_id (optional), account_name, industry, website, phone
   - Response: ServiceResponse with account_id

2. POST /api/v1/crm/lead
   - Create new lead
   - Parameters: conversation_id, tenant_id, first_name, last_name, email, company, phone
   - Response: ServiceResponse with lead_id

3. GET /api/v1/crm/leads
   - Fetch leads with filters
   - Query Parameters: conversation_id, tenant_id, status (optional), source (optional)
   - Response: ServiceResponse with list of leads

ANALYTICS ROUTES:
=================
1. GET /api/v1/analytics/customer-metrics
   - Get customer metrics and analytics
   - Query Parameters: conversation_id, tenant_id
   - Response: ServiceResponse with customer metrics

2. GET /api/v1/analytics/sales
   - Get sales analytics
   - Query Parameters: conversation_id, tenant_id
   - Response: ServiceResponse with sales metrics

3. GET /api/v1/analytics/hr
   - Get HR analytics
   - Query Parameters: conversation_id, tenant_id
   - Response: ServiceResponse with HR metrics

4. GET /api/v1/analytics/transactions
   - Get transaction analytics
   - Query Parameters: conversation_id, tenant_id, date_from, date_to
   - Response: ServiceResponse with transaction metrics

UTILITY ROUTES:
===============
1. POST /api/v1/service-initialize/{tenant_id}
   - Initialize services for a tenant
   - Response: ServiceResponse with initialization status

2. GET /api/v1/health
   - Health check endpoint
   - Response: Health status JSON

DATABASE MODELS MAPPING:
======================
The extended views integrate with the following models defined in customer/models.py:

CRM Models:
- Account: Company/organization accounts
- Contact: Individual contacts linked to accounts
- Lead: Sales leads
- Opportunity: Sales opportunities (managed in workflow)
- CRMUser: CRM-specific user profile

Transaction Models:
- Customer: Customer profile
- Transaction: Transaction history

The models are automatically traced and updated through the respective service managers
(CustomerServiceManager, CRMManager, AnalyticsManager, HREmployeeManager).
"""

# Export URL patterns for Django
urlpatterns = django_urlpatterns

# This module is imported in main.py and the router is included in the FastAPI app:
# app.include_router(router, prefix="/api/v1")
