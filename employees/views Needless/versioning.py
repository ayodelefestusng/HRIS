from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from org.services.versioning import create_org_version
from org.models import OrgUnitVersion

class OrgVersionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        version = create_org_version()
        return Response({"version": version})


class OrgVersionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        versions = OrgUnitVersion.objects.all().values("version", "snapshot_date")
        return Response(list(versions))