# CHATBOT REFACTORING GUIDE
# ===========================

## Overview

This document describes the complete refactoring of the chatbot system to support:
1. **Customer Service** - Issue handling, complaints, inquiries
2. **HR Employee Services** - Leave requests, benefits, payroll inquiries
3. **Customer Relationship Management (CRM)** - Account and lead management
4. **Analytics** - Comprehensive reporting and insights

## Architecture

### New Files Created

1. **chat_bot_refactored.py** - Main chatbot module with service managers
2. **extended_views.py** - FastAPI endpoints for all services
3. **urls_extended.py** - URL routing documentation and configuration
4. **mongodb_config.ini** - MongoDB configuration and data models
5. **REFACTORING_GUIDE.md** - This documentation

### Service Modules

#### 1. CustomerServiceManager
Handles customer service requests including:
- Complaints
- Inquiries
- Transaction issues
- Account issues
- Generic requests

**Methods:**
- `handle_customer_service_request()` - Main request handler
- `handle_complaint()` - Process complaints
- `handle_inquiry()` - Handle inquiries
- `handle_transaction_issue()` - Escalate transaction problems
- `handle_account_issue()` - Handle account-related issues
- `handle_generic_request()` - Process generic requests

**Database Model:**
```python
Customer:
  - customer_id: str
  - first_name: str
  - last_name: str
  - email: str
  - phone_number: str
  - account_number: str
  - gender: str
  - city_of_residence: str
  - state_of_residence: str
  - occupation: str
  - date_of_birth: date
  - branch: ForeignKey
```

#### 2. HREmployeeManager
Manages HR employee services:
- Leave requests
- Benefits inquiries
- Payroll inquiries
- Training requests
- HR complaints

**Methods:**
- `handle_hr_request()` - Main request handler
- `handle_leave_request()` - Process leave applications
- `handle_payroll_inquiry()` - Retrieve payroll information
- `handle_benefits_inquiry()` - Provide benefits information
- `handle_training_request()` - Handle training applications
- `handle_hr_complaint()` - Process HR complaints

**Database Model:**
```python
Employee:
  - employee_id: str
  - name: str
  - email: str
  - department: str
  - position: str
  - hire_date: date
  - leave_balance: float
  - manager: ForeignKey
```

#### 3. CRMManager
Manages CRM operations:
- Create/update accounts
- Create leads
- Update contacts
- Update sales opportunities
- Fetch accounts and leads

**Methods:**
- `handle_crm_operation()` - Main request handler
- `create_account()` - Create new CRM account
- `create_lead()` - Create new lead
- `update_contact()` - Update contact information
- `update_opportunity()` - Update sales opportunity
- `fetch_account()` - Retrieve account details
- `fetch_leads()` - Retrieve leads with filters

**Database Models:**
```python
Account:
  - account_id: str
  - name: str
  - website: str
  - phone: str
  - industry: str
  - account_type: str
  - description: str
  - annual_revenue: decimal
  - employees: int
  - address_*: str
  - owner: ForeignKey[User]
  - created_at: datetime
  - updated_at: datetime

Contact:
  - contact_id: str
  - first_name: str
  - last_name: str
  - email: str
  - phone: str
  - mobile: str
  - title: str
  - department: str
  - account: ForeignKey[Account]
  - owner: ForeignKey[User]
  - created_at: datetime
  - updated_at: datetime

Lead:
  - lead_id: str
  - first_name: str
  - last_name: str
  - email: str
  - phone: str
  - company: str
  - title: str
  - lead_status: str (new, contacted, qualified, converted)
  - lead_source: str (web, referral, partner, event)
  - created_at: datetime
  - updated_at: datetime
```

#### 4. AnalyticsManager
Provides analytics and reporting:
- Customer metrics
- Sales analytics
- HR analytics
- Transaction analytics

**Methods:**
- `handle_analytics_request()` - Main request handler
- `get_customer_metrics()` - Customer-related metrics
- `get_sales_analytics()` - Sales pipeline analytics
- `get_hr_analytics()` - HR department metrics
- `get_transaction_analytics()` - Transaction data analytics

## Logging System

### Log Levels and Functions

```python
log_info(msg, tenant_id, conversation_id, user_id=None)
log_error(msg, tenant_id, conversation_id, user_id=None, exc_info=False)
log_warning(msg, tenant_id, conversation_id, user_id=None)
log_debug(msg, tenant_id, conversation_id, user_id=None)
log_exception(msg, tenant_id, conversation_id, user_id=None)
```

### Log File Location
- **File:** `logs/chatbot_refactored.log`
- **Format:** `[timestamp] [LEVEL] module:function:line - context - message`
- **Rotation:** 5MB per file, max 5 backup files

