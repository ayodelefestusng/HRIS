from rest_framework.permissions import BasePermission
from rbac.services.rbac_services import employee_has_permission


class HasPermission(BasePermission):
    """
    Base permission class for RBAC.
    Subclasses must define `required_permission`.
    """
    required_permission = None

    def has_permission(self, request, view):
        # If no permission code is set, allow by default
        if not self.required_permission:
            return True

        # Ensure user has an HR profile
        employee = getattr(request.user, "hr_profile", None)
        if not employee:
            return False

        # Check RBAC service
        return employee_has_permission(employee, self.required_permission)


def make_permission_class(permission_code):
    """
    Factory to create concrete permission classes easily.

    Example:
        ApproveLeavePermission = make_permission_class("approve_leave")
    """

    class _Permission(HasPermission):
        required_permission = permission_code

    _Permission.__name__ = f"HasPermission_{permission_code}"
    return _Permission