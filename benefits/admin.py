from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import  GradeHealthInsurance,Reimbursement

# admin.site.register(Grade)

admin.site.register(GradeHealthInsurance)
admin.site.register(Reimbursement)

