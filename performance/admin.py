from django.contrib import admin
from .models import AppraisalRating,AppraisalSkillRating
# Register your models here.
class AppraisalRatingInline(admin.TabularInline):
    model = AppraisalRating
    extra = 0
    fields = ('indicator', 'self_score', 'manager_score', 'manager_comment')
    readonly_fields = ('self_score', 'self_comment') # Manager shouldn't edit employee's comments
    
    
admin.site.register(AppraisalSkillRating)