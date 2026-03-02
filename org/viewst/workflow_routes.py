from rest_framework import viewsets, permissions
from org.models import OrgWorkflowRoute
from org.serializers import OrgWorkflowRouteSerializer


class OrgWorkflowRouteViewSet(viewsets.ModelViewSet):
    queryset = OrgWorkflowRoute.objects.all()
    serializer_class = OrgWorkflowRouteSerializer
    permission_classes = [permissions.IsAuthenticated]