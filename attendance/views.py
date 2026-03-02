from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.http import JsonResponse, HttpResponse

from workflow.services.workflow_engine import WorkflowService

from .models import AttendanceRecord, ShiftSchedule, ClockLog
from employees.models import Employee
import logging

import logging
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.generic import ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import timedelta  
from django.db.models import Q
from employees.views import EmployeeDetailView   
from org.models import OrgUnit  
# --- Reporting ---
from workflow.services.workflow_service import get_recursive_downline_ids
from io import BytesIO
from django.core.mail import EmailMessage
from django.template.loader import get_template
from django.conf import settings
import csv
from django.http import HttpResponse
from django.template.loader import get_template
# If using xhtml2pdf: pip install xhtml2pdf
from xhtml2pdf import pisa

from workflow.models import HistoricalRecord    
logger = logging.getLogger(__name__)

def log_with_context(level, message, user):
    tenant = getattr(user, "tenant", None)
    logger.log(
        level,
        f"tenant={tenant}|user={user.username}|{message}"
    )

# --- Tracking ---

class TrackAttendanceView(LoginRequiredMixin, ListView):
    model = AttendanceRecord
    template_name = "attendance/track_attendance.html"
    context_object_name = "records"
    paginate_by = 20

    def get_queryset(self):
        try:
            today = timezone.localtime().date()
            date_param = self.request.GET.get("date", str(today))
            log_with_context(logging.INFO, f"Tracking attendance for date: {date_param}", self.request.user)
            
            return AttendanceRecord.objects.filter(
                tenant=self.request.user.tenant, date=date_param
            ).select_related("employee", "shift")
        except Exception as e:
            log_with_context(logging.ERROR, f"Error in TrackAttendanceView: {str(e)}", self.request.user)
            return AttendanceRecord.objects.none()


class LateArrivalsView(LoginRequiredMixin, ListView):
    model = AttendanceRecord
    template_name = "attendance/late_arrivals.html"
    context_object_name = "late_records"

    def get_queryset(self):
        log_with_context(logging.INFO, "Viewing today's late arrivals", self.request.user)
        return AttendanceRecord.objects.filter(
            tenant=self.request.user.tenant,
            status="LATE",
            date=timezone.localtime().date(),
        ).select_related("employee")


class EarlyDeparturesView(LoginRequiredMixin, ListView):
    model = AttendanceRecord
    template_name = "attendance/early_departures.html"
    context_object_name = "early_records"

    def get_queryset(self):
        log_with_context(logging.INFO, "Viewing today's early departures", self.request.user)
        return AttendanceRecord.objects.filter(
            tenant=self.request.user.tenant,
            is_under_hours=True,
            date=timezone.localtime().date(),
        ).select_related("employee")


# --- Biometric ---

class BiometricIntegrationView(LoginRequiredMixin, TemplateView):
    template_name = "attendance/biometric_integrate.html"

    def post(self, request, *args, **kwargs):
        try:
            log_with_context(logging.INFO, "Initiating biometric device sync", request.user)
            # STUB: Receive a JSON payload from a machine
            return JsonResponse(
                {"status": "success", "message": "Device synced successfully (Stub)."}
            )
        except Exception as e:
            log_with_context(logging.ERROR, f"Biometric sync failed: {str(e)}", request.user)
            return JsonResponse(
                {"status": "error", "message": "Sync failed."}, status=500
            )



class AttendanceReportView3(LoginRequiredMixin, TemplateView):
    template_name = "attendance/report_dashboard.html"

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            today = timezone.localtime().date()
            tenant = self.request.user.tenant

            log_with_context(logging.INFO, "Generating today's attendance report summary", self.request.user)

            stats = AttendanceRecord.objects.filter(tenant=tenant, date=today).aggregate(
                present=Count("id", filter=Q(work_status="PRESENT")),
                absent=Count("id", filter=Q(work_status="ABSENT")),
                late=Count("id", filter=Q(work_status="LATE")),
            )
            context["today_stats"] = stats
            return context
        except Exception as e:
            log_with_context(logging.ERROR, f"Error in AttendanceReportView: {str(e)}", self.request.user)
            return {"today_stats": {}}
