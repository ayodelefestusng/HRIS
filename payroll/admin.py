from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render
from .models import (
    AllowanceType, GradeAllowance, EmployeeAllowance,
    PayrollPeriod, PayrollEntry, PayrollAllowanceItem,
    Deduction, PayrollDeductionItem, EmployeePayslip, TaxRecord
)
from workflow.services.workflow_service import PayrollService,BankExportService
from analytics.services.analytics_engine import PayrollAnalyticsService



from django.contrib import admin, messages
from .models import Employee, PayrollPeriod



# Register Simple Models
admin.site.register(AllowanceType)
admin.site.register(GradeAllowance)
admin.site.register(EmployeeAllowance)
admin.site.register(Deduction)
admin.site.register(PayrollAllowanceItem)
# admin.site.register(Deduction)
admin.site.register(PayrollDeductionItem)
admin.site.register(TaxRecord)

@admin.action(description="Download Bank Schedule (CSV)")
def download_bank_schedule(modeladmin, request, queryset):
    if queryset.count() != 1:
        modeladmin.message_user(request, "Please select exactly one period.", level="error")
        return

    period = queryset.first()
    try:
        service = BankExportService(period)
        return service.generate_bank_csv()
    except Exception as e:
        modeladmin.message_user(request, str(e), level="error")




@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'status')
    actions = ['generate_bulk_payroll', 'finalize_periods','download_bank_schedule']
    

    @admin.action(description="1. Generate Payroll for ALL Active Staff")
    def generate_bulk_payroll(self, request, queryset):
        for period in queryset:
            if period.status != "OPN":
                self.message_user(request, f"{period.name} is not Open.", messages.ERROR)
                continue
            
            service = PayrollService(request.user.tenant, period)
            count = service.generate_for_all_staff()
            self.message_user(request, f"Generated {count} entries for {period.name}.", messages.SUCCESS)

    @admin.action(description="2. Finalize and Close Periods")
    def finalize_periods(self, request, queryset):
        for period in queryset:
            if period.entries.exists():
                period.status = "CLO"
                period.save()
                self.message_user(request, f"Closed {period.name}.", messages.SUCCESS)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:period_id>/variance/', self.admin_site.admin_view(self.variance_view), name='payroll-variance'),
        ]
        return custom_urls + urls

    def variance_view(self, request, period_id):
        period = self.get_object(request, period_id)
        service = PayrollAnalyticsService(request.user.tenant)
        report_data = service.get_variance_report(period)
        return render(request, 'admin/payroll/variance_report.html', {'report': report_data, 'title': f"Variance: {period.name}"})  

@admin.register(PayrollEntry)
class PayrollEntryAdmin(admin.ModelAdmin):
    list_display = ("employee", "period", "net_pay")
    list_filter = ("period",)


@admin.register(EmployeePayslip)
class EmployeePayslipAdmin(admin.ModelAdmin):
    list_display = ("entry", "generated_at")
    list_filter = ("generated_at",)


