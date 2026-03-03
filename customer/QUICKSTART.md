# QUICK START GUIDE
# =================

This guide provides a quick overview of the refactored chatbot system and how to use it.

## What Changed?

The chatbot was refactored from a single monolithic service to a **multi-service architecture** supporting:

1. **Customer Service** - Handle customer issues, complaints, and inquiries
2. **HR Employee Services** - Manage leaves, benefits, payroll, training
3. **CRM** - Create/manage accounts, leads, contacts, opportunities
4. **Analytics** - Get business metrics and insights

## New Files Created

Seven new files were created in the `customer/` directory:

```
customer/
├── chat_bot_refactored.py              # Main refactored service module
├── extended_views.py                    # FastAPI endpoints for all services
├── chatbot_config.py                    # Configuration management
├── urls_extended.py                     # URL documentation
├── mongodb_config.ini                   # MongoDB schema config
├── main_integration_example.py          # How to integrate with main.py
├── REFACTORING_GUIDE.md                 # Complete documentation
└── REFACTORING_COMPLETION_SUMMARY.md   # Summary of changes
```

## Quick Integration (5 Steps)

### Step 1: Update main.py imports
```python
from customer.chatbot_config import ServiceConfig, setup_main_app
from customer.extended_views import router as service_router
```

### Step 2: Initialize app
```python
app = FastAPI(title=ServiceConfig.API_TITLE)
setup_main_app(app)
app.include_router(service_router, prefix="/api/v1")
```

### Step 3: Add startup event
```python
@app.on_event("startup")
async def startup():
    from database import init_db
    init_db()
```

### Step 4: Update .env
```env
GEMINI_API_KEY=your-api-key
DATABASE_URL=sqlite:///ai_database.sqlite3
LOG_LEVEL=INFO
```

### Step 5: Test
```bash
curl http://localhost:8000/api/v1/health
```

## Key Features

### 1. Customer Service Endpoints
```bash
POST /api/v1/customer-service/inquiry
POST /api/v1/customer-service/message
```

### 2. HR Endpoints
```bash
POST /api/v1/hr/leave-request
POST /api/v1/hr/benefits-inquiry
POST /api/v1/hr/message
```

### 3. CRM Endpoints
```bash
POST /api/v1/crm/account
POST /api/v1/crm/lead
GET  /api/v1/crm/leads
```

### 4. Analytics Endpoints
```bash
GET /api/v1/analytics/customer-metrics
GET /api/v1/analytics/sales
GET /api/v1/analytics/hr
GET /api/v1/analytics/transactions
```

## Example Usage

### Create a customer service ticket
```bash
curl -X POST http://localhost:8000/api/v1/customer-service/inquiry \
  -F "customer_id=CUST001" \
  -F "conversation_id=CONV001" \
  -F "tenant_id=TENANT001" \
  -F "issue_type=complaint" \
  -F "priority=high" \
  -F "description=My ATM withdrawal failed"
```

### Submit a leave request
```bash
curl -X POST http://localhost:8000/api/v1/hr/leave-request \
  -F "employee_id=EMP001" \
  -F "conversation_id=CONV001" \
  -F "tenant_id=TENANT001" \
  -F "leave_type=annual" \
  -F "start_date=2026-03-15" \
  -F "end_date=2026-03-20" \
  -F "reason=Vacation"
```

### Create a CRM lead
```bash
curl -X POST http://localhost:8000/api/v1/crm/lead \
  -F "conversation_id=CONV001" \
  -F "tenant_id=TENANT001" \
  -F "first_name=John" \
  -F "last_name=Doe" \
  -F "email=john@example.com" \
  -F "company=Tech Corp"
```

## Logging

All operations are logged to `logs/chatbot_refactored.log` with context:

```
[2026-03-03 10:15:30,123] [INFO] chat_bot_refactored:handle_customer_service_request:200 - [Tenant: TENANT001 | Conversation: CONV001 | User: USER001] Processing customer service request: complaint
```

## Error Handling

All errors return structured responses:

```json
{
  "status": "error",
  "code": "CUSTOMER_NOT_FOUND",
  "message": "Customer CUST123 not found in the system.",
  "metadata": {
    "timestamp": "2026-03-03T10:15:30.123456",
    "service": "customer_service"
  }
}
```

## Database Models

The system uses existing Django models from `customer/models.py`:

- `Account` - CRM accounts
- `Contact` - CRM contacts  
- `Lead` - CRM leads
- `Opportunity` - Sales opportunities
- `Customer` - Customer profiles
- `Transaction` - Transaction history
- `Tenant` - Multi-tenant support
- `Conversation` - Conversation tracking
- `Message` - Message storage
- `LLM` - LLM configuration

## Service Managers

Each service has a manager class:

```python
from customer.chat_bot_refactored import (
    CustomerServiceManager,
    HREmployeeManager,
    CRMManager,
    AnalyticsManager
)

# Usage example
cs_manager = CustomerServiceManager("tenant_id", "conversation_id")
result = await cs_manager.handle_customer_service_request(request, "user_id")
```

## Async/Await

All methods are async and should be called with `await`:

```python
result = await cs_manager.handle_customer_service_request(request, user_id)
```

## Configuration

Configure via environment variables:

```env
# Services (true/false)
CUSTOMER_SERVICE_ENABLED=true
HR_SERVICE_ENABLED=true
CRM_ENABLED=true
ANALYTICS_ENABLED=true

# Database
DATABASE_URL=sqlite:///ai_database.sqlite3

# LLM
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-1.5-flash

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs

# API
API_PREFIX=/api/v1
```

Or use `ServiceConfig` class:

```python
from customer.chatbot_config import ServiceConfig

print(ServiceConfig.CUSTOMER_SERVICE_ENABLED)  # True
print(ServiceConfig.LOG_LEVEL)  # INFO
```

## Testing

Test all services:

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Service configuration
curl http://localhost:8000/api/v1/service-config

# Service statistics
curl http://localhost:8000/api/v1/service-stats
```

## Documentation

Detailed documentation in:

- **REFACTORING_GUIDE.md** - Architecture, APIs, models, examples
- **REFACTORING_COMPLETION_SUMMARY.md** - Summary of all changes
- **extended_views.py** - Endpoint docstrings
- **chat_bot_refactored.py** - Class and method docstrings

## Common Patterns

### Logging with context
```python
log_info("User initiated request", tenant_id, conversation_id, user_id)
log_error("Database error occurred", tenant_id, conversation_id, user_id)
```

### Error handling
```python
try:
    result = await some_operation()
    return {"status": "success", "data": result}
except Exception as e:
    log_exception(f"Error: {str(e)}", tenant_id, conversation_id, user_id)
    return {"status": "error", "message": str(e)}
```

### Database operations
```python
db = SessionLocal()
try:
    entity = db.query(Model).filter(Model.id == entity_id).first()
    if not entity:
        return {"status": "error", "code": "NOT_FOUND"}
    # Update entity
    db.commit()
    return {"status": "success", "data": entity}
except Exception as e:
    db.rollback()
    log_exception(str(e), tenant_id, conversation_id)
    return {"status": "error"}
finally:
    db.close()
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Endpoints not found (404) | Make sure router is included: `app.include_router(service_router)` |
| Database errors | Check DATABASE_URL in .env and ensure DB is running |
| Vector store errors | Set GEMINI_API_KEY in .env |
| Logging not working | Create logs directory: `mkdir logs` |

## Next Steps

1. ✅ Review [REFACTORING_GUIDE.md](REFACTORING_GUIDE.md) for complete documentation
2. ✅ Look at [main_integration_example.py](main_integration_example.py) for integration code
3. ✅ Check [mongodb_config.ini](mongodb_config.ini) for data schema
4. ✅ Update your main.py with integration code
5. ✅ Test endpoints with curl or Postman
6. ✅ Monitor logs in `logs/chatbot_refactored.log`

## Performance Tips

1. **Use Redis caching** - Set `REDIS_ENABLED=true`
2. **Batch requests** - Group similar operations
3. **Connection pooling** - Already configured in SQLDatabase
4. **Async operations** - Use async/await throughout
5. **Indexes** - MongoDB indexes configured in mongodb_config.ini

## Security Considerations

1. ✅ All inputs validated with Pydantic
2. ✅ SQL injection prevention via SQLAlchemy ORM
3. ✅ CORS configured via CORSMiddleware
4. ✅ User tracking via user_id parameter
5. ✅ Error messages sanitized (no internal details in responses)
6. ✅ Sensitive data never logged
7. ✅ Database credentials in environment variables

## Production Checklist

- [ ] Update SECRET_KEY in environment
- [ ] Configure proper CORS_ORIGINS for your domain
- [ ] Set LOG_LEVEL to INFO or WARNING
- [ ] Enable Redis caching: REDIS_ENABLED=true
- [ ] Configure database connection pooling
- [ ] Set up monitoring and alerting
- [ ] Enable HTTPS for API endpoints
- [ ] Configure backup strategy
- [ ] Test all endpoints thoroughly
- [ ] Load test the system
- [ ] Set up log rotation and archival

## Contact & Support

For questions or issues:
1. Check the logs in `logs/chatbot_refactored.log`
2. Review the error code in the response
3. Consult [REFACTORING_GUIDE.md](REFACTORING_GUIDE.md)
4. Check [main_integration_example.py](main_integration_example.py) for integration examples

---

**Happy coding! 🚀**