# attendance/views.py
class AttendanceReportView(LoginRequiredMixin, ListView):
    model = AttendanceRecord
    template_name = "attendance/report_dashboard.html"
    context_object_name = "records"
    paginate_by = 20

    def get_queryset(self):
        log_with_context(logging.INFO, "Generating attendance report summary", self.request.user)
        user = self.request.user
        qs = AttendanceRecord.objects.filter(tenant=user.tenant).select_related(
            'employee', 'shift', 'employee__grade', 'employee__grade__pyramid'
        )
        downline_ids = get_recursive_downline_ids(user.employee)
        # Role-based Scope
        if user.is_hr_admin or user.is_hr_manager or user.is_hr_officer:
            pass # Full access
        # elif user.is_manager:
            # Recursive downline (using the helper method we wrote earlier)
            # downline_ids = self.get_recursive_downline_ids(user.employee)
            # downline_ids = get_recursive_downline_ids(user.employee)
            # 1. Role-based Visibility
        if not (user.is_hr_admin or user.is_hr_manager or user.is_hr_officer):
            if user.is_manager:
                
                qs = qs.filter(Q(employee_id__in=downline_ids) | Q(employee=user.employee))
           
                log_with_context(logging.INFO, f"Searching employees with query: {downline_ids}", self.request.user)

            else:
                qs = qs.filter(employee=user.employee)


            # Include self in manager view
            qs = qs.filter(Q(employee_id__in=downline_ids) | Q(employee=user.employee))
        else:
            qs = qs.filter(employee=user.employee)
        log_with_context(logging.INFO, f"Searching employees with query Total: {qs.count()}", self.request.user)    
        # 2. Advanced Off-canvas Filters
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        shift_val = self.request.GET.get('shift')
        staff_id = self.request.GET.get('staff_id')
        org_unit = self.request.GET.get('org_unit')
        log_with_context(logging.INFO, f"Searching employees with query: {org_unit}", self.request.user)    
        status_val = self.request.GET.get('status')
        approval_val = self.request.GET.get('approval')
        if start_date: qs = qs.filter(date__gte=start_date)
        if end_date: qs = qs.filter(date__lte=end_date)
        if shift_val: qs = qs.filter(shift_id=shift_val)
        if staff_id: qs = qs.filter(employee__employee_id__icontains=staff_id)
        if org_unit: qs = qs.filter(employee__roles__org_unit_id=org_unit)
        if status_val: qs = qs.filter(work_status=status_val)
        if approval_val: qs = qs.filter(approval_status=approval_val)
        log_with_context(logging.INFO, f"Searching employees with queryTTT: {qs.count()}", self.request.user)    

        # Apply Filters (Search, Date, Status)
        # q = self.request.GET.get("q")
        # if q:
        #     qs = qs.filter(Q(employee__first_name__icontains=q) | Q(employee__employee_id__icontains=q))
        # Dynamic Sorting
        
        # 3. Enhanced Sorting (Status, Clock In/Out, Approval)
        sort_by = self.request.GET.get("sort", "-date")
        return qs.order_by(sort_by)
    
    def get_recursive_downline_ids1(self, employee):
        """Helper to fetch all IDs in the reporting chain."""
        full_ids = []
        # Start with direct reports
        stack = list(Employee.objects.filter(line_manager=employee).values_list('id', flat=True))
    
        while stack:
            current_id = stack.pop()
            if current_id not in full_ids:
                full_ids.append(current_id)
                # Find reports of this person and add to stack
                child_reports = Employee.objects.filter(line_manager_id=current_id).values_list('id', flat=True)
                stack.extend(child_reports)
            log_with_context(logging.INFO, f"Searching employees with query: {current_id}", self.request.user)
    
        return full_ids

    def get_context_data(self, **kwargs):
        log_with_context(logging.INFO, "Generating attendance report summary", self.request.user)
        context = super().get_context_data(**kwargs)
        # Stats for the "Snippet" (Month to date)
        now = timezone.now()
        
        user = self.request.user
        today = timezone.localtime().date()
        
        # Monthly Stats (Including Absent)
        personal_month_qs = AttendanceRecord.objects.filter(
            employee=user.employee, 
            date__month=today.month, 
            date__year=today.year
        )
        context['my_stats'] = {
            'present': personal_month_qs.filter(clock_in__isnull=False).count(),
            'late': personal_month_qs.filter(is_late=True).count(),
            'absent': personal_month_qs.filter(work_status="ABSENT").count(), # New
        }
        
        # 1. Attendance Snippet (HR/Manager View)
        scope_qs = self.get_queryset() # Respects existing visibility
        context['snippet'] = scope_qs.filter(date=today).aggregate(
            present=Count('id', filter=Q(clock_in__isnull=False)),
            absent=Count('id', filter=Q(clock_in__isnull=True)),
            late=Count('id', filter=Q(is_late=True))
        )
        
        
        # 2. My Attendance View (Personal stats for current month)
        personal_qs = AttendanceRecord.objects.filter(
            employee=user.employee, 
            date__month=today.month, 
            date__year=today.year
        )
        
        # context['my_stats'] = {
        #     'present': personal_qs.filter(clock_in__isnull=False).count(),
        #     'late': personal_qs.filter(is_late=True).count(),
        # }
        # Filter Dropdown Data
        context['shifts'] = ShiftSchedule.objects.filter(tenant=user.tenant)
        context['org_units'] = OrgUnit.objects.filter(tenant=user.tenant, is_deleted=False)
        
        # 3. Smart Clock State
        last_record = AttendanceRecord.objects.filter(employee=user.employee).order_by('-date', '-clock_in').first()
        context['is_clocked_in'] = last_record.clock_in and not last_record.clock_out if last_record else False
        
        personal_qs = AttendanceRecord.objects.filter(employee=self.request.user.employee, date__month=now.month)
        
        context['my_present'] = personal_qs.filter(work_status="PRESENT").count()
        context['my_late'] = personal_qs.filter(is_late=True).count()
        
        
        context['dept_heads'] = Employee.objects.filter(
        roles__role_type="HEAD", 
        roles__is_deleted=False,
        tenant=self.request.user.tenant
    ).distinct()
    
        # Include the Audit Logs for the footer
        context['audit_logs'] = HistoricalRecord.objects.filter(
        tenant=self.request.user.tenant
    ).order_by('-created_at')[:10]
            
        return context

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get('export')
        if export_type:
            queryset = self.get_queryset()
            if export_type == 'csv':
                return self.export_csv(queryset)
            elif export_type == 'pdf':
                return self.export_pdf(queryset)
        
        return super().get(request, *args, **kwargs)

    def export_csv(self, queryset):
        log_with_context(logging.INFO, "Exporting attendance report to CSV", self.request.user)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="attendance_report_{timezone.now().date()}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Employee ID', 'Full Name', 'Date', 'Clock In', 'Clock Out', 'Status', 'Approval'])
        log_with_context(logging.INFO, f"Exporting attendance report to CSV: {queryset}", self.request.user)
        for rec in queryset:
            writer.writerow([
                rec.employee.employee_id,
                rec.employee.full_name,
                rec.date,
                rec.clock_in or '--',
                rec.clock_out or '--',
                rec.get_status_display(),
                rec.get_approval_status_display()
            ])
        return response

    def export_pdf(self, queryset):
        log_with_context(logging.INFO, "Exporting attendance report to PDF", self.request.user)
        template_path = 'attendance/pdf_template.html'
        context = {
            'records': queryset,
            'tenant': self.request.user.tenant,
            'generated_at': timezone.now()
        }
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="attendance_report.pdf"'
        log_with_context(logging.INFO, f"Exporting attendance report to PDF: {queryset}", self.request.user)
        template = get_template(template_path)
        html = template.render(context)

        # Create the PDF
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')
        return response
    
    
    def post(self, request, *args, **kwargs):
        """Handle the Email Report request via POST"""
        log_with_context(logging.INFO, "Emailing attendance report", self.request.user)
        if 'email_report' in request.POST:
            recipient_id = request.POST.get('recipient_head')
            queryset = self.get_queryset()
            
            # 1. Generate PDF in memory
            template = get_template('attendance/pdf_template.html')
            html = template.render({'records': queryset, 'tenant': request.user.tenant})
            result = BytesIO()
            pisa.CreatePDF(BytesIO(html.encode("UTF-8")), dest=result)
            log_with_context(logging.INFO, f"Generated PDF for attendance report: {queryset}", self.request.user)
            # 2. Prepare Email
            recipient = Employee.objects.get(id=recipient_id)
            email = EmailMessage(
                subject=f"Attendance Report - {timezone.now().date()}",
                body=f"Hello {recipient.full_name},\n\nPlease find the attached attendance report for your review.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient.user.email],
            )
            
            # 3. Attach and Send
            email.attach(f'Report_{timezone.now().date()}.pdf', result.getvalue(), 'application/pdf')
            email.send()
            log_with_context(logging.INFO, f"Sent email to {recipient.full_name} ({recipient.user.email}) for attendance report", self.request.user)
            # 3. Log to HistoricalRecord
        # Note: In a real scenario, you might link this to a specific 'Attendance' WorkflowInstance
            HistoricalRecord.objects.create(
                tenant=request.user.tenant,
                actor=request.user.employee,
                action_description=(
                    f"Dispatched Attendance Report to {recipient.full_name} ({recipient.user.email}). "
                    f"Filters: {filters_used}"
                ),
                is_approved=True  # Marking as a successful system action
            )
            log_with_context(logging.INFO, f"Logged attendance report to HistoricalRecord: {queryset}", self.request.user)
            messages.success(request, f"Report successfully sent to {recipient.full_name}")
            return redirect(request.get_full_path())
        
        return super().get(request, *args, **kwargs)

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views import View   
from .models import AttendanceRecord
from workflow.models import WorkflowInstance
from workflow.services.workflow_engine import WorkflowService