### Log Context Format
```
[Tenant: {tenant_id} | Conversation: {conversation_id} | User: {user_id}] Message
```

## Exception Handling

All service managers implement comprehensive try-except blocks with:

1. **Input Validation** - Check required fields
2. **Database Operations** - Wrapped in try-except-finally
3. **Transaction Management** - Rollback on error
4. **Error Responses** - Structured error codes and messages

### Common Error Codes

| Code | Meaning |
|------|---------|
| CUSTOMER_NOT_FOUND | Customer ID not found in system |
| DB_ERROR | Database operation failed |
| INTERNAL_ERROR | Unexpected server error |
| COMPLAINT_LOGGED | Complaint successfully logged |
| LEAD_CREATED | Lead created successfully |
| ACCOUNT_UPDATED | Account updated successfully |

## API Endpoints

### Customer Service Endpoints

```
POST /api/v1/customer-service/inquiry
  - customer_id: str
  - conversation_id: str
  - tenant_id: str
  - issue_type: str (complaint, inquiry, transaction, account)
  - priority: str (low, normal, high, critical)
  - description: str
  - attachment: Optional[File]
  - user_id: Optional[str]

POST /api/v1/customer-service/message
  - message_content: str
  - conversation_id: str
  - tenant_id: str
  - service_type: Optional[str]
  - user_id: Optional[str]
```

### HR Endpoints

```
POST /api/v1/hr/leave-request
  - employee_id: str
  - conversation_id: str
  - tenant_id: str
  - leave_type: str
  - start_date: str (YYYY-MM-DD)
  - end_date: str (YYYY-MM-DD)
  - reason: str
  - user_id: Optional[str]

POST /api/v1/hr/benefits-inquiry
  - employee_id: str
  - conversation_id: str
  - tenant_id: str
  - inquiry_topic: str
  - user_id: Optional[str]

POST /api/v1/hr/message
  - message_content: str
  - conversation_id: str
  - tenant_id: str
  - service_type: Optional[str]
  - user_id: Optional[str]
```

### CRM Endpoints

```
POST /api/v1/crm/account
  - conversation_id: str
  - tenant_id: str
  - account_id: Optional[str]
  - account_name: str
  - industry: Optional[str]
  - website: Optional[str]
  - phone: Optional[str]
  - user_id: Optional[str]

POST /api/v1/crm/lead
  - conversation_id: str
  - tenant_id: str
  - first_name: str
  - last_name: str
  - email: str
  - company: str
  - phone: Optional[str]
  - user_id: Optional[str]

GET /api/v1/crm/leads
  - conversation_id: str
  - tenant_id: str
  - status: Optional[str]
  - source: Optional[str]
  - user_id: Optional[str]
```

### Analytics Endpoints

```
GET /api/v1/analytics/customer-metrics
  - conversation_id: str
  - tenant_id: str
  - user_id: Optional[str]

GET /api/v1/analytics/sales
  - conversation_id: str
  - tenant_id: str
  - user_id: Optional[str]

GET /api/v1/analytics/hr
  - conversation_id: str
  - tenant_id: str
  - user_id: Optional[str]

GET /api/v1/analytics/transactions
  - conversation_id: str
  - tenant_id: str
  - date_from: Optional[str]
  - date_to: Optional[str]
  - user_id: Optional[str]

GET /api/v1/health
  - No parameters
```

## Integration with main.py

The refactored chatbot integrates with the main FastAPI application:

```python
# In main.py
from customer.extended_views import router

# Include the router
app.include_router(router)

# Or for custom prefix
app.include_router(router, prefix="/api/v1/services")
```

## MongoDB Configuration

The MongoDB configuration is defined in `mongodb_config.ini`:

### Collections

**Customer Service:**
- `customers` - Customer profiles
- `customer_service_issues` - Issue tracking
- `customer_support_tickets` - Support tickets

**HR:**
- `employees` - Employee records
- `leave_requests` - Leave applications
- `payroll_records` - Payroll data
- `benefits_enrollments` - Benefits information

**CRM:**
- `crm_accounts` - Company accounts
- `crm_contacts` - Contact information
- `crm_leads` - Sales leads
- `crm_opportunities` - Sales opportunities

**Analytics:**
- `customer_analytics` - Customer metrics
- `sales_analytics` - Sales metrics
- `hr_analytics` - HR metrics
- `transaction_analytics` - Transaction data

### Indexes

Critical indexes for performance:
- `collections.field_name: [indexed_field1, indexed_field2]`
- Enables fast queries on tenant_id, created_at, status fields
- Enables efficient filtering and sorting

## Database Models Mapping

The refactored code integrates with existing Django models:

### From customer/models.py

**CRM Models:**
- `Account` - Company/organization accounts
- `Contact` - Individual contacts
- `Lead` - Sales leads
- `Opportunity` - Sales opportunities
- `CRMUser` - CRM user profiles

