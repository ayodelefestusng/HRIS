import json
from math import log
import os
import logging
from django.http import JsonResponse
from django.views import View
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
import requests
from .models import Tenant_AI, Prompt,Opportunity # Assuming your models are in models.py
from org.models import Tenant
logger = logging.getLogger(__name__)
from .chat_bot import get_llm_instance
from .chat_bot import initialize_vector_store,process_message
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from typing import Any, Dict, List, Literal, Optional, Union, Annotated
@method_decorator(csrf_exempt, name='dispatch')
class OnboardTenantView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            logger.info("Onboard View Called")

            # --- Trigger Global LLM Check/Creation ---
            get_llm_instance()
            logger.info("Get Instance View Called")

            requested_prompt_type = data.get("prompt_type", "standard")
            default_prompt_name = os.getenv("name", "standard")

            with transaction.atomic():
                # Fetch or create prompt record
                prompt_record = Prompt.objects.filter(name=requested_prompt_type).first()

                if not prompt_record and requested_prompt_type != default_prompt_name:
                    logger.info(f"Prompt '{requested_prompt_type}' fallback to '{default_prompt_name}'")
                    prompt_record = Prompt.objects.filter(name=default_prompt_name).first()

                if not prompt_record:
                    logger.info(f"Creating '{default_prompt_name}' from env vars.")
                    prompt_record = Prompt.objects.create(
                        name=default_prompt_name,
                        is_hum_agent_allow_prompt=os.getenv("is_hum_agent_allow_prompt"),
                        no_hum_agent_allow_prompt=os.getenv("no_hum_agent_allow_prompt"),
                        summary_prompt=os.getenv("summary_prompt")
                    )

                # --- Tenant lookup ---
                tenant_code = data.get("tenant_id")  # assuming tenant_id is actually a code like "AY"

                if tenant_code:
                    # If tenant already exists, raise error
                    if Tenant.objects.filter(code=tenant_code).exists():
                        raise ValueError(f"Tenant with code '{tenant_code}' already exists.")
                    # Otherwise create new tenant
                    tenant_obj = Tenant.objects.create(
                        name=data.get("tenant_name", tenant_code),
                        code=tenant_code,
                        subdomain=tenant_code.lower(),
                        is_active=True
                    )
                else:
                    # Fallback to DMC if no tenant_id provided
                    tenant_obj = Tenant.objects.filter(code="DMC").first()
                    if not tenant_obj:
                        tenant_obj = Tenant.objects.create(
                            name="DMC",
                            code="DMC",
                            subdomain="dmc",
                            is_active=True
                        )

                # Create Tenant_AI
                new_tenant = Tenant_AI.objects.create(
                    tenant=tenant_obj,
                    prompt_template=prompt_record,
                    prompt_type=requested_prompt_type,
                    tenant_website=data.get("tenant_website"),
                    tenant_knowledge_base=data.get("tenant_knowledge_base"),
                    tenant_text=data.get("tenant_text"),
                    tenant_document=data.get("tenant_document"),
                    is_hum_agent_allow=data.get("is_hum_agent_allow"),
                    conf_level=data.get("conf_level"),
                    sentiment_threshold=data.get("sentiment_threshold"),
                    message_tone=data.get("message_tone"),
                    ticket_type=data.get("ticket_type"),
                    chatbot_greeting=data.get("chatbot_greeting")
                )

            # Trigger AI Indexing
            logger.info(f"Tenant {tenant_obj.code} committed. Initializing vector store.")
            initialize_vector_store(tenant_obj.code)

            return JsonResponse({"status": "success", "message": "Tenant onboarded successfully"}, status=201)

        except Exception as e:
            logger.error(f"Onboarding error: {e}")
            return JsonResponse({"error": str(e)}, status=400)