class AttendanceActionView(View):
    """
    Handles Approval, Rejection, and Amendment for Attendance Records
    via the Workflow engine.
    """
    def post(self, request, instance_id):
        # 1. Setup
        instance = get_object_or_404(WorkflowInstance, id=instance_id, tenant=request.tenant)
        service = WorkflowService(tenant=request.tenant)
        
        # Determine the action from the button clicked
        action_type = request.POST.get("action")  # 'APP', 'REJ', or 'AMD'
        comment = request.POST.get("comment", "")
        
        # Get the employee object for the current user
        actor = request.user.employee 

        try:
            # 2. Process the action through the Service
            updated_instance, message = service.process_action(
                instance=instance,
                actor=actor,
                action_type=action_type,
                comment=comment,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, message)
            
        except PermissionError as e:
            messages.error(request, f"Authorization Error: {str(e)}")
            logger.warning(f"Unauthorized action attempt by {actor} on instance {instance_id}")
            
        except Exception as e:
            messages.error(request, "An error occurred while processing the request.")
            logger.error(f"Error in AttendanceActionView: {str(e)}", exc_info=True)

        # 3. Redirect back to the Workflow Inbox
        return redirect("workflow:inbox")
# attendance/views.py
class SmartClockView(LoginRequiredMixin, View):
    def post(self, request):
        user = request.user
        emp = user.employee
        now = timezone.localtime()
        today = now.date()
        yesterday = today - timedelta(days=1)

        try:
            # 1. Look for an unfinished night shift from yesterday first
            record = AttendanceRecord.objects.filter(
                employee=emp, date=yesterday, clock_out__isnull=True
            ).first()

            if not record:
                # 2. Look for today's record
                record, created = AttendanceRecord.objects.get_or_create(
                    employee=emp, date=today,
                    defaults={'shift': emp.shift_assignments.filter(date=today).first().shift if emp.shift_assignments.exists() else None}
                )

            if not record.clock_in:
                record.clock_in = now.time()
                action = "Clocked In"
            else:
                record.clock_out = now.time()
                action = "Clocked Out"
            
            record.save()
            messages.success(request, f"{action} successfully at {now.strftime('%H:%M:%S')}")

            return redirect('attendance:attendance_report')
            # return JsonResponse({'status': 'success', 'message': action})
            # # redirect_url = request.GET.get('next', 'attendance:attendance_report')
            # redirect_url = 'attendance:attendance_report'
            # return redirect(redirect_url)
        except Exception as e:
            log_with_context(logging.ERROR, f"Clocking Error: {str(e)}", user)
            return JsonResponse({'status': 'error', 'message': "System error during clocking."}, status=500)

