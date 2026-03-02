from rest_framework.permissions import BasePermission


class IsSelfOrHR(BasePermission):
    """
    Employee can see their own record; HR (or staff) can see everyone.
    You can replace `is_staff` with your RBAC logic later.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        return getattr(user, "employee", None) == obj