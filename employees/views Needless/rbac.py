from rest_framework import viewsets, permissions
from org.models import OrgUnitPermission
from org.serializers import OrgUnitPermissionSerializer

class OrgUnitPermissionViewSet(viewsets.ModelViewSet):
    queryset = OrgUnitPermission.objects.all()
    serializer_class = OrgUnitPermissionSerializer
    permission_classes = [permissions.IsAuthenticated]