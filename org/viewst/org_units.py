from rest_framework import viewsets, permissions
from org.models import OrgUnit
from org.serializers import OrgUnitSerializer
from rbac.permissions import make_permission_class

ViewOrgPermission = make_permission_class("view_org")
ManageOrgPermission = make_permission_class("manage_org")

class OrgUnitViewSet(viewsets.ModelViewSet):
    queryset = OrgUnit.objects.all().order_by("path")
    serializer_class = OrgUnitSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), ViewOrgPermission()]
        return [permissions.IsAuthenticated(), ManageOrgPermission()]