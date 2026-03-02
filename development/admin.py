
# development/admin.py
from django.contrib import admin
from .models import Course, TrainingSession, Enrollment, Certification, SkillMatrix
from users.admin import BaseTenantAdmin
admin.site.register(Course)
admin.site.register(TrainingSession)
admin.site.register(SkillMatrix)


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee', 'issue_date', 'expiry_date', 'status_flag')
    list_filter = ('tenant', 'issue_date')

    def status_flag(self, obj):
        if obj.is_expired:
            return "❌ Expired"
        return "✅ Active"

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'session', 'status', 'score')
    list_editable = ('status', 'score')
    actions = ['mark_as_completed']

    @admin.action(description="Mark selected as Completed (Triggers Skill Upgrade)")
    def mark_as_completed(self, request, queryset):
        for enrollment in queryset:
            enrollment.status = "COM"
            enrollment.save() # Triggering the save() logic for skill updates
        self.message_user(request, "Enrollments updated and skills upgraded.")
        

        
        
        

from .models import Competency,Skill,CompetencySkill,EmployeeRoleFit,EmployeeSkillProfile

admin.site.register(CompetencySkill)

admin.site.register(Competency)
admin.site.register(Skill)

admin.site.register(EmployeeRoleFit)
admin.site.register(EmployeeSkillProfile)




# class EmployeeSkillProfileInline(admin.TabularInline):
#     model = EmployeeSkillProfile
#     extra = 1
    
# @admin.register(Skill)
# class SkillAdmin(BaseTenantAdmin):
#     list_display = ('name', 'description')
#     inlines = [EmployeeSkillProfileInline]
#     search_fields = ('name',)
#     # readonly_fields = ('created_at', 'updated_at') 