from django.contrib import admin
from .models import(
    Customer,  Customer, Transaction, Account,
    Contact, Lead, Opportunity, CRMUser,
    Tenant_AI, LLM, Conversation,
    Message,Prompt,BranchPerformance)

# Register your models here.
admin.site.register(Customer)
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