**Transaction Models:**
- `Customer` - Customer profiles
- `Transaction` - Transaction history

**HR Models** (to be extended):
- `Employee` - Employee records
- `LeaveRequest` - Leave applications
- `PayrollRecord` - Payroll information
- `BenefitsEnrollment` - Benefits data

## Usage Examples

### Customer Service Request

```python
from chat_bot_refactored import (
    CustomerServiceManager,
    CustomerServiceRequest
)

cs_manager = CustomerServiceManager("tenant_123", "conv_456")
request = CustomerServiceRequest(
    customer_id="cust_789",
    issue_type="complaint",
    priority="high",
    description="ATM withdrawal failed"
)
result = await cs_manager.handle_customer_service_request(request, "user_001")
```

### CRM Lead Creation

```python
from chat_bot_refactored import (
    CRMManager,
    CRMRequest
)

crm_manager = CRMManager("tenant_123", "conv_456")
request = CRMRequest(
    operation="create_lead",
    entity_type="Lead",
    data={
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "company": "Tech Corp",
        "phone": "+1234567890"
    }
)
result = await crm_manager.handle_crm_operation(request, "user_001")
```

### Analytics Query

```python
from chat_bot_refactored import (
    AnalyticsManager,
    AnalyticsRequest
)

analytics_manager = AnalyticsManager("tenant_123", "conv_456")
request = AnalyticsRequest(
    analysis_type="customer_metrics",
    filters={}
)
result = await analytics_manager.handle_analytics_request(request, "user_001")
```

## Migration Steps

### Step 1: Backup Existing Code
```bash
cp chat_bot.py chat_bot_backup.py
```

### Step 2: Deploy New Files
- Copy `chat_bot_refactored.py` to `customer/chat_bot_refactored.py`
- Copy `extended_views.py` to `customer/extended_views.py`
- Copy `mongodb_config.ini` to `customer/mongodb_config.ini`

### Step 3: Update Imports in main.py
```python
# From
from chat_bot import process_message

# To
from customer.chat_bot_refactored import process_message, ServiceType
from customer.extended_views import router
```

### Step 4: Register Routes
```python
# In main.py FastAPI app setup
app.include_router(router, prefix="/api/v1")
```

### Step 5: Test Endpoints
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Customer service
curl -X POST http://localhost:8000/api/v1/customer-service/inquiry \
  -F "customer_id=CUST001" \
  -F "conversation_id=CONV001" \
  -F "tenant_id=TENANT001" \
  -F "issue_type=complaint" \
  -F "priority=high" \
  -F "description=Test issue"
```

## Performance Considerations

1. **Database Connection Pooling** - Configured in chat_bot_refactored.py
2. **Async Processing** - All service methods are async
3. **Caching** - Implement Redis caching for frequently accessed data
4. **Indexing** - MongoDB indexes configured in mongodb_config.ini
5. **Batch Operations** - Process multiple requests efficiently

## Security Considerations

1. **Input Validation** - All inputs validated using Pydantic
2. **SQL Injection Prevention** - Using SQLAlchemy ORM
3. **Error Messages** - Sanitized error messages without internal details
4. **User Authentication** - user_id tracking for audit
5. **Data Encryption** - Sensitive fields encrypted in MongoDB

## Monitoring and Debugging

### Key Log Locations
- `logs/chatbot_refactored.log` - Main log file
- Logs rotate every 5MB
- Each log entry includes: timestamp, level, module, function, line number, context, and message

### Debug Mode
Set environment variable to increase logging:
```bash
export CHATBOT_DEBUG=1
```

## Troubleshooting

### Common Issues

**Issue:** Database connection errors
- **Cause:** Database service not running
- **Solution:** Check database connectivity, verify connection string

**Issue:** MongoDB collection not found
- **Cause:** Collections not initialized
- **Solution:** Run MongoDB initialization scripts in mongodb_config.ini

**Issue:** API endpoint returns 500 error
- **Cause:** Check logs for detailed error message
- **Solution:** Review logs in `logs/chatbot_refactored.log`

## Future Enhancements

1. **Machine Learning** - Sentiment analysis for customer issues
2. **Predictive Analytics** - Forecasting customer churn, sales pipeline
3. **Advanced CRM** - Automated opportunity scoring
4. **Integration** - Slack, Teams, SMS notifications
5. **Mobile App** - Native iOS/Android applications
6. **Real-time Dashboard** - Live analytics and metrics

## Support and Questions

For questions or issues:
1. Check logs in `logs/chatbot_refactored.log`
2. Review error codes in this documentation
3. Check MongoDB configuration in `mongodb_config.ini`
4. Verify database models are properly defined
