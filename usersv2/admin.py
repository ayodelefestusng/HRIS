import logging
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
logger = logging.getLogger(__name__)

class BaseTenantAdmin(admin.ModelAdmin):
    """
    Abstract Admin class that:
    1. Filters list views to only show records belonging to the user's tenant.
    2. Automatically assigns the tenant to new records on save.
    """
    
    # Exclude tenant from the form so users can't manually change it
    # exclude = ('tenant',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Superusers can see everything; others see only their tenant's data
        if request.user.is_superuser:
            return qs
        return qs.filter(tenant=request.user.tenant)

    def save_model(self, request, obj, form, change):
        # Automatically assign the logged-in user's tenant if not already set
        if not obj.tenant_id and not request.user.is_superuser:
            obj.tenant = request.user.tenant
            
        # Logging with context (Tenant and User IDs are handled by our filter)
        action = "Updated" if change else "Created"
        logger.info(f"{action} {obj._meta.model_name}: {obj}")
        
        super().save_model(request, obj, form, change)


from org.models import Tenant

# 1. Create a custom Creation Form to include Tenant
class CustomUserCreationForm(UserCreationForm):
    tenant = forms.ModelChoiceField(
        queryset=Tenant.objects.filter(is_active=True).order_by("name"),
        empty_label="Select a tenant"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'full_name', 'tenant', 'password1', 'password2')

        # fields = ('email', 'full_name', 'tenant')

  
  
        
# users/forms.py (or inside admin.py)
class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        # Ensure 'tenant' is explicitly in this list
        fields = ('email', 'full_name', 'phone', 'tenant', 'is_active', 'is_staff', 'is_superuser')

@admin.register(User)
class UserAdmin(BaseUserAdmin, BaseTenantAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    
    
    # REMOVE exclude here so tenant is allowed in fieldsets
    exclude = None

    # CRITICAL: We must override these to prevent Django from looking for 'username'
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions')
    search_fields = ('email', 'full_name')
    list_display = ('email', 'full_name', 'tenant', 'is_staff', 'is_active')

    # Redefining fieldsets to ensure 'tenant' is captured
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone', 'tenant')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('MFA', {'fields': ('mfa_enabled', 'mfa_secret')}),
        ('Important dates', {'fields': ('last_login',)}),
    )

    # Redefining add_fieldsets for the creation process
    add_fieldsets = (
    (None, {
        'classes': ('wide',),
        'fields': ('email', 'full_name', 'tenant', 'password1', 'password2'),
    }),
    
)   
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Restrict tenant dropdown:
        - Superusers see all tenants
        - Regular users only see their own tenant
        """
        if db_field.name == "tenant":
            if request.user.is_superuser:
                kwargs["queryset"] = Tenant.objects.filter(is_active=True).order_by("name")
            else:
                kwargs["queryset"] = Tenant.objects.filter(pk=request.user.tenant_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


    # def get_form(self, request, obj=None, **kwargs):
    #     """
    #     Special override: BaseUserAdmin sometimes strips fields it doesn't 
    #     recognize. This ensures the form stays intact.
    #     """
    #     return super(BaseUserAdmin, self).get_form(request, obj, **kwargs)
    
    
    
    

