from django.contrib import admin
from .models import (
    Employee,
    JobAssignment,
    CompensationRecord,
    # JobTitle,
    EmployeeDocument,
    ProfileUpdateRequest
)


from django.contrib import admin, messages
from payroll.models import Employee, PayrollPeriod
from workflow.services.workflow_service import PayrollService   


# employees/admin.py
import logging
from .models import (
    Survey,
    SurveyQuestion,
    SurveyResponse,
    Poll,
    PollOption,
    PollVote,
    PulseCheck,
)

logger = logging.getLogger(__name__)

# class BaseTenantAdmin(admin.ModelAdmin):
#     """Base Admin that filters lists and auto-assigns tenant on save."""

#     def get_queryset(self, request):
#         qs = super().get_queryset(request)
#         if request.user.is_superuser:
#             return qs
#         return qs.filter(tenant=request.user.tenant)

#     def save_model(self, request, obj, form, change):
#         if not obj.tenant:
#             obj.tenant = request.user.tenant

#         logger.info(f"Saving {obj._meta.model_name}: {obj}")
#         super().save_model(request, obj, form, change)

# @admin.register(Employee)
# class EmployeeAdmin(BaseTenantAdmin):
#     list_display = ('full_name', 'tenant')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "grade", "is_active")
    actions = ["generate_payroll_for_selected"]
    search_fields = ("first_name", "last_name")
    list_filter = ("grade", "is_active")

    @admin.action(description="Generate Payroll for current Open period")
    def generate_payroll_for_selected(self, request, queryset):
        # 1. Find the currently open period
        period = PayrollPeriod.objects.filter(status="OPN").first()

        if not period:
            self.message_user(
                request,
                "No 'Open' payroll period found. Please create or open one first.",
                messages.ERROR,
            )
            return

        # 2. Initialize Service
        service = PayrollService(period)
        count = 0
        errors = 0

        # 3. Process each selected employee
        for employee in queryset:
            try:
                service.generate_for_employee(employee)
                count += 1
            except Exception as e:
                # Log error or handle duplicates (unique_together constraint)
                errors += 1

        # 4. Feedback to user
        self.message_user(
            request,
            f"Successfully generated {count} payroll entries for {period.name}. "
            f"({errors} errors/duplicates skipped).",
            messages.SUCCESS,
        )

    # employees/admin.py (Modified)

    @admin.action(description="Audit Readiness for Next Grade")
    def audit_promotion_readiness(self, request, queryset):
        from development.services import CareerPathService
        from org.models import Grade

        service = CareerPathService(request.user.tenant)

        for employee in queryset:
            # Find the next level grade
            next_grade = Grade.objects.filter(
                tenant=request.user.tenant, level=employee.grade.level + 1
            ).first()

            if not next_grade:
                self.message_user(
                    request, f"{employee}: No higher grade found.", messages.WARNING
                )
                continue

            result = service.evaluate_readiness(employee, next_grade)

            if result["is_ready"]:
                self.message_user(
                    request,
                    f"🌟 {employee} is 100% READY for promotion to {next_grade.name}!",
                    messages.SUCCESS,
                )
            else:
                gap_list = ", ".join(result["gaps"][:2])  # Show first 2 gaps
                self.message_user(
                    request,
                    f"🚩 {employee} is {result['readiness_score']}% ready for {next_grade.name}. Gaps: {gap_list}",
                    messages.INFO,
                )


# @admin.register(JobTitle)
class JobTitleAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(JobAssignment)
class JobAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "department",
        "job_title",
        "employment_status",
        "is_active",
    )
    list_filter = ("employment_status", "is_active", "department", "job_title")


@admin.register(CompensationRecord)
class CompensationRecordAdmin(admin.ModelAdmin):
    list_display = ("employee", "salary_amount", "currency", "effective_date", "reason")
    list_filter = ("currency", "effective_date")
    search_fields = ("employee__first_name", "employee__last_name", "reason")


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ("employee", "name", "doc_type", "uploaded_at", "expires_at")
    list_filter = ("doc_type",)
    search_fields = ("employee__first_name", "employee__last_name", "name")


admin.site.register(Survey)
admin.site.register(SurveyQuestion)
admin.site.register(SurveyResponse)
admin.site.register(Poll)
admin.site.register(PollOption)
admin.site.register(PollVote)
admin.site.register(PulseCheck)
admin.site.register(ProfileUpdateRequest)
