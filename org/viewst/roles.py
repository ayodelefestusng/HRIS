from rest_framework import viewsets
from org.models import JobRole, RoleOfficerInCharge, RoleCompetencyRequirement, RoleSkillRequirement
from org.serializers import (
    OrgUnitRoleSerializer,
    RoleOfficerInChargeSerializer,
    RoleCompetencyRequirementSerializer,
    RoleSkillRequirementSerializer,
)


from rest_framework import viewsets, filters
from org.models import OrgUnit
from org.serializers import OrgUnitSerializer

class OrgUnitViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing organizational units.
    - Includes location details.
    - Supports filtering by ?location=<id>.
    """
    queryset = OrgUnit.objects.select_related(
        "department", "location", "location__town", "location__town__state", "location__town__state__country"
    ).all()
    serializer_class = OrgUnitSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code", "location__name", "department__name"]
    ordering_fields = ["name", "code", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        location_id = self.request.query_params.get("location")
        if location_id:
            queryset = queryset.filter(location_id=location_id)
        return queryset
    
 
from rest_framework import viewsets, filters

from org.serializers import OrgUnitFlatSerializer

class OrgUnitFlatViewSet(viewsets.ModelViewSet):
    """
    API endpoint for OrgUnits (flat representation).
    - No recursive children.
    - Includes location details.
    - Supports filtering by ?location=<id>.
    """
    queryset = OrgUnit.objects.select_related(
        "department", "location", "location__town", "location__town__state", "location__town__state__country"
    ).all()
    serializer_class = OrgUnitFlatSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code", "location__name", "department__name"]
    ordering_fields = ["name", "code", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        location_id = self.request.query_params.get("location")
        if location_id:
            queryset = queryset.filter(location_id=location_id)
        return queryset
 
from rest_framework.views import APIView
from rest_framework.response import Response
from org.models import OrgUnit


class OrgUnitTreeView(APIView):
    """
    API endpoint that returns the full OrgUnit hierarchy as a tree.
    Uses the recursive OrgUnitSerializer to include children.
    """
    def get(self, request, *args, **kwargs):
        # Only top-level units (no parent) are roots of the tree
        roots = OrgUnit.objects.filter(parent__isnull=True).order_by("sort_order")
        serializer = OrgUnitSerializer(roots, many=True)
        return Response(serializer.data)
    
class OrgUnitRoleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing OrgUnit roles (Head, Deputy, Member).
    """
    queryset = JobRole.objects.select_related("org_unit", "employee").all()
    serializer_class = OrgUnitRoleSerializer


class RoleProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing role profiles.
    """
    queryset = RoleOfficerInCharge.objects.select_related("org_unit", "officer_in_charge").all()
    serializer_class = RoleOfficerInChargeSerializer


class RoleCompetencyRequirementViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing competency requirements for roles.
    """
    queryset = RoleCompetencyRequirement.objects.select_related("role", "competency").all()
    serializer_class = RoleCompetencyRequirementSerializer


class RoleSkillRequirementViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing skill requirements for roles.
    """
    queryset = RoleSkillRequirement.objects.select_related("role").all()
    serializer_class = RoleSkillRequirementSerializer