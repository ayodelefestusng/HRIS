# myproject/myapp/forms.py

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Fieldset, Layout, Submit
from django import forms
from django.contrib.auth.forms import (AuthenticationForm, PasswordResetForm,
                                       SetPasswordForm)
from django.urls import reverse_lazy

from .models import \
    User  # Currency,; Country,; Client,; BranchDetails,; TellerDetails,; Customer,; Transaction,; BranchAccountTill,; AccountTransactionT,; Crispy,; validate_nigerian_prefix,

#from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'full_name', 'tenant', 'password1', 'password2')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('email', 'full_name', 'tenant', 'is_active', 'is_staff', 'is_superuser')




class RegistrationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "full_name" ]
        widgets = {
            'email': forms.EmailInput(attrs={
                'hx-post': reverse_lazy('users:check_username'),
                'hx-trigger': 'keyup',
                'hx-target': '#username-err'
            }),
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_action = reverse_lazy('users:register')
        self.helper.form_method = ('POST')
        self.helper.add_input(Submit('submit', 'Register'))
        self.helper.layout = Layout(
        
            Field('email'),
            # This is the custom div with id "ayo"
            HTML('<div class="text-danger mt-2" id="username-err"></div>'),
             HTML('<div class="custom-divider"></div>'),
             HTML('<p></p>'),
            Field('full_name'),
        )

    
    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email





class RegistrationForm6666(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "full_name" ]
        widgets = {
            'email': forms.EmailInput(attrs={
                'hx-post': reverse_lazy('users:check_username'),
                'hx-trigger': 'keyup',
                'hx-target': '#username-err'
            }),
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_action = reverse_lazy('register')
        self.helper.form_method = ('POST')
        self.helper.add_input(Submit('submit', 'Register'))
        self.helper.layout = Layout(
        
            Field('email'),
            # This is the custom div with id "ayo"
            HTML('<div class="text-danger mt-2" id="username-err"></div>'),
             HTML('<div class="custom-divider"></div>'),
             HTML('<p> div.</p>'),
            Field('full_name'),
        )

    
    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class PasswordSetupForm(SetPasswordForm):
    pass

        
class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(widget=forms.PasswordInput)
 


# class SenderAccountLookupForm(forms.ModelForm):
#     class Meta:
#         model = Customer
#         fields = ["account_number"]
#         widgets = {
#             "account_number": forms.TextInput(attrs={
#                 "hx-post": reverse_lazy("check_account"),
#                 'hx-trigger': 'keyup',
#                 'hx-target': '#account-err',
#                 # "autocomplete": "off",
#             }),
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.form_action = reverse_lazy('sender_with_account_lookup')
#         self.helper.form_method = ('POST')
#         # self.helper.add_input(Submit('submit', 'Look UP'))
#         self.helper.layout = Layout(
        
#             Field('account_number'),
#             # This is the custom div with id "ayo"
#             HTML('<div class="text-dark  mt-2" id="account-err"></div>'),
#             #  HTML('<div class="custom-divider">-- Divider Between Names --</div>'),
#             #  HTML('<p>More content inside the "ayo" div.</p>'),
#         )



#     def clean_account_number(self):
#         return self.cleaned_data["account_number"].strip()





# class CountryForm(forms.ModelForm):
#     class Meta:
#         model = Country
#         fields = ['name', 'currency']
#         widgets = {
#             'name': forms.TextInput(attrs={'class': 'form-control'}),
#             'currency': forms.Select(attrs={'class': 'form-control'}),
#         }


# class TransactionForm(forms.ModelForm):
#     class Meta:
#         model = Transaction
#         fields = [
#             'sender_name',
#             'beneficiary_name',
#             'beneficiary_address',
#             'beneficiary_phone',
#             'transaction_amount',
#             'created_by',
#             'destination_country',
#             'exchange_rate',
#         ]
#         widgets = {
#             'sender': forms.Select(attrs={'class': 'form-control'}),
#             'beneficiary_name': forms.TextInput(attrs={'class': 'form-control'}),
#             'beneficiary_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
#             'beneficiary_phone': forms.TextInput(attrs={'class': 'form-control'}),
#             'transaction_amount': forms.NumberInput(attrs={'class': 'form-control'}),
#             'created_by': forms.Select(attrs={'class': 'form-control'}),
#             'destination_country': forms.Select(attrs={'class': 'form-control'}),
#             'exchange_rate': forms.Select(attrs={'class': 'form-control'}),
#         }

#     def clean_transaction_amount(self):
#         amount = self.cleaned_data.get('transaction_amount')
#         if amount <= 0:
#             raise forms.ValidationError("Transaction amount must be greater than zero.")
#         return amount
#     class Meta:
#         model = Transaction
#         fields = [
#             'sender_name',
#             'beneficiary_name',
#             'beneficiary_address',
#             'beneficiary_phone',
#             'transaction_amount',
#             'destination_country',
#             'exchange_rate',
#         ]
#         widgets = {
#             'beneficiary_address': forms.Textarea(attrs={'rows': 3}),
#             'transaction_amount': forms.NumberInput(attrs={'step': '0.01'}),
#             'destination_country': forms.Select(),
#         }
#         labels = {
#             'sender_name': 'Sender',
#             'beneficiary_name': 'Beneficiary Name',
#             'beneficiary_address': 'Beneficiary Address',
#             'beneficiary_phone': 'Beneficiary Phone',
#             'transaction_amount': 'Amount to Send',
#             'destination_country': 'Destination Country',
#             'exchange_rate': 'Exchange Rate',
#         }

#     def __init__(self, *args, **kwargs):
#         user = kwargs.pop('user', None)
#         super(TransactionForm, self).__init__(*args, **kwargs)
#         if user:
#             self.instance.created_by = user


# class WalkinForm(forms.ModelForm):
#     class Meta:
#         model = Transaction
#         # fields = ["email","name",'phone']
#         fields =  ["sender_phone",'beneficiary_name',"beneficiary_address","beneficiary_phone","transaction_amount","destination_country"]
        

# class AccountHoldernForm(forms.ModelForm):
#     class Meta:
#         model = Transaction
#         # fields = ["email","name",'phone']
#         fields =  ["sender_phone",'beneficiary_name',"beneficiary_address","beneficiary_phone","transaction_amount","destination_country"]
        

# class PhoneValidation(forms.ModelForm):
#     class Meta:
#         model = Customer
#         fields = ["phone"]

#     def clean_phone(self):
#         phone = self.cleaned_data.get("phone")

#         # Run model-level validator
#         try:
#             validate_nigerian_prefix(phone)
#         except forms.ValidationError as e:
#             raise forms.ValidationError(f"Invalid phone number: {e.message}")

#         # Check for duplicates, excluding current instance (for updates)
#         if Customer.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
#             raise forms.ValidationError("This phone number is already registered.")

#         return phone
    

# class CustomerForm(forms.ModelForm):
#     class Meta:
#         model = Customer
#         fields = ['name', 'phone', 'address', 'account_number', 'account_bal']
#         widgets = {
#             'address': forms.Textarea(attrs={'rows': 3}),
#         }

#     def clean_account_number(self):
#         account_number = self.cleaned_data['account_number']
#         if Customer.objects.filter(account_number=account_number).exists():
#             raise forms.ValidationError("🚫 This account number already exists.")
#         return account_number

#     def clean_phone(self):
#         phone = self.cleaned_data['phone']
#         # if Customer.objects.filter(phone=phone).exists():
#         #     raise forms.ValidationError("🚫 This phone number is already registered.")
#         return phone

# class TransactionWithAccountForm(forms.ModelForm):
#     class Meta:
#         model = Transaction
#         fields = [
#             "beneficiary_name", "beneficiary_phone",
#             "transaction_amount", "sender_address",
#             "beneficiary_address", "destination_country"
#         ]
#         widgets = {
#             "transaction_amount": forms.TextInput(attrs={
#                 "hx-post": reverse_lazy("balance_check"),
#                 "hx-trigger": "keyup",
#                 "hx-target": "#balance_check",
#                 # "autocomplete": "off",
#             }),
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.form_method = 'POST'
#         # self.helper.add_input(Submit('submit', 'Look UP'))
#         self.helper.layout = Layout(
#             Field('beneficiary_name'),
#             Field('beneficiary_phone'),
#             Field('transaction_amount'),
#             HTML('<div class="text-danger mt-2" id="balance_check"></div>'),
#             Field('sender_address'),
#             Field('beneficiary_address'),
#             Field('destination_country'),
#             # HTML('<div class="custom-divider">-- Divider Between Names --</div>'),
#             # HTML('<div class="text-danger mt-2" id="balance_check2">Another div!</div>'),
#             # HTML('<p>More content inside the "ayo" div.</p>'),
#         )
# class TransactionWithoutAccountForm(forms.ModelForm):
#     class Meta:
#         model = Transaction
#         fields = [
#             "sender_name", "sender_phone","sender_address",
#             "beneficiary_name", "beneficiary_address", "beneficiary_phone",
#             "transaction_amount", "destination_country"
#         ]



# class CustomLoginForm(AuthenticationForm):
#     username = forms.CharField(label="Username", widget=forms.TextInput(attrs={'placeholder': 'Username'}))
#     password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))


# class UserForm(forms.ModelForm):
#     class Meta:
#         model = User
#         fields = ['email', 'phone', 'full_name']

 
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.layout = Layout(
#             Field('email'),
#     #     Fieldset(
#     #     'Tell us your favorite stuff {{ username }}',
#     #     'like_website',
#     #     'favorite_number',
#     #     'favorite_color',
#     #     'favorite_food',
#     #     HTML("""
#     #         <p>We use notes to get better, <strong>please help us {{ username }}</strong></p>
#     #     """),
#     #     'notes'
#     # ),
#             Field('phone'),
#             Field('full_name'),
#             Submit('submit', 'Submit', css_class='button white'),
#         )
 



# # https://gemini.google.com/app/2fd85cfc4be88c05

# class CripsyForm1b(forms.ModelForm):
#     class Meta:
#         model = Crispy
#         fields = ['name', 'phone']

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.layout = Layout(
#             Field('name'),
#             # This is the custom div with id "ayo"
#             # HTML('<div id="ayo" class="my-custom-div-class">This is the extra div content!</div>'),
#              HTML('<div class="custom-divider">-- Divider Between Names --</div>'),
#              HTML('<p>More content inside the "ayo" div.</p>'),
#             Field('phone'),
#         )


# class RegistrationForm1(forms.ModelForm):
#     class Meta:
#         model = User
#         fields = ["email", "full_name" ]
    
 
# # https://django-crispy-forms.readthedocs.io/en/latest/layouts.html
# # {% load custom_tags %}


# class ExampleForm(forms.Form):

#     class Meta:
#         model = Crispy
#         fields = ['name', 'phone']
 
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.layout = Layout(
#             Field('name'),
#     #     Fieldset(
#     #     'Tell us your favorite stuff {{ username }}',
#     #     'like_website',
#     #     'favorite_number',
#     #     'favorite_color',
#     #     'favorite_food',
#     #     HTML("""
#     #         <p>We use notes to get better, <strong>please help us {{ username }}</strong></p>
#     #     """),
#     #     'notes'
#     # ),
#             Field('phone'),
#             Submit('submit', 'Submit', css_class='button white'),
#         )


# apps/demo/forms.py
from django import forms
from django.core.validators import RegexValidator
from django.utils import timezone
from .models import DemoBooking, Solution

class DemoBookingForm(forms.ModelForm):
    # Custom fields with enhanced validation
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name',
            'data-msg-required': 'Please enter your first name',
        }),
        validators=[
            RegexValidator(
                regex='^[a-zA-Z\s\-]+$',
                message='First name can only contain letters, spaces, and hyphens',
                code='invalid_first_name'
            )
        ]
    )
    
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name',
        }),
        validators=[
          RegexValidator(
    regex=r'^[a-zA-Z\s\-]+$',
    message='Last name can only contain letters, spaces, and hyphens',
    code='invalid_last_name'
)
        ]
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@company.com',
            'data-msg-required': 'Please enter a valid email address',
            'data-msg-email': 'Please enter a valid email address',
        })
    )
    
    company = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your company name',
        })
    )
    
    job_title = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., CTO, Head of Innovation, IT Director',
        })
    )
    
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1 (555) 123-4567',
        }),
        validators=[
            RegexValidator(
                regex='^[\+]?[0-9\s\-\(\)]{10,20}$',
                message='Please enter a valid phone number',
                code='invalid_phone'
            )
        ]
    )
    
    INDUSTRY_CHOICES = [
        ('', 'Select your industry'),
        ('banking', 'Banking & Financial Services'),
        ('insurance', 'Insurance'),
        ('oil_gas', 'Oil & Gas'),
        ('retail', 'Retail & E-commerce'),
        ('telecom', 'Telecommunications'),
        ('healthcare', 'Healthcare'),
        ('manufacturing', 'Manufacturing'),
        ('government', 'Government & Public Sector'),
        ('other', 'Other'),
    ]
    
    industry = forms.ChoiceField(
        choices=INDUSTRY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-msg-required': 'Please select your industry',
        })
    )
    
    # Dynamic solution choices
    interest_areas = forms.ModelMultipleChoiceField(
        queryset=Solution.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input',
        }),
        required=True,
        error_messages={
            'required': 'Please select at least one area of interest',
        }
    )
    
    preferred_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local',
            'min': timezone.now().strftime('%Y-%m-%dT%H:%M'),
        }),
        help_text="Select your preferred date and time for the demo"
    )
    
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Tell us about your specific challenges or requirements...',
        }),
        help_text="Optional: Share any specific use cases or questions"
    )
    
    # GDPR Compliance
    privacy_policy = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        error_messages={
            'required': 'You must agree to the privacy policy to continue',
        }
    )
    
    newsletter_subscription = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        label='Subscribe to our newsletter for industry insights and updates'
    )
    
    class Meta:
        model = DemoBooking
        fields = [
            'first_name', 'last_name', 'email', 'company', 'job_title', 
            'phone', 'industry', 'interest_areas', 'preferred_date', 
            'message', 'privacy_policy', 'newsletter_subscription'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Group solutions by category for better organization
        self.fields['interest_areas'].queryset = Solution.objects.filter(
            is_active=True
        ).select_related('category').order_by('category__display_order', 'display_order')
        
        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field, 'widget') and hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.Select)):
                        field.widget.attrs['class'] = 'form-control'
                    elif isinstance(field.widget, forms.Textarea):
                        field.widget.attrs['class'] = 'form-control'
    
    def clean_preferred_date(self):
        preferred_date = self.cleaned_data.get('preferred_date')
        
        if preferred_date:
            now = timezone.now()
            
            # Ensure date is not in the past
            if preferred_date < now:
                raise forms.ValidationError("Please select a future date and time for the demo.")
            
            # Ensure date is within reasonable future (6 months)
            max_future_date = now + timezone.timedelta(days=180)
            if preferred_date > max_future_date:
                raise forms.ValidationError("Please select a date within the next 6 months.")
            
            # Ensure it's a business hour (9 AM - 5 PM, Monday-Friday)
            if preferred_date.weekday() >= 5:  # Saturday (5) or Sunday (6)
                raise forms.ValidationError("Please select a weekday (Monday-Friday) for the demo.")
            
            hour = preferred_date.hour
            if hour < 9 or hour >= 17:
                raise forms.ValidationError("Please select a time between 9:00 AM and 5:00 PM.")
        
        return preferred_date
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Check for disposable email domains
        disposable_domains = [
            'tempmail.com', 'guerrillamail.com', 'mailinator.com',
            '10minutemail.com', 'throwawaymail.com', 'yopmail.com'
        ]
        
        domain = email.split('@')[-1].lower()
        if domain in disposable_domains:
            raise forms.ValidationError("Please use a professional email address from your company.")
        
        return email
    
    def clean_company(self):
        company = self.cleaned_data.get('company')
        
        # Basic company name validation
        if len(company.strip()) < 2:
            raise forms.ValidationError("Please enter a valid company name.")
        
        # Check for suspicious patterns
        suspicious_patterns = ['test', 'fake', 'demo company']
        if any(pattern in company.lower() for pattern in suspicious_patterns):
            raise forms.ValidationError("Please provide your actual company name.")
        
        return company.strip()
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Additional processing before save
        instance.first_name = self.cleaned_data['first_name'].strip().title()
        instance.last_name = self.cleaned_data['last_name'].strip().title()
        instance.company = self.cleaned_data['company'].strip()
        
        if commit:
            instance.save()
            self.save_m2m()  # Save many-to-many relationships (interest_areas)
        
        return instance


