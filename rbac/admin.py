from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Role, Permission, RolePermission, EmployeeRole


admin.site.register(Role)
admin.site.register(Permission)
admin.site.register(RolePermission)
admin.site.register(EmployeeRole)