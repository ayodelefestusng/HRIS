import logging
from django.contrib import admin
from users.admin import BaseTenantAdmin
from .models import (
    Tenant, Country, State, Town, Location, Grade,
    OrgUnit, OrgUnitVersion, OrgSnapshot,
    OrgWorkflowRoute, RoleOfficerInCharge, RoleOfficerInCharge,
    RoleCompetencyRequirement, RoleSkillRequirement,
    Department, Unit,JobRole,JobTitle,QualificationLevel,CompanyTier,CompanySize,PyramidGroup,

    LinkedInIntegration,GoogleMeetIntegration,TaggedItem
)
from workflow.services.workflow_service import merge_units

logger = logging.getLogger(__name__)
@admin.register(TaggedItem)
class TaggedItemAdmin(BaseTenantAdmin):
    list_display = ("tag", "content_type", "object_id")
    search_fields = ("tag", "content_type__model")
    list_filter = ("content_type",)
    list_select_related = ("content_type",)
@admin.register(GoogleMeetIntegration)
class GoogleMeetIntegrationAdmin(BaseTenantAdmin):
    list_display = ("tenant", "CLIENT_ID", "CLIENT_SECRET", "access_token")
    search_fields = ("tenant__name", "CLIENT_ID")
    list_filter = ("tenant",)
    list_select_related = ("tenant",)
    fieldsets = (
        ("Tenant", {
            "fields": ("tenant",)
        }),
        ("Google App Credentials", {
            "fields": ("CLIENT_ID", "CLIENT_SECRET", "REDIRECT_URI"),
            "description": "Enter the Google API credentials for this tenant."
        }),
        ("Token Info", {
            "fields": ("access_token", "refresh_token", "expires_at"),
            "description": "Tokens are managed automatically via OAuth callback."
        }),
    )

    def token_status(self, obj):
        return "Valid" if obj.is_token_valid() else "Expired"
    token_status.short_description = "Token Status"

@admin.register(LinkedInIntegration)
class LinkedInIntegrationAdmin(BaseTenantAdmin):
    list_display = ("tenant", "client_id", "client_secret", "access_token")
    search_fields = ("tenant__name", "client_id")
    list_filter = ("tenant",)
    list_select_related = ("tenant",)

    
# --- Standard Admin (Non-Tenant Specific) ---
@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "subdomain", "is_active")
    search_fields = ("name", "code")

# These are usually global lookups, but if they are tenant-specific, 
# change them to BaseTenantAdmin.
admin.site.register(Country)
admin.site.register(State)
admin.site.register(Town)

# --- Multi-Tenant Admins ---
@admin.register(Location)
class LocationAdmin(BaseTenantAdmin):
    list_display = ("name", "tenant")

admin.site.register(CompanyTier)
admin.site.register(CompanySize)
admin.site.register(PyramidGroup)

admin.site.register(Grade)
admin.site.register(JobTitle)    
@admin.register(OrgUnit)
class OrgUnitAdmin(BaseTenantAdmin):
    list_display = ("name", "code", "parent", "depth", "tenant")
    search_fields = ("name", "code")
    list_filter = ("depth", "tenant")
    list_select_related = ("parent", "tenant") # Performance optimization

    actions = ["merge_selected_units"]

    def merge_selected_units(self, request, queryset):
        if queryset.count() < 2:
            self.message_user(request, "Select at least two units to merge.")
            return

        target = queryset.first()
        sources = queryset.exclude(id=target.id)

        # Ensure tenant isolation during merge
        for src in sources:
            if src.tenant == target.tenant:
                merge_units(src.id, target.id)
                logger.info(f"Merged Unit {src.id} into {target.id} for Tenant {target.tenant}")
            else:
                logger.error(f"Security Alert: Attempt to merge units across tenants by {request.user}")

        self.message_user(request, f"Merged {sources.count()} units into {target.name}.")


# class QualificationLevelInline(admin.TabularInline):
#     model = QualificationLevel
#     extra = 2
admin.site.register(QualificationLevel)    

@admin.register(JobRole)
class OrgUnitRoleAdmin(BaseTenantAdmin):
    list_display = ( "org_unit",'job_title','role_type', "tenant","vacant")
    search_fields = ('org_unit__name', 'job_title__name', 'role_type','vacant')
    list_filter = ('org_unit__name', 'job_title__name', 'role_type','vacant')
    list_select_related = ('org_unit', 'job_title')
    # inlines = [QualificationLevelInline]

# Register remaining models with Tenant Protection
@admin.register(Department, Unit, OrgWorkflowRoute, RoleOfficerInCharge, 
                RoleCompetencyRequirement, RoleSkillRequirement, 
                OrgUnitVersion, OrgSnapshot)
class GeneralOrgAdmin(BaseTenantAdmin):
    pass