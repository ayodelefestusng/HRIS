import base64
import io
import random
from io import BytesIO

import pyotp
import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import (HttpResponse, HttpResponseRedirect,
                         HttpResponseServerError, JsonResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from .forms import (PasswordChangeForm, PasswordResetForm, PasswordSetupForm,
                    RegistrationForm, User, EmailLoginForm)

# Create your views here.
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags




def is_member_of(self, tenant_id):
        """
        Checks if the user belongs to a specific tenant.
        Critical for API security.
        """
        if self.is_superuser:
            return True
        return self.tenant_id == tenant_id

from org.models import Tenant
def email_login_viewv1(request):
    if request.method == "POST":
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"email": email, "tenant": Tenant.objects.get(name="DMC")}
            )
            # Explicitly set backend
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            next_url = request.GET.get("next", "/")
            return redirect(next_url)
    else:
        form = EmailLoginForm()
    return redirect("users:login")
    # return render(request, "hr:/email_login.html", {"form": form})
from django.shortcuts import redirect
from django.contrib.auth import login
from .forms import EmailLoginForm
from .models import User

def email_login_view(request):
    if request.method == "POST":
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # Try to fetch user by submitted email
            user = User.objects.filter(email=email).first()

            # If not found, fallback to default email
            if not user:
                email = "obinna.kelechi.adewale@dignityconcept.tech"
                user = User.objects.filter(email=email).first()

            # If user still not found, redirect back to login
            if not user:
                return redirect("users:login")

            # Explicitly set backend and log in
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            next_url = request.GET.get("next", "/")
            return redirect(next_url)
    else:
        form = EmailLoginForm()

    return redirect("users:login")


def about(request):
    return render(request,"about.html")

def contact(request):
    return render(request,"contact.html")




def home  (request):
    return render(request, "home.html")
    # return HttpResponse("I am okay")


def check_username(request):

    if request.method == "GET":
        return HttpResponse("Oya")
    elif request.method == "POST":
        email = request.POST.get('email')
        print("AJADI", email)

        if email and User.objects.filter(email=email).exists():
            return HttpResponse("This username already exists")
        return HttpResponse("")  # Empty response if email is available or not provided


@csrf_exempt
def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(None)  # User sets password later
            user.save()

            token = default_token_generator.make_token(user)
            link = request.build_absolute_uri(reverse("users:setup_password", args=[user.pk, token]))
            # link = f"{settings.SITE_DOMAIN}{reverse('users:setup_password', args=[user.pk, token])}"

            # send_mail(
            #     "Set Your Password",
            #     f"Click the link to set your password: {link}",
            #     settings.DEFAULT_FROM_EMAIL,
            #     [user.email],
            # )
            # Render HTML template
            html_content = render_to_string("emails/register_email.html", {
                    "user": user,
                    "ceate_link": link,
    
                })
            text_content = strip_tags(html_content)

            # Send email
            msg = EmailMultiAlternatives(
                subject="Set Your Password",
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            messages.success(request, "Registration successful! Please check your email to set your password.")

            # return render(request, "myapp/registration_success.html", {"email": user.email})
            return render(request, "registration/password_setup_sent.html", {"email": user.email})
    else:
        form = RegistrationForm()
    return render(request, "registration/register.html", {"form": form})

@csrf_exempt
def setup_password(request, user_id, token):
    user = User.objects.get(pk=user_id)
    if default_token_generator.check_token(user, token):
        if request.method == "POST":
            form = PasswordSetupForm(user, request.POST)
            if form.is_valid():
                form.save()
                return redirect("users:login")
                # return HttpResponseRedirect("login")
        else:
            form = PasswordSetupForm(user)
        return render(request, "registration/setup_password.html", {"form": form})
    else:
        return render(request, "registration/error.html", {"message": "Invalid token"})







@csrf_exempt
def password_reset_request(request):
    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            user = User.objects.filter(email=email).first()
            if user:
                token = default_token_generator.make_token(user)
                link = request.build_absolute_uri(reverse("users:setup_password", args=[user.pk, token]))
                
                # send_mail(
                #     "Reset Your Password",
                #     f"Click the link to reset your password: {link}",
                #     "admin@example.com",
                #     [email],
                # )
                  # Render HTML template
                html_content = render_to_string("emails/password_reset_email.html", {
                    "user": user,
                    "reset_link": link,
                })
                text_content = strip_tags(html_content)

                # Send email
                msg = EmailMultiAlternatives(
                    subject="Reset Your Password",
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    # from_email='Dignity Concept <upwardwave.dignity@gmail.com>',
                    to=[email],
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
            return render(request, "registration/password_reset_sent.html", {"email": email})
    else:
        form = PasswordResetForm()
    return render(request, "registration/password_reset.html", {"form": form})


@csrf_exempt
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = authenticate(email=request.user.email, password=form.cleaned_data["old_password"])
            if user:
                user.set_password(form.cleaned_data["new_password"])
                user.save()
                logout(request)
                return redirect("users:login")
            else:
                return render(request, "myapp/change_password.html", {"form": form, "error": "Incorrect password"})
    else:
        form = PasswordChangeForm()
    return render(request, "registration/change_password.html", {"form": form})

@csrf_exempt
def user_login1(request):
 
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)

        if user is not None:
            print("ijaya",user.mfa_secret)
            if not user.mfa_enabled:
                # Generate MFA secret and QR code
                user.mfa_secret = pyotp.random_base32()
                user.save()

                otp_uri = pyotp.totp.TOTP(user.mfa_secret).provisioning_uri(
                    name=user.email,
                    issuer_name="DMC Technologies"
                )

                qr = qrcode.make(otp_uri)
                buffer = io.BytesIO()
                qr.save(buffer, format="PNG")
                buffer.seek(0)
                qr_code = base64.b64encode(buffer.getvalue()).decode("utf-8")
                qr_code_data_uri = f"data:image/png;base64,{qr_code}"

                # Show QR code for first-time setup
                return render(request, 'registration/profile.html', {"qrcode": qr_code_data_uri,"email": email})

            # Redirect to OTP verification without logging in yet
            # return redirect(reverse("verify_mfa", kwargs={"email": email}))
            # return redirect(reverse("verify_mfa"))
            
            return render(request, 'registration/otp_verify.html', {"email": email})
        messages.error(request, "Invalid email or password. Please try again.",)
            
    
    return render(request, "registration/login.html")

from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render

@csrf_exempt
def user_login(request):
    
    next_url = request.GET.get("next") or reverse("users:home")  # Default to dashboard if no next
    print("request", request.GET.get("next"))
    print("next_url", next_url)
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)  # Log the user in
            # return render(request, 'registration/profile.html', {"email": email})
            return redirect(reverse("users:home"))  # Redirect to home page after login   
            print("next_urltttttt", next_url)  
            # return redirect(request.POST.get("next", next_url))  # Redirect to original destination

        else:
            messages.error(request, "Invalid email or password. Please try again.")

    return render(request, "registration/login.html")
