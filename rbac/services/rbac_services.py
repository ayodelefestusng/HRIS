from django.core.cache import cache
from rbac.models import Role, EmployeeRole


# ----------------------------------------------------------------------
# ASSIGN ROLE
# ----------------------------------------------------------------------
def assign_role_to_employee(employee, role_name):
    """
    Assigns a role to an employee.
    """
    try:
        role = Role.objects.get(name=role_name)
    except Role.DoesNotExist:
        raise ValueError(f"Role '{role_name}' does not exist.")

    EmployeeRole.objects.get_or_create(employee=employee, role=role)

    # Invalidate permission cache
    cache.delete_pattern(f"perm:{employee.id}:*")

    return role


# ----------------------------------------------------------------------
# REMOVE ROLE
# ----------------------------------------------------------------------
def remove_role_from_employee(employee, role_name):
    """
    Removes a role from an employee.
    """
    try:
        role = Role.objects.get(name=role_name)
    except Role.DoesNotExist:
        raise ValueError(f"Role '{role_name}' does not exist.")

    EmployeeRole.objects.filter(employee=employee, role=role).delete()

    # Invalidate permission cache
    cache.delete_pattern(f"perm:{employee.id}:*")

    return role


# ----------------------------------------------------------------------
# CHECK PERMISSION
# ----------------------------------------------------------------------
def employee_has_permission(employee, permission_code):
    """
    Returns True if the employee has the given permission.
    Uses caching for performance.
    """
    cache_key = f"perm:{employee.id}:{permission_code}"
    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    has_perm = EmployeeRole.objects.filter(
        employee=employee,
        role__permissions__code=permission_code
    ).exists()

    cache.set(cache_key, has_perm, 300)  # cache for 5 minutes
    return has_perm