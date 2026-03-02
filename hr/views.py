from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Conversation, Message
from .hr_bot import process_message
from employees.models import Employee
from attendance.models import AttendanceRecord
from leave.models import LeaveRequest
from workflow.models import WorkflowInstance
from .forms import ChatForm
import logging
from notifications.models import Notification

from org.views import log_with_context
import logging
from django.shortcuts import render
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)

# def log_with_context(level, message, user):
#     # Standardized helper to include | separator
#     tenant = getattr(user, "tenant", None)
#     username = getattr(user, "email", "Anonymous")
#     logger.log(
#         level,
#         f"tenant={tenant}|user={username}|{message}"
#     )


# def log_with_context(level, message, user, app_name="general"):
#     """
#     Enhanced helper to include App Name, Tenant, and User Email.
#     Format: app=leave|tenant=1|user=admin@company.com|message
#     """
#     tenant = getattr(user, "tenant", None)
#     email = getattr(user, "email", "Anonymous")


#     logger.log(
#         level,
#         f"app={app_name}|tenant={tenant}|user={email}|{message}"
#     )
def log_with_context1(level, message, request_or_user, app_name=None, module_name=None):
    if hasattr(request_or_user, "user"):  # it's a request
        request = request_or_user
        user = request.user
    else:  # it's a user
        request = None
        user = request_or_user

    tenant = getattr(user, "tenant", "N/A")
    email = getattr(user, "email", "Anonymous")

    # App name
    if not app_name and request and request.resolver_match:
        app_name = request.resolver_match.app_name or request.resolver_match.namespace
    app_name = app_name or "general"

    # Module name
    if not module_name and request and request.resolver_match:
        func = getattr(request.resolver_match, "func", None)
        if func:
            module_name = func.__module__
    module_name = module_name or "unknown"

    logger.log(
        level,
        f"app={app_name}|module={module_name}|tenant={tenant}|user={email}|{message}",
    )

from django.http import HttpResponseRedirect
def index(request):
    """
    Main Homepage / Dashboard Logic with proper logging context.
    """
    if not request.user.is_authenticated:
        # log_with_context(logging.WARNING, "Unauthenticated access attempt to dashboard.", request.user)

        # return render(request, "account/login.html")
        return HttpResponseRedirect("users/login/")

    tenant = request.user.tenant
    # log_with_context(logging.INFO, f"Accessing index view for tenant: {request}", request.user)
    print("Akdkdkdk", request)

    # Stats Context
    # Note: 'pending_leaves' maps to 'leave_application' state logic
    context = {
        "stats": {
            "employees_count": Employee.objects.filter(
                tenant=tenant, is_active=True
            ).count(),
            "attendance_today": AttendanceRecord.objects.filter(
                tenant=tenant, date=timezone.now().date(), work_status="PRESENT"
            ).count(),
            "pending_leaves": LeaveRequest.objects.filter(
                tenant=tenant, approval_status="pending"
            ).count(),
            "pending_workflows": WorkflowInstance.objects.filter(
                tenant=tenant, completed_at__isnull=True
            ).count(),
        }
    }

    # Chat History Logic
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    conversation, _ = Conversation.objects.get_or_create(
        session_id=session_key,
        is_active=True,
    )

    context["messages"] = conversation.messages.all().order_by("timestamp")
    context["chat_form"] = ChatForm()

    # log_with_context(logging.INFO, f"Dashboard rendered; chat history loaded (Session: {session_key})", request.user)
    logger.info("Dashboard rendered; chat history loaded (Session: %s)", session_key)
    return render(request, "hr_dashboard.html", context)

def confirm_resumption(request):
    try:
        employee = request.user.employee
        employee.work_status = 'ACTIVE'
        employee.save()
        
        # Notify Line Manager
        Notification.objects.create(
            recipient=employee.line_manager,
            message=f"{employee.full_name} has confirmed resumption from leave."
        )
        return JsonResponse({"status": "success"})
    except Exception as e:
        logger.error(f"Resumption Error: {str(e)}")
        return JsonResponse({"status": "error"}, status=500)





@login_required
def send_message(request):
    """
    AJAX Endpoint for the HR Bot with context-aware error logging.
    """
    if request.method == "POST":
        form = ChatForm(request.POST, request.FILES)
        if form.is_valid():
            user_message = form.cleaned_data["message"]
            attachment = form.cleaned_data["attachment"]

            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key

            # Save User Message
            conversation, _ = Conversation.objects.get_or_create(
                session_id=session_key, is_active=True
            )
            msg_obj = Message.objects.create(
                conversation=conversation,
                text=user_message,
                is_user=True,
                attachment=attachment,
            )

            log_with_context(
                logging.INFO,
                f"User sent message (Message ID: {msg_obj.id})",
                request.user,
            )

            # Process with Bot
            try:
                bot_response = process_message(
                    user_message,
                    session_key,
                    msg_obj.attachment.path if attachment else "",
                )

                answer_text = bot_response.get(
                    "answer", "I'm not sure how to help with that."
                )
                if isinstance(answer_text, list):
                    answer_text = " ".join([str(x) for x in answer_text])

                # Save Bot Message
                Message.objects.create(
                    conversation=conversation, text=answer_text, is_user=False
                )

                log_with_context(
                    logging.INFO, "Bot response generated successfully", request.user
                )
                return JsonResponse({"status": "success", "response": answer_text})

            except Exception as e:
                log_with_context(
                    logging.ERROR, f"Bot Processing Error: {str(e)}", request.user
                )
                return JsonResponse(
                    {
                        "status": "error",
                        "response": "I encountered an error processing your request.",
                    }
                )
        else:
            log_with_context(
                logging.WARNING, "Invalid ChatForm submission", request.user
            )
            return JsonResponse({"status": "error", "response": "Invalid input."})

    return JsonResponse({"status": "error", "response": "Invalid method."})


@login_required
def admin_tool(request):
    """
    Simple Admin Tool view for HR Admins.
    """
    if not request.user.is_hr_admin and not request.user.is_superuser:
        # Redirect or show 403
        return render(
            request, "403.html", status=403
        )  # assuming 403.html exists, or just redirect

    if request.method == "POST":
        # Handle announcement update logic here (stub)
        announcement = request.POST.get("announcement")
        # Save to DB or Cache...
        logger.info(f"Admin {request.user} updated announcement: {announcement}")
        pass

    return render(request, "hr/admin_tool.html")


def chat_home(request):
    return index(request)