@method_decorator(csrf_exempt, name='dispatch')
class TenantDetailView(View):
    def get(self, request):
        tenant_code = request.GET.get('tenant_id')  # actually a code like "DMC" or "AY"
        logger.info(f"TenantDetailView GET called with tenant_code={tenant_code}")
        logger.info(f"Alukee={request}")
        if not tenant_code:
            logger.warning("No tenant_id provided in GET request.")
            return JsonResponse({"error": "tenant_id is required"}, status=400)

        tenant_obj = Tenant.objects.filter(code=tenant_code).first()
        if not tenant_obj:
            logger.error(f"Tenant with code '{tenant_code}' not found.")
            return JsonResponse({"error": "Tenant not found"}, status=404)

        tenant_ai = Tenant_AI.objects.filter(tenant=tenant_obj).first()
        if not tenant_ai:
            logger.error(f"Tenant_AI record for tenant '{tenant_code}' not found.")
            return JsonResponse({"error": "Tenant AI not found"}, status=404)

        return JsonResponse({
            "tenant_code": tenant_obj.code,
            "tenant_name": tenant_obj.name,
            "chatbot_greeting": tenant_ai.chatbot_greeting,
            "tenant_text": tenant_ai.tenant_text,
            "is_hum_agent_allow": tenant_ai.is_hum_agent_allow,
            "tenant_document": tenant_ai.tenant_document,
            "conf_level": tenant_ai.conf_level,
            "sentiment_threshold": tenant_ai.sentiment_threshold,
            "message_tone": tenant_ai.message_tone,
            "ticket_type": tenant_ai.ticket_type,
            
            # add other fields as needed
        })

    def post(self, request):  # Update Logic
        try:
            data = json.loads(request.body)
            tenant_code = data.get("tenant_id")
            logger.info(f"TenantDetailView POST called with tenant_code={tenant_code}")

            if not tenant_code:
                logger.warning("No tenant_id provided in POST request.")
                return JsonResponse({"error": "tenant_id is required"}, status=400)

            tenant_obj = Tenant.objects.filter(code=tenant_code).first()
            if not tenant_obj:
                logger.error(f"Tenant with code '{tenant_code}' not found.")
                return JsonResponse({"error": "Tenant not found"}, status=404)

            tenant_ai = Tenant_AI.objects.filter(tenant=tenant_obj).first()
            if not tenant_ai:
                logger.error(f"Tenant_AI record for tenant '{tenant_code}' not found.")
                return JsonResponse({"error": "Tenant AI not found"}, status=404)

            # Update fields dynamically
            for key, value in data.items():
                if key != "tenant_id" and hasattr(tenant_ai, key):
                    setattr(tenant_ai, key, value)
                    logger.debug(f"Updated {key} for tenant {tenant_code}")

            tenant_ai.save()
            initialize_vector_store(tenant_code)

            return JsonResponse({"status": "success", "message": "Tenant updated."})
        except Exception as e:
            logger.exception("Error updating tenant.")
            return JsonResponse({"error": str(e)}, status=500)
@method_decorator(csrf_exempt, name='dispatch')


class ChatView(View):
    def post(self, request):
        
        try:
            logger.info("ChatView POST called")

            if request.content_type == 'application/json':
                try:
                    data = json.loads(request.body)
                    logger.info(f"Received JSON data: {data}")
                except json.JSONDecodeError:
                    data = {}
                message_content = data.get("message_content") or data.get("message") or ""
                conversation_id = data.get("conversation_id")
                tenant_id = data.get("tenant_id")
                summarization_request = data.get("summarization_request") == True
                user_msg_attach = None
                employee_id=data.get("employee_id","obinna.kelechi.adewale@dignityconcept.tech")

            else:
                logger.info("Received non-JSON data")
                logger.info(f"POST data: {request.POST}")
                message_content = request.POST.get("message_content") or request.POST.get("message") or ""
                conversation_id = request.POST.get("conversation_id")
                tenant_id = request.POST.get("tenant_id")
                summarization_request = request.POST.get("summarization_request") == 'true'
                user_msg_attach = request.FILES.get("user_msg_attach")
                employee_id=request.POST.get("employee_id","obinna.kelechi.adewale@dignityconcept.tech")

            # get_or_create_global_llm()
            get_llm_instance()

            file_path = None
            if user_msg_attach:
                # Save using Django's storage system
                path = f"chat_attachments/{user_msg_attach.name}"
                file_path = default_storage.save(path, ContentFile(user_msg_attach.read()))
                # default_storage returns the final path (handles name collisions)
         
            # Call your async processing logic
            response = process_message(
                message_content=message_content,
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                 employee_id=employee_id,
                file_path=file_path,
                summarization_request=summarization_request
               
              
            )
            logger.info(f"Chat processing completed. Response: {response}")
            return JsonResponse(response)

        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            return JsonResponse({"error": "Internal Server Error"}, status=500)


class CRMPipelineView(LoginRequiredMixin, TemplateView):
    template_name = "workflow/crm_pipeline.html"

    def post(self, request, *args, **kwargs):
        action = request.GET.get('action')
        if action == 'move':
            opp_id = request.GET.get('id')
            to_stage = request.GET.get('to')
            try:
                opp = Opportunity.objects.get(pk=opp_id, tenant=request.user.tenant)
                # Instead of immediate update, trigger workflow
                opp.trigger_stage_transition(to_stage, request.user)
            except Opportunity.DoesNotExist:
                pass
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, 'tenant', None)
        
        # Group opportunities by stage
        stages = [choice[0] for choice in Opportunity.SALES_STAGE_CHOICES]
        pipeline = {stage: [] for stage in stages}
        
        opportunities = Opportunity.objects.filter(tenant=tenant).select_related('account', 'owner')
        for opp in opportunities:
            if opp.stage in pipeline:
                pipeline[opp.stage].append(opp)
        
        context['pipeline'] = pipeline
        context['stage_choices'] = Opportunity.SALES_STAGE_CHOICES
        return context


"""
banking_views.py
────────────────────────────────────────────────────────────────────────────────
Django views that power the password-creation and success pages.

URL wiring (see banking_urls.py):
  /banking/set-password/<uuid:token>/  →  SetPasswordView
  /banking/password-success/           →  PasswordSuccessView

Security checklist
  ✔ CSRF enforced (Django's CsrfViewMiddleware)
  ✔ Token validated: exists, unused, not expired
  ✔ Single-use: token.is_used = True immediately on success
  ✔ Password meets complexity rules before hashing
  ✔ PBKDF2/SHA-256 via Django's make_password
  ✔ Rate-limiting: bind this view behind django-ratelimit or nginx in prod
"""

import re
from django.contrib.auth.hashers import make_password
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

# ── Import from your models_update.py (adjust app label as needed) ────────────
from .models import Customer, PasswordSetupToken,PasswordResetOTP,PasswordResetOTP   # adjust import path

# ── Password complexity rule ──────────────────────────────────────────────────
# Min 8 chars · 1 uppercase · 1 lowercase · 1 digit · 1 special char
PASSWORD_PATTERN = re.compile(
    r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&#\-_])[A-Za-z\d@$!%*?&#\-_]{8,}$'
)

PASSWORD_REQUIREMENTS = (
    "Your password must be at least 8 characters and include: "
    "an uppercase letter, a lowercase letter, a number, and a "
    "special character (@$!%*?&#-)."
)


# ──────────────────────────────────────────────────────────────────────────────
# SET PASSWORD VIEW
# ──────────────────────────────────────────────────────────────────────────────

class SetPasswordView(View):
    """
    Renders and processes the password-creation form.
    The <token> in the URL is validated on every GET and POST.
    """
    template_name = "banking/set_password.html"

    def _get_valid_token(self, token_str: str) -> PasswordSetupToken:
        """
        Returns the PasswordSetupToken if it is valid.
        Raises Http404 on not-found; returns None when used/expired (caller handles).
        """
        try:
            token_obj = PasswordSetupToken.objects.select_related("customer").get(
                token=token_str
            )
        except PasswordSetupToken.DoesNotExist:
            raise Http404("This password setup link does not exist.")
        return token_obj

    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        token_obj = self._get_valid_token(token)

        if token_obj.is_used:
            return render(request, self.template_name, {
                "error_state": True,
                "error_title": "Link Already Used",
                "error_message": (
                    "This password setup link has already been used. "
                    "If you need to reset your password, please contact support "
                    "or request a new link via WhatsApp."
                ),
            })

        if timezone.now() >= token_obj.expires_at:
            return render(request, self.template_name, {
                "error_state": True,
                "error_title": "Link Expired",
                "error_message": (
                    "This password setup link has expired. "
                    "Please request a new link via WhatsApp."
                ),
            })

        customer = token_obj.customer
        return render(request, self.template_name, {
            "token":          str(token),
            "account_number": customer.account_number,
            "customer_name":  customer.full_name,
            "requirements":   PASSWORD_REQUIREMENTS,
        })

    def post(self, request: HttpRequest, token: str) -> HttpResponse:
        token_obj = self._get_valid_token(token)
        customer  = token_obj.customer

        context = {
            "token":          str(token),
            "account_number": customer.account_number,
            "customer_name":  customer.full_name,
            "requirements":   PASSWORD_REQUIREMENTS,
        }

        # ── Guard: token state ────────────────────────────────────────────────
        if token_obj.is_used:
            context["form_error"] = (
                "This link has already been used. Please request a new one via WhatsApp."
            )
            return render(request, self.template_name, context, status=410)

        if timezone.now() >= token_obj.expires_at:
            context["form_error"] = "This link has expired. Please request a new one."
            return render(request, self.template_name, context, status=410)

        # ── Extract & validate passwords ──────────────────────────────────────
        new_password     = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        if not new_password or not confirm_password:
            context["form_error"] = "Both password fields are required."
            return render(request, self.template_name, context, status=400)

        if new_password != confirm_password:
            context["form_error"] = "Passwords do not match. Please try again."
            return render(request, self.template_name, context, status=400)

        if not PASSWORD_PATTERN.match(new_password):
            context["form_error"] = PASSWORD_REQUIREMENTS
            return render(request, self.template_name, context, status=400)

        # ── Hash & persist password, invalidate token ─────────────────────────
        customer.password = make_password(new_password)
        customer.password_created = True
        customer.password_attempts = 0
        customer.password_locked = False
        customer.save(update_fields=["password", "password_created", "password_attempts", "password_locked"])

        token_obj.mark_used()  # sets is_used=True – link is now dead

        # ── Engage user via chatbot CTA (Webhook to FastAPI) ──────────────────
        try:
            import requests
            requests.post("http://127.0.0.1:8000/webhook/trigger_cta", json={
                "phone_number": customer.phone_number,
                "event": "password_created",
                "customer_name": customer.full_name,
                "tenant_id": getattr(customer, "tenant_id", "DMC"),
                "pending_intent": request.GET.get("intent")
            }, timeout=3)
        except Exception as e:
            logger.error(f"Failed to trigger CTA webhook: {e}")

        return redirect(
            f"/banking/password-success/"
            f"?name={customer.first_name}"
            f"&acc={customer.account_number}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# PASSWORD SUCCESS VIEW
# ──────────────────────────────────────────────────────────────────────────────

class PasswordSuccessView(View):
    """
    Simple success page advising the customer to return to WhatsApp.
    """
    template_name = "banking/password_success.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {
            "customer_name":  request.GET.get("name", ""),
            "account_number": request.GET.get("acc", ""),
        })


"""
loan_views.py
────────────────────────────────────────────────────────────────────────────────
Django views for the in-browser loan application confirmation page.

This page is shown when a customer wants to review and formally accept
their loan offer before it is finalised.

URL wiring (see loan_urls.py):
  /banking/loan/apply/<uuid:loan_id>/   →  LoanApplicationView
  /banking/loan/confirmed/              →  LoanConfirmedView

Flow
  1. apply_for_loan_tool creates a LoanApplication with disbursed=False.
  2. Bot sends the customer a link:
       https://yourapp.com/banking/loan/apply/<loan_id>/
  3. Customer reviews terms → clicks "Accept & Confirm".
  4. View sets disbursed=True, date_user_accept=now(), redirects to success.
"""

from decimal import Decimal
from django.contrib.auth.hashers import check_password as django_check
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View


# Adjust import paths to your actual app label
from .models import LoanApplication, LoanProfile, Customer, PasswordSetupToken


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

PASSWORD_SETUP_PATH = "/banking/set-password"


def _verify_customer_password(customer: Customer, raw_password: str) -> bool:
    """Verifies the customer's service password."""
    if not customer.password:
        return False
    return django_check(raw_password, customer.password)


# ──────────────────────────────────────────────────────────────────────────────
# LOAN APPLICATION VIEW
# ──────────────────────────────────────────────────────────────────────────────

class LoanApplicationView(View):
    """
    Displays the loan offer details and collects customer's password
    as final confirmation of acceptance.

    GET  → Show offer & password form.
    POST → Verify password → mark LoanApplication as accepted & disbursed.
    """
    template_name = "banking/loan_apply.html"

    def _get_application(self, loan_id: str):
        """Returns LoanApplication or raises Http404."""
        try:
            return LoanApplication.objects.select_related(
                "profile__customer", "loan_tier"
            ).get(loan_id=loan_id)
        except LoanApplication.DoesNotExist:
            raise Http404("Loan application not found.")

    def get(self, request: HttpRequest, loan_id: str) -> HttpResponse:
        application = self._get_application(loan_id)
        customer    = application.profile.customer
        tier        = application.loan_tier

        if application.disbursed:
            return render(request, self.template_name, {
                "already_accepted": True,
                "customer_name":    customer.full_name,
                "account_number":   customer.account_number,
            })

        context = self._build_context(application, customer, tier)
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, loan_id: str) -> HttpResponse:
        application = self._get_application(loan_id)
        customer    = application.profile.customer
        tier        = application.loan_tier
        context     = self._build_context(application, customer, tier)

        if application.disbursed:
            context["form_error"] = "This loan has already been accepted."
            return render(request, self.template_name, context, status=410)

        password = request.POST.get("password", "").strip()
        if not password:
            context["form_error"] = "Please enter your banking password to confirm."
            return render(request, self.template_name, context, status=400)

        # Password not yet set → send setup link
        if not customer.password_created and not customer.password:
            try:
                from .models import PasswordSetupToken
                from datetime import timedelta
                import uuid as _uuid
                token_str  = str(_uuid.uuid4())
                expires_at = timezone.now() + timedelta(hours=24)
                PasswordSetupToken.objects.create(
                    token=token_str,
                    customer=customer,
                    expires_at=expires_at,
                )
                setup_link = f"/customer{PASSWORD_SETUP_PATH}/{token_str}/"
            except Exception:
                setup_link = f"/customer{PASSWORD_SETUP_PATH}"

            context["form_error"] = (
                "You have not yet created a banking password. "
                f"Please set your password first: {request.build_absolute_uri(setup_link)}"
            )
            return render(request, self.template_name, context, status=403)

        if not _verify_customer_password(customer, password):
            context["form_error"] = (
                "Incorrect password. Please try again."
            )
            return render(request, self.template_name, context, status=400)

        # ── Accept & disburse ─────────────────────────────────────────────────
        application.disbursed       = True
        application.date_user_accept = timezone.now()
        application.save(update_fields=["disbursed", "date_user_accept"])

        # ── Engage user via chatbot CTA (Webhook to FastAPI) ──────────────────
        try:
            import requests
            requests.post("http://127.0.0.1:8000/webhook/trigger_cta", json={
                "phone_number": customer.phone_number,
                "event": "loan_accepted",
                "customer_name": customer.full_name,
                "tenant_id": getattr(customer, "tenant_id", "DMC"),
                "pending_intent": request.GET.get("intent")
            }, timeout=3)
        except Exception as e:
            logger.error(f"Failed to trigger CTA webhook: {e}")

        return redirect(
            f"/customer/banking/loan/confirmed/"
            f"?name={customer.first_name}"
            f"&acc={customer.account_number}"
            f"&amount={application.amount_requested}"
            f"&ref={str(application.loan_id)[:8].upper()}"
        )

    @staticmethod
    def _build_context(application, customer, tier) -> dict:
        amount   = Decimal(str(application.amount_requested))
        monthly  = Decimal(str(application.monthly_repayment))
        total    = Decimal(str(application.total_loan_due))
        interest = monthly - amount

        return {
            "loan_id":          str(application.loan_id),
            "customer_name":    customer.full_name,
            "account_number":   customer.account_number,
            "tier_name":        tier.name,
            "amount_requested": amount,
            "tenor":            application.tenor,
            "monthly_repayment":monthly,
            "total_loan_due":   total,
            "monthly_interest": interest,
            "interest_rate":    tier.monthly_interest_rate,
            "process_fee":      tier.process_fee,
            "late_fee":         tier.late_fee,
            "already_accepted": False,
        }


# ──────────────────────────────────────────────────────────────────────────────
# LOAN CONFIRMED VIEW
# ──────────────────────────────────────────────────────────────────────────────

class LoanConfirmedView(View):
    """
    Success page shown after the customer formally accepts their loan.
    """
    template_name = "banking/loan_confirmed.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {
            "customer_name":  request.GET.get("name", ""),
            "account_number": request.GET.get("acc", ""),
            "amount":         request.GET.get("amount", ""),
            "reference":      request.GET.get("ref", ""),
        })


# ──────────────────────────────────────────────────────────────────────────────
# NEW AUTHENTICATION & LOGIN VIEWS
# ──────────────────────────────────────────────────────────────────────────────
import random
from datetime import timedelta
from django.http import HttpResponse

class BankingLoginView(View):
    template_name = "banking/login.html"

    def get(self, request, token, *args, **kwargs):
        from django.utils import timezone
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "")

        setup_token = PasswordSetupToken.objects.filter(token=token, is_used=False).first()
        if not setup_token or (setup_token.expires_at and timezone.now() > setup_token.expires_at):
             return HttpResponse("Invalid or expired login link. Please request a new one from the chatbot.", status=403)

        customer = setup_token.customer
        if customer.phone_number != phone:
            logger.warning(f"Phone number mismatch for token {token}: expected {customer.phone_number}, got {phone}")
            return HttpResponse("Account mismatch.", status=403)

        # Task 2: Redirection logic
        if not customer.password_created:
             logger.info(f"Password not set for {customer.phone_number}. Redirecting to set_password.")
             return redirect(f"/customer/banking/set-password/{token}/?phone={phone}&intent={intent}")

        if customer.password_locked:
            logger.warning(f"Locked account access for {customer.phone_number}. Redirecting to banking_locked.")
            return redirect(f"/customer/banking/locked/{token}/?phone={phone}&intent={intent}")

        account_number = customer.account_number
        full_name = customer.full_name
        logger.info(f"Rendering login page for {customer.phone_number} with intent: {intent}")
        return render(request, self.template_name, {
            "phone": phone, 
            "account_number": account_number, 
            "full_name": full_name, 
            "intent": intent,
            "token": token
        })



    def post(self, request, token, *args, **kwargs):
        from django.utils import timezone
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "")

        setup_token = PasswordSetupToken.objects.filter(token=token, is_used=False).first()
        if not setup_token or (setup_token.expires_at and timezone.now() > setup_token.expires_at):
            logger.warning(f"Expired login link attempted for token {token}")
            return HttpResponse("Invalid or expired login link.", status=403)

        customer = setup_token.customer
        if customer.phone_number != phone:
            logger.warning(f"Phone number mismatch for token {token}: expected {customer.phone_number}, got {phone}")
            return HttpResponse("Account mismatch.", status=403)

        if customer.password_locked:
            # For locked accounts, we still need a token for the locked view 
            # But the login itself is blocked.
            logger.warning(f"Locked account login attempt for {customer.phone_number}")
            return redirect(f"/customer/banking/locked/{token}/?phone={phone}&intent={intent}")

        password = request.POST.get("password")
        if customer.check_password(password):
            customer.authenticated = True
            customer.password_attempts = 0
            customer.save(update_fields=['authenticated', 'password_attempts'])

            # Mark token as used to prevent replay
            setup_token.is_used = True
            setup_token.save(update_fields=['is_used'])

            # Fastapi webhook CTA
            try:
                import requests
                logger.info(f"Triggering CTA for {customer.phone_number} with intent: {intent}")
                requests.post("http://127.0.0.1:8000/webhook/trigger_cta", json={
                    "phone_number": customer.phone_number,
                    "event": "auth_completed",
                    "customer_name": customer.full_name,
                    # "tenant_id": getattr(customer, "tenant_id", "DMC"),
                    "tenant_id": str(getattr(customer, "tenant_id", "DMC")),  # cast to string
                    "pending_intent": intent
                }, timeout=3)
                # requests.post("http://[IP_ADDRESS]/webhook/trigger_cta", json={
                #     "phone_number": customer.phone_number,
                #     "event": "auth_completed",
                #     "customer_name": customer.full_name,
                #     "tenant_id": getattr(customer, "tenant_id", "DMC"),
                #     "pending_intent": intent
                # }, timeout=3)
                logger.info(f"CTA triggered for {customer.phone_number} with intent: {intent}")
            except Exception as e:
                logger.error(f"CTA webhook failed: {e}")
            logger.info(f"Redirect to Success Page :  {customer.phone_number} with intent: {intent}")
            return redirect(f"/customer/banking/password-success/?name={customer.first_name}&acc={customer.account_number}")
        else:
            customer.password_attempts += 1
            if customer.password_attempts >= 5:
                customer.password_locked = True
                customer.save(update_fields=['password_attempts', 'password_locked'])
                return redirect(f"/customer/banking/locked/{token}/?phone={phone}&intent={intent}")
            else:
                customer.save(update_fields=['password_attempts'])
                error_msg = f"Incorrect password. You have {5 - customer.password_attempts} attempt(s) remaining."
                return render(request, self.template_name, {"phone": phone, "intent": intent, "error": error_msg, "token": token})


class BankingLockedView(View):
    template_name = "banking/locked.html"

    def get(self, request, token, *args, **kwargs):
        logger.warning(f"Accessing locked account page with token {token}")
        from django.utils import timezone
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "")
        
        setup_token = PasswordSetupToken.objects.filter(token=token, is_used=False).first()
        if not setup_token or (setup_token.expires_at and timezone.now() > setup_token.expires_at):
            logger.warning(f"Invalid or expired token access to locked view for token {token}")
            return HttpResponse("Invalid or expired link.", status=403)
        logger.info(f"Rendering locked account page for {phone} with intent: {intent}")
        return render(request, self.template_name, {"phone": phone, "intent": intent, "token": token})

    def post(self, request, token, *args, **kwargs):
        from django.utils import timezone
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "")
        
        setup_token = PasswordSetupToken.objects.filter(token=token, is_used=False).first()
        if not setup_token or (setup_token.expires_at and timezone.now() > setup_token.expires_at):
            logger.warning(f"Invalid or expired token attempt to unlock account for token {token}")
            return HttpResponse("Invalid or expired link.", status=403)

        customer = setup_token.customer
        if customer:
            # Generate OTP
            customer.otp_code = f"{random.randint(0, 999999):06d}"
            customer.otp_expiry = timezone.now() + timedelta(minutes=5)
            customer.save(update_fields=['otp_code', 'otp_expiry'])

            logger.info(f"SMS Placeholder: Sent OTP {customer.otp_code} to {customer.phone_number}")
        
        return redirect(f"/customer/banking/verify-otp/?phone={phone}&intent={intent}")


class BankingForgotPasswordView(View):
    template_name = "banking/forgot_password.html"

    def get(self, request, token, *args, **kwargs):
        from django.utils import timezone
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "forgot_password")
        
        setup_token = PasswordSetupToken.objects.filter(token=token, is_used=False).first()
        if not setup_token or (setup_token.expires_at and timezone.now() > setup_token.expires_at):
             return HttpResponse("Invalid or expired reset link.", status=403)
        
        customer = setup_token.customer
        if not customer.password_created:
            logger.info(f"Password not set for {customer.phone_number}. Redirecting to set_password.")
            return redirect(f"/customer/banking/set-password/{token}/?phone={phone}&intent={intent}")

        logger.info(f"Rendering forgot password page for {phone} with intent: {intent}")
        return render(request, self.template_name, {"phone": phone, "intent": intent, "token": token})

    def post(self, request, token, *args, **kwargs):
        from django.utils import timezone
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "forgot_password")

        # Validate token first
        setup_token = PasswordSetupToken.objects.filter(token=token, is_used=False).first()
        if not setup_token or (setup_token.expires_at and timezone.now() > setup_token.expires_at):
            logger.warning(f"Invalid or expired reset link attempt for token {token}")
            return HttpResponse("Invalid or expired reset link. Please request a new one via WhatsApp.", status=403)

        customer = setup_token.customer
        if customer.phone_number != phone:
            logger.warning(f"Phone number mismatch for forgot password token {token}: expected {customer.phone_number}, got {phone}")
            return HttpResponse("Account mismatch.", status=403)

        # Fetch tenant with DMC fallback
        tenant_id_raw = request.GET.get("tenant_id")
        tenant_obj = None
        if tenant_id_raw:
            if str(tenant_id_raw).isdigit():
                tenant_obj = Tenant.objects.filter(id=tenant_id_raw).first()
            else:
                tenant_obj = Tenant.objects.filter(code=tenant_id_raw).first()
        
        if not tenant_obj:
            tenant_obj = Tenant.objects.filter(code="DMC").first()

        # Generate 10-second OTP
        otp_obj = PasswordResetOTP.generate_for(customer, tenant=tenant_obj)
        
        # Log/Mock SMS
        logger.info(f"OTP for {customer.phone_number}: {otp_obj.otp_code} (Expires in 10s)")
        
        # In a real system, we'd trigger an SMS service here
        # For now, we'll store it in the session or rely on the DB
        request.session['pending_otp_ref'] = str(otp_obj.id)
        logger.info(f"Redirecting to OTP verification for {customer.phone_number} with intent: {intent}")
        return redirect(f"/customer/banking/verify-otp/{token}/?phone={phone}&intent={intent}")


class BankingVerifyOTPView(View):
    template_name = "banking/otp_verify.html"

    def get(self, request, token, *args, **kwargs):
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "")
        logger.info(f"Rendering OTP verification page for {phone} with intent: {intent}")
        return render(request, self.template_name, {"phone": phone, "intent": intent, "token": token})

    def post(self, request, token, *args, **kwargs):
        from django.utils import timezone
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "")
        otp_submitted = request.POST.get("otp_code", "")

        otp_id = request.session.get('pending_otp_ref')
        if not otp_id:
            logger.warning(f"No pending OTP reference found in session for {phone}")
            return render(request, self.template_name, {"phone": phone, "error": "No pending verification found."})

        try:
            otp_obj = PasswordResetOTP.objects.get(id=otp_id, is_used=False)
            if not otp_obj.is_valid:
                logger.warning(f"Expired or used OTP attempted for {phone}")
                return render(request, self.template_name, {"phone": phone, "error": "Code expired. Please request a new one."})

            if otp_obj.otp_code != otp_submitted:
                logger.warning(f"Invalid OTP submitted for {phone}")
                return render(request, self.template_name, {"phone": phone, "error": "Invalid code. Please try again."})

            # Success
            otp_obj.mark_used()
            
            # If it was a login/auth flow, we might mark customer as authenticated
            # If it's forgot password, we redirect to SetPasswordView
            if intent == "forgot_password" or intent == "change_password":
                logger.info(f"OTP verified for {phone}. Redirecting to password setup with intent: {intent}")
                return redirect(f"/customer/banking/set-password/{token}/?phone={phone}&intent={intent}")
            logger.info(f"OTP verified for {phone}. Redirecting to success page with intent: {intent}")
            return redirect(f"/customer/banking/password-success/")

        except PasswordResetOTP.DoesNotExist:
            logger.warning(f"Invalid OTP reference for {phone}")
            return render(request, self.template_name, {"phone": phone, "error": "Invalid session."})


class BankingChangePasswordView(View):
    """
    Initiates change password flow by requiring OTP first.
    """
    def get(self, request, token, *args, **kwargs):
        phone = request.GET.get("phone", "")
        intent = "change_password"
        
        setup_token = PasswordSetupToken.objects.filter(token=token, is_used=False).first()
        if not setup_token:
            logger.warning(f"Invalid token attempt for change password with token {token}")
            return HttpResponse("Invalid token.", status=403)
            
        customer = setup_token.customer
        
        # Fetch tenant with DMC fallback
        tenant_id_raw = request.GET.get("tenant_id")
        tenant_obj = None
        if tenant_id_raw:
            if str(tenant_id_raw).isdigit():
                tenant_obj = Tenant.objects.filter(id=tenant_id_raw).first()
            else:
                tenant_obj = Tenant.objects.filter(code=tenant_id_raw).first()
        
        if not tenant_obj:
            tenant_obj = Tenant.objects.filter(code="DMC").first()

        otp_obj = PasswordResetOTP.generate_for(customer, tenant=tenant_obj)
        logger.info(f"Change Password OTP for {customer.phone_number}: {otp_obj.otp_code}")
        request.session['pending_otp_ref'] = str(otp_obj.id)
        logger.info(f"Redirecting to OTP verification for change password for {customer.phone_number} with intent: {intent}")
        return redirect(f"/customer/banking/verify-otp/{token}/?phone={phone}&intent={intent}")
        #     customer.otp_code = f"{random.randint(0, 999999):06d}"
        #     customer.otp_expiry = timezone.now() + timedelta(minutes=5)
        #     customer.save(update_fields=['otp_code', 'otp_expiry'])

        #     logger.info(f"SMS Placeholder: Sent OTP {customer.otp_code} to {customer.phone_number}")

        # return redirect(f"/customer/banking/verify-otp/?phone={phone}&intent={intent}")


class BankingVerifyOTPViewv1(View):
    template_name = "banking/verify_otp.html"

    def get(self, request, *args, **kwargs):
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "")
        return render(request, self.template_name, {"phone": phone, "intent": intent})

    def post(self, request, *args, **kwargs):
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "")
        otp = request.POST.get("otp")

        customer = Customer.objects.filter(phone_number=phone).first()
        if not customer:
            return HttpResponse("Customer not found", status=404)
            
        from django.utils import timezone

        if customer.otp_code and customer.otp_code == otp:
            if timezone.now() > customer.otp_expiry:
                return render(request, self.template_name, {"phone": phone, "intent": intent, "error": "OTP has expired."})
            
            customer.otp_code = ""
            customer.password_locked = False
            customer.password_attempts = 0
            customer.save(update_fields=['otp_code', 'password_locked', 'password_attempts'])

            from .models import PasswordSetupToken
            import uuid
            token = PasswordSetupToken.objects.create(
                token=str(uuid.uuid4()),
                customer=customer,
                expires_at=timezone.now() + timedelta(hours=24)
            )
            return redirect(f"/customer{PASSWORD_SETUP_PATH}/{token.token}/?intent={intent}")
        else:
            return render(request, self.template_name, {"phone": phone, "intent": intent, "error": "Invalid OTP. Please try again."})



from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Prompt
# from .vfd_client import VFDBillsPaymentClient, get_access_token  # adjust import paths

# from typing import Optional, List, Dict, Any
# BASE_URL = "https://api-devapps.vfdbank.systems/vtech-wallet/api/v2/wallet2"
# yourConsumerKey="mL1dqaMcB760EP3fR18Vc23qUSZy"
# yourConsumerSecret="ohAWPpabbj0UmMppmOgAFTazkjQt"
# AUTH_URL         = os.getenv("VFD_AUTH_URL",
#     "https://api-devapps.vfdbank.systems/vfd-tech/baas-portal/v1.1/baasauth/token"
# )


