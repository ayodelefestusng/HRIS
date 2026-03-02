from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from org.services.kpis import compute_org_metrics

class OrgUnitKPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(compute_org_metrics())