@login_required
def profile_view(request):
        email = request.POST.get("email")
        user = User.objects.get(email=email)
        print("Ajayi", user)
        if not user.mfa_secret:
            user.mfa_secret = pyotp.random_base32()
            user.save()

        otp_uri = pyotp.totp.TOTP(user.mfa_secret).provisioning_uri(
            name=user.email,
            issuer_name="DMC Technologies"
        )

        qr = qrcode.make(otp_uri)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        
       
        buffer.seek(0)  
        qr_code = base64.b64encode(buffer.getvalue()).decode("utf-8")

        qr_code_data_uri = f"data:image/png;base64,{qr_code}"
        return render(request, 'registration/profile.html', {"qrcode": qr_code_data_uri})


def verify_2fa_otp(user, otp):
    totp = pyotp.TOTP(user.mfa_secret)
    if totp.verify(otp):
        user.mfa_enabled = True
        user.save()
        return True
    return False


def verify_mfa(request):
    # email = request.POST.get('email')
    # print ("aleko",request)

    # try:
    #     user = User.objects.get(email=email)
    # except User.DoesNotExist:
    #     messages.error(request, 'User not founds.')
    #     return redirect('login')

    if request.method == 'POST':
        otp = request.POST.get('otp_code')
        print ("otp",otp)
        email = request.POST.get('email')
        print ("email",email)

        user = User.objects.get(email=email)
       
        

        if verify_2fa_otp(user, otp):
            login(request, user)  # ✅ Only log in after successful OTP
            messages.success(request, 'Login successful with 2FA!')
            return redirect('users:home')
        else:
            messages.error(request, 'Invalid OTP code. Please try again.')
            return render(request, 'registration/otp_verify.html', {'email': email})

    return render(request, 'registration/otp_verify.html', {'email': email})




def reset_qr(request):
    if request.method == 'POST':
   
        email = request.POST.get('email')
        user=User.objects.get(email=email)
        user.mfa_enabled=False
        user.save()
    
        otp_uri = pyotp.totp.TOTP(user.mfa_secret).provisioning_uri(
            name=email,
            issuer_name="AGOBA DIGNITY"
        )

        qr = qrcode.make(otp_uri)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        
       
        buffer.seek(0)  
        qr_code = base64.b64encode(buffer.getvalue()).decode("utf-8")

        qr_code_data_uri = f"data:image/png;base64,{qr_code}"

        return render(request, 'registration/profile.html', {"qrcode": qr_code_data_uri})

    



