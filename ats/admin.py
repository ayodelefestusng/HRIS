from django.contrib import admin
from .models import JobPosting, Candidate, Application, Interview, Offer, InterviewFeedback
from users.admin import BaseTenantAdmin # Inherited Multi-tenant logic
    
from django.contrib import admin
from django.utils.html import format_html
from users.admin import BaseTenantAdmin
from .models import OnboardingTemplate, OnboardingTaskTemplate, OnboardingPlan, OnboardingTask,RecruiterTag,CandidateSkillProfile


# admin.site.register(RecruiterTag)
# admin.site.register(Candidate)

@admin.register(RecruiterTag)
class RecruiterTagAdmin(BaseTenantAdmin):
    list_display = ('name', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('name',)
    # readonly_fields = ('created_at',)
 
@admin.register(Candidate)
class CandidateAdmin(BaseTenantAdmin):  
    list_display = ('full_name', 'email', 'phone', 'created_at')
    list_filter = ( 'created_at',)
    search_fields = ('full_name', 'email', 'phone')
    # readonly_fields = ('created_at',)

class InterviewFeedbackInline(admin.TabularInline):
    model = InterviewFeedback
    extra = 1

@admin.register(JobPosting)
class JobPostingAdmin(BaseTenantAdmin):
    list_display = ('role', 'status', 'closing_date')
    list_filter = ('status', 'employment_type')
    search_fields = ('role', 'description')

@admin.register(Application)
class ApplicationAdmin(BaseTenantAdmin):
    list_display = ('candidate', 'job_posting', 'status', 'submitted_at')
    list_filter = ('status', 'job_posting__role')
    list_select_related = ('candidate', 'job_posting', 'tenant')
    readonly_fields = ('application_id',)

@admin.register(Interview)
class InterviewAdmin(BaseTenantAdmin):
    list_display = ('application', 'scheduled_at')
    inlines = [InterviewFeedbackInline]
    search_fields = ('application__candidate__full_name', 'application__job_posting__role__job_title')
    # readonly_fields = ('created_at', 'updated_at')  

@admin.register(Offer)
class OfferAdmin(BaseTenantAdmin):
    list_display = ('application', 'salary', 'status', 'start_date')
    list_filter = ('status',)
    search_fields = ('application__candidate__full_name', 'application__job_posting__role__job_title')
    # readonly_fields = ('created_at', 'updated_at')  

@admin.register(CandidateSkillProfile)
class CandidateSkillProfileAdmin(BaseTenantAdmin):
    list_display = ('candidate', 'skill', 'level')
    list_filter = ('skill', 'level')
    search_fields = ('candidate__full_name', 'skill__name')
    # readonly_fields = ('created_at', 'updated_at')
    
    

class TaskTemplateInline(admin.TabularInline):
    model = OnboardingTaskTemplate
    extra = 1

@admin.register(OnboardingTemplate)
class OnboardingTemplateAdmin(BaseTenantAdmin):
    list_display = ("name", "tenant")
    inlines = [TaskTemplateInline]
    search_fields = ('name',)
    # readonly_fields = ('created_at', 'updated_at')  
    

class OnboardingTaskInline(admin.StackedInline):
    model = OnboardingTask
    extra = 0
    # readonly_fields = ('completed_at',)

@admin.register(OnboardingPlan)
class OnboardingPlanAdmin(BaseTenantAdmin):
    list_display = ("candidate_name", "start_date", "status", "colored_progress")
    list_filter = ("status", "tenant")
    inlines = [OnboardingTaskInline]
    search_fields = ('application__candidate__full_name', 'application__job_posting__role__job_title')
    # readonly_fields = ('created_at', 'updated_at')      
    def candidate_name(self, obj):
        return obj.application.candidate.full_name

    def colored_progress(self, obj):
        # A visual progress bar in the admin list
        color = "#28a745" if obj.progress == 100 else "#ffc107"
        return format_html(
            '<div style="width:100px; background:#eee;"><div style="width:{}px; background:{}; height:10px;"></div></div> {}%',
            obj.progress, color, obj.progress
        )
    colored_progress.short_description = "Onboarding Progress"

@admin.register(OnboardingTask)
class OnboardingTaskAdmin(BaseTenantAdmin):
    list_display = ("title", "plan", "due_date", "is_completed")
    list_filter = ("is_completed", "tenant")