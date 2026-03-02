from django.db import models
from employees.models import Employee
from org.models import TenantModel

class Permission(TenantModel):
    """
    A granular permission such as:
    - view_employee
    - edit_employee
    - approve_leave
    - run_payroll
    """
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.code


class Role(TenantModel):
    """
    A role such as:
    - EMPLOYEE
    - MANAGER
    - HR
    - ADMIN
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    # Many-to-many through RolePermission for explicit control
    permissions = models.ManyToManyField(
        Permission,
        through="RolePermission",
        related_name="roles",
    )

    def __str__(self):
        return self.name


class RolePermission(TenantModel):
    """
    Mapping table linking roles to permissions.
    """
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="permission_roles")

    class Meta:
        unique_together = ("role", "permission")

    def __str__(self):
        return f"{self.role.name} → {self.permission.code}"


class EmployeeRole(TenantModel):
    """
    Assigns a role to an employee.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employee_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_employees")

    class Meta:
        unique_together = ("employee", "role")

    def __str__(self):
        return f"{self.employee} → {self.role.name}"