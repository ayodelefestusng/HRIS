from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from org.services.snapshots import generate_snapshot
from org.models import OrgSnapshot


class OrgSnapshotCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        snap = generate_snapshot()
        return Response({"snapshot_id": snap.id})


class OrgSnapshotListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        snaps = OrgSnapshot.objects.all().values("id", "captured_at")
        return Response(list(snaps))