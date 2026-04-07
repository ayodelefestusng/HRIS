from django.contrib import admin

from users.admin import BaseTenantAdmin # Inherited Multi-tenant logic
from .models import(
    Customer,  Customer, Transaction, Account,
    Contact, Lead, Opportunity, CRMUser,
    Tenant_AI, LLM, Conversation,
    Message,Prompt,BranchPerformance,PasswordSetupToken)

# Register your models here.
# admin.site.register(Customer)


@admin.register(Customer)
class CustomerAdmin(BaseTenantAdmin):  
    list_display = ('full_name', 'email', 'phone_number', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('first_name', 'last_name', 'email', 'phone_number','account_number','nin')

admin.site.register(Transaction)
admin.site.register(Account)
admin.site.register(Contact)
admin.site.register(Lead)
admin.site.register(Opportunity)
admin.site.register(CRMUser)
admin.site.register(Tenant_AI)
admin.site.register(LLM)
admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(Prompt)
admin.site.register(BranchPerformance)
admin.site.register(PasswordSetupToken)