def _get_access_token_bot() -> str:
    from typing import Optional, List, Dict, Any
    BASE_URL = "https://api-devapps.vfdbank.systems/vtech-wallet/api/v2/wallet2"
    # yourConsumerKey="mL1dqaMcB760EP3fR18Vc23qUSZy"
    # yourConsumerSecret="ohAWPpabbj0UmMppmOgAFTazkjQt"


    yourConsumerKey     = os.getenv("VFD_CONSUMER_KEY",    "mL1dqaMcB760EP3fR18Vc23qUSZy")
    yourConsumerSecret  = os.getenv("VFD_CONSUMER_SECRET", "ohAWPpabbj0UmMppmOgAFTazkjQt")
    AUTH_URL         = os.getenv("VFD_AUTH_URL",
    "https://api-devapps.vfdbank.systems/vfd-tech/baas-portal/v1.1/baasauth/token"
)

    print("Requesting VFD access token...")
    logger.info("Initiating request to fetch VFD access token.")
    
    payload = {
        "consumerKey":    yourConsumerKey,
        "consumerSecret": yourConsumerSecret,
        "validityTime":   "-1",
    }
    resp = requests.post(
        AUTH_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    data = resp.json()
    if data.get("status") == "00":
        return data["data"]["access_token"]
    raise RuntimeError(f"VFD auth failed: {data}")


# token = get_access_token()
token = _get_access_token_bot()


class VFDBillsPaymentClient:
    def __init__(self, access_token: str):
        self.base_url = "https://api-devapps.vfdbank.systems/vtech-bills/api/v2/billspaymentstore"
        self.headers = {
            "AccessToken": access_token,
            "Content-Type": "application/json"
        }
    def get_biller_items(self, biller_id: str, division_id: str, product_id: str) -> Optional[List[Dict[str, Any]]]:
        endpoint = f"{self.base_url}/billerItems?billerId={biller_id}&divisionId={division_id}&productId={product_id}"
        try:
            logger.info(f"Fetching biller items for {biller_id}")
            response = requests.get(endpoint, headers=self.headers, timeout=10)
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") == "00":
                return payload["data"].get("paymentitems", [])
            logger.error(f"Unsuccessful status for biller items: {payload.get('message')}")
            return None
        except Exception as e:
            logger.error(f"Error fetching biller items: {e}")
            return None
    def get_biller_categories(self) -> Optional[List[Dict[str, Any]]]:
        endpoint = f"{self.base_url}/billercategory"
        try:
            logger.info(f"Fetching biller categories from {endpoint}")
            response = requests.get(endpoint, headers=self.headers, timeout=10)
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") == "00":
                return payload.get("data", [])
            logger.error(f"Unsuccessful status: {payload.get('message')}")
            return None
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            return None

    def get_billers_by_category(self, category_name: str) -> Optional[List[Dict[str, Any]]]:
        endpoint = f"{self.base_url}/billerlist?categoryName={category_name}"
        try:
            logger.info(f"Fetching billers for category {category_name} from {endpoint}")
            response = requests.get(endpoint, headers=self.headers, timeout=10)
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") == "00":
                return payload.get("data", [])
            logger.error(f"Unsuccessful status for {category_name}: {payload.get('message')}")
            return None
        except Exception as e:
            logger.error(f"Error fetching billers for {category_name}: {e}")
            return None
    

    def get_all_billers(self) -> List[Dict[str, Any]]:
        """
        Iterates over all categories and fetches billers for each.
        Returns a combined list of all billers.
        """
        all_billers: List[Dict[str, Any]] = []
        categories = self.get_biller_categories()
        if not categories:
            logger.error("No categories found, cannot fetch billers.")
            return []

        for cat in categories:
            category_name = cat.get("category")
            if not category_name:
                continue
            billers = self.get_billers_by_category(category_name)
            if billers:
                all_billers.extend(billers)

        logger.info(f"Total billers fetched: {len(all_billers)}")
        return all_billers


def update_biller_items(request):
    """
    Fetch billers from VFDBillsPaymentClient and update the Prompt.biller_items field
    for tenant 'DMC'. Always fetches fresh data when endpoint is called.
    """
    prompt = get_object_or_404(Prompt, tenant__name="DMC", name="standard")

    token = _get_access_token_bot()
    client = VFDBillsPaymentClient(access_token=token)

    all_billers = client.get_all_billers()
    if not all_billers:
        return JsonResponse({"status": "error", "message": "No billers retrieved"}, status=500)

    enriched_billers = []
    for biller in all_billers:
        biller_id = biller.get("id")
        division = biller.get("division")
        product_id = biller.get("product")
        payment_items = client.get_biller_items(biller_id, division, product_id) or []
        biller["payment_items"] = payment_items
        enriched_billers.append(biller)

    # Save enriched JSON into the Prompt model
    prompt.biller_items = enriched_billers
    prompt.save(update_fields=["biller_items", "updated_at"])

    return JsonResponse({
        "status": "success",
        "message": f"Updated {len(enriched_billers)} billers for tenant DMC",
        "biller_count": len(enriched_billers)
    })