# Quick Demo Form (for partial submissions)
class QuickDemoForm(forms.ModelForm):
    """Simplified form for quick demo requests"""
    
    class Meta:
        model = DemoBooking
        fields = ['first_name', 'last_name', 'email', 'company', 'job_title']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Your {field.label.lower()}'
            })


# Calendly Integration Form
class CalendlyBookingForm(forms.Form):
    """Form for Calendly webhook integration"""
    
    calendly_event_id = forms.CharField(max_length=100)
    calendly_invitee_id = forms.CharField(max_length=100)
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    company = forms.CharField(max_length=200, required=False)
    job_title = forms.CharField(max_length=150, required=False)
    
    def process_booking(self):
        """Process Calendly booking and create/update DemoBooking"""
        calendly_data = self.cleaned_data
        
        try:
            # Find existing booking or create new one
            booking, created = DemoBooking.objects.update_or_create(
                calendly_event_id=calendly_data['calendly_event_id'],
                defaults={
                    'first_name': calendly_data['first_name'],
                    'last_name': calendly_data['last_name'],
                    'email': calendly_data['email'],
                    'company': calendly_data.get('company', ''),
                    'job_title': calendly_data.get('job_title', ''),
                    'status': 'confirmed',
                }
            )
            return booking, created
        except Exception as e:
            # Log error and handle appropriately
            raise forms.ValidationError(f"Error processing booking: {str(e)}")