from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Warning,Suspension,Investigation


admin.site.register(Warning)
admin.site.register(Suspension)
admin.site.register(Investigation)