class AbsenteeismReportView(LoginRequiredMixin, ListView):
    template_name = "attendance/absenteeism_report.html"
    model = AttendanceRecord

    def get_queryset(self):
        log_with_context(logging.INFO, "Accessing historical absenteeism report", self.request.user)
        return AttendanceRecord.objects.filter(
            tenant=self.request.user.tenant, approval_status="ABSENT"
        ).order_by("-date")


class TardinessReportView(LoginRequiredMixin, ListView):
    template_name = "attendance/tardiness_report.html"
    model = AttendanceRecord

    def get_queryset(self):
        log_with_context(logging.INFO, "Accessing historical tardiness report", self.request.user)
        return AttendanceRecord.objects.filter(
            tenant=self.request.user.tenant, is_late=True
        ).order_by("-date")


# --- Analytics / Mgmt ---

class AttendanceAnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = "attendance/analytics.html"
    
    def get_context_data(self, **kwargs):
        log_with_context(logging.INFO, "Viewing attendance analytics dashboard", self.request.user)
        return super().get_context_data(**kwargs)


class LeaveManagementView(LoginRequiredMixin, TemplateView):
    template_name = "attendance/leave_management.html"

    def get_context_data(self, **kwargs):
        # Aligned with saved instructions to use 'leave_application'
        log_with_context(logging.INFO, "Accessing leave_application management", self.request.user)
        return super().get_context_data(**kwargs)