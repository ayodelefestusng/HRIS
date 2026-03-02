@shared_task
def generate_monthly_tenant_invoices():
    from org.models import Tenant
    from django.utils import timezone
    
    tenants = Tenant.objects.filter(is_active=True)
    today = timezone.now().date()
    
    for tenant in tenants:
        stats = BillingEngine.calculate_monthly_bill(tenant)
        
        Invoice.objects.create(
            tenant=tenant,
            billing_period=today,
            employee_count=stats['headcount'],
            amount_due=stats['total'],
            is_paid=False
        )
        
        logger.info(f"[BILLING_GEN] Invoice created for {tenant.name}: ₦{stats['total']}")