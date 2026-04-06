import os

views_file = r'c:\Users\Pro\Desktop\PROJECT\Live\HR\myproject\customer\views.py'
urls_file = r'c:\Users\Pro\Desktop\PROJECT\Live\HR\myproject\customer\urls.py'

views_addition = """

# ──────────────────────────────────────────────────────────────────────────────
# NEW AUTHENTICATION & LOGIN VIEWS
# ──────────────────────────────────────────────────────────────────────────────
import random
from datetime import timedelta
from django.http import HttpResponse

class BankingLoginView(View):
    template_name = "banking/login.html"

    def get(self, request, *args, **kwargs):
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "")
        customer = Customer.objects.filter(phone_number=phone).first()
        if not customer:
            return HttpResponse("Customer not found", status=404)
        return render(request, self.template_name, {"phone": phone, "intent": intent})

    def post(self, request, *args, **kwargs):
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "")
        customer = Customer.objects.filter(phone_number=phone).first()
        if not customer:
            return HttpResponse("Customer not found", status=404)

        if customer.password_locked:
            return redirect(f"/banking/locked/?phone={phone}&intent={intent}")

        password = request.POST.get("password")
        if customer.check_password(password):
            customer.authenticated = True
            customer.password_attempts = 0
            customer.save(update_fields=['authenticated', 'password_attempts'])

            # Fastapi webhook CTA
            try:
                import requests
                requests.post("http://127.0.0.1:8000/webhook/trigger_cta", json={
                    "phone_number": customer.phone_number,
                    "event": "auth_completed",
                    "customer_name": customer.full_name,
                    "tenant_id": getattr(customer, "tenant_id", "DMC"),
                    "pending_intent": intent
                }, timeout=3)
            except Exception as e:
                logger.error(f"CTA webhook failed: {e}")

            return redirect(f"/banking/password-success/?name={customer.first_name}&acc={customer.account_number}")
        else:
            customer.password_attempts += 1
            if customer.password_attempts >= 5:
                customer.password_locked = True
                customer.save(update_fields=['password_attempts', 'password_locked'])
                return redirect(f"/banking/locked/?phone={phone}&intent={intent}")
            else:
                customer.save(update_fields=['password_attempts'])
                error_msg = f"Incorrect password. You have {5 - customer.password_attempts} attempt(s) remaining."
                return render(request, self.template_name, {"phone": phone, "intent": intent, "error": error_msg})


class BankingLockedView(View):
    template_name = "banking/locked.html"

    def get(self, request, *args, **kwargs):
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "")
        return render(request, self.template_name, {"phone": phone, "intent": intent})


class BankingForgotPasswordView(View):
    template_name = "banking/forgot_password.html"

    def get(self, request, *args, **kwargs):
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "")
        return render(request, self.template_name, {"phone": phone, "intent": intent})

    def post(self, request, *args, **kwargs):
        phone = request.GET.get("phone", "")
        intent = request.GET.get("intent", "")
        customer = Customer.objects.filter(phone_number=phone).first()
        if customer:
            # Generate OTP
            from django.utils import timezone
            customer.otp_code = f"{random.randint(0, 999999):06d}"
            customer.otp_expiry = timezone.now() + timedelta(minutes=5)
            customer.save(update_fields=['otp_code', 'otp_expiry'])

            logger.info(f"SMS Placeholder: Sent OTP {customer.otp_code} to {customer.phone_number}")

        return redirect(f"/banking/verify-otp/?phone={phone}&intent={intent}")


class BankingVerifyOTPView(View):
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
            return redirect(f"{PASSWORD_SETUP_PATH}/{token.token}/?intent={intent}")
        else:
            return render(request, self.template_name, {"phone": phone, "intent": intent, "error": "Invalid OTP. Please try again."})

"""

with open(views_file, "a", encoding="utf-8") as f:
    f.write(views_addition)

print("Views added.")

# Update the urls.py manually
urls_content = ""
with open(urls_file, "r", encoding="utf-8") as f:
    urls_content = f.read()

# Add imports
import_str = "    BankingLoginView, BankingLockedView, BankingForgotPasswordView, BankingVerifyOTPView,\\n"
urls_content = urls_content.replace(
    "PasswordSuccessView, SetPasswordView,LoanApplicationView,LoanConfirmedView",
    "PasswordSuccessView, SetPasswordView,LoanApplicationView,LoanConfirmedView,\\n" + import_str
)

# Add URL paths
url_paths = """
    path('banking/login/', BankingLoginView.as_view(), name='banking_login'),
    path('banking/locked/', BankingLockedView.as_view(), name='banking_locked'),
    path('banking/forgot-password/', BankingForgotPasswordView.as_view(), name='banking_forgot_password'),
    path('banking/verify-otp/', BankingVerifyOTPView.as_view(), name='banking_verify_otp'),
"""
if "banking/login/" not in urls_content:
    urls_content = urls_content.replace("urlpatterns = [", f"urlpatterns = [\\n{url_paths}")

with open(urls_file, "w", encoding="utf-8") as f:
    f.write(urls_content)

print("URLs added.")

# Also update SetPasswordView trigger CTA to pass pending_intent
views_content = ""
with open(views_file, "r", encoding="utf-8") as f:
    views_content = f.read()

target = '''"customer_name": customer.full_name,
                "tenant_id": getattr(customer, "tenant_id", "DMC")
            }, timeout=3)'''

replacement = '''"customer_name": customer.full_name,
                "tenant_id": getattr(customer, "tenant_id", "DMC"),
                "pending_intent": request.GET.get("intent")
            }, timeout=3)'''

if target in views_content:
    views_content = views_content.replace(target, replacement)
    with open(views_file, "w", encoding="utf-8") as f:
        f.write(views_content)
    print("SetPasswordView updated with incoming intent.")
else:
    print("Could not find SetPasswordView intent target.")