@csrf_exempt
@login_required

def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("users:login")  # Redirect to login page after logout



# def save_user(self, request, sociallogin, form=None):
#     user = sociallogin.user
#     full_name = sociallogin.account.extra_data.get('name') or f"{sociallogin.account.extra_data.get('given_name', '')} {sociallogin.account.extra_data.get('family_name', '')}".strip()
#     if not user.full_name:
#         user.full_name = full_name
#     user.save()


from django.shortcuts import render

def terms_and_privacy(request):
    return render(request, 'registration/terms_and_privacy.html')

def solutions_overview(request):
    return render(request, 'home/solutions_overview.html')


# apps/home/views.py
from django.views.generic import TemplateView
from django.views.generic.list import ListView
from django.http import JsonResponse
from .models import Solution, SolutionCategory

class HomeView1(TemplateView):
    template_name = 'home/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_solutions'] = Solution.objects.filter(
            is_active=True
        ).select_related('category')[:6]
        context['solution_categories'] = SolutionCategory.objects.all()
        return context

class SolutionQuickView(ListView):
    template_name = 'partials/solution_quick_view.html'
    context_object_name = 'solutions'
    
    def get_queryset(self):
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            return Solution.objects.filter(
                category__slug=category_slug, 
                is_active=True
            )[:3]
        return Solution.objects.filter(is_active=True)[:3]

# apps/demo/views.py
from django.views.generic import CreateView, TemplateView
from django.urls import reverse_lazy
from .models import DemoBooking
from .forms import DemoBookingForm

# hd
class DemoBookingView(CreateView):
    model = DemoBooking
    form_class = DemoBookingForm
    template_name = 'demo/booking.html'
    success_url = reverse_lazy('demo_success')
    
    def form_valid(self, form):
        # Integrate with Calendly API
        response = super().form_valid(form)
        self.integrate_with_calendly(self.object)
        return response
    
    def integrate_with_calendly(self, booking):
        # Calendly integration logic
        pass

class DemoBookingPartialView(CreateView):
    model = DemoBooking
    form_class = DemoBookingForm
    template_name = 'partials/demo_form.html'
    
    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({
            'status': 'success',
            'message': 'Thank you! We will contact you shortly.'
        })
# apps/home/views.py
from django.views.generic import TemplateView

from django.views.generic import TemplateView
from users.models import Company    

class HomeView(TemplateView):
    print("HomeView")
    template_name = 'home/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['companies'] = Company.objects.all() # or .last(), or .get(id=1)
        return context

def solution_detail(request, slug):
    solution = get_object_or_404(Solution, slug=slug)
    return render(request, 'solution_detail.html', {'solution': solution})

from django.shortcuts import render

def platform_view(request):
    return render(request, 'platform.html')
def industries(request):
    return render(request, 'industries.html')
def industry_detail(request, industry_slug):
    return render(request, 'industry_detail.html', {'industry_slug': industry_slug})
def case_studies(request):
    return render(request, 'case_studies.html')
def case_study_detail(request, slug):
    return render(request, 'case_study_detail.html', {'slug': slug})
def blog_list(request):
    return render(request, 'blog_list.html')
def blog_detail(request, slug):
    return render(request, 'blog_detail.html', {'slug': slug})
def demo_booking(request):
    return render(request, 'demo_booking.html')
def thank_you(request):
    return render(request, 'thank_you.html')

# apps/demo/views.py
from django.views.generic import CreateView, TemplateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from .models import SolutionCategory
from .models import DemoBooking
from .forms import DemoBookingForm

class DemoBookingView(CreateView):
    model = DemoBooking
    form_class = DemoBookingForm
    template_name = 'demo/booking.html'
    success_url = reverse_lazy('demo_success')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['solution_categories'] = SolutionCategory.objects.prefetch_related(
            'solution_set'
        ).filter(solution__is_active=True).distinct()
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # You can add additional processing here, like:
        # - Send confirmation email
        # - Integrate with Calendly
        # - Notify sales team
        return response

class DemoSuccessView(TemplateView):
    template_name = 'demo/success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data for the success page
        return context

class DemoBookingPartialView(CreateView):
    model = DemoBooking
    form_class = DemoBookingForm
    template_name = 'partials/demo_form.html'
    
    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({
            'status': 'success',
            'message': 'Thank you! We will contact you shortly to schedule your demo.'
        })
    
    def form_invalid(self, form):
        return JsonResponse({
            'status': 'error',
            'errors': form.errors.get_json_data()
        }, status=400)

class CalendlyWebhookView(View):
    def post(self, request, *args, **kwargs):
        # Handle Calendly webhook integration
        # This would process Calendly booking confirmations
        pass
