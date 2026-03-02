from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from org.services.merge_split import merge_units, split_unit

class OrgUnitMergeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        merge_units(request.data["source"], request.data["target"])
        return Response({"status": "merged"})


class OrgUnitSplitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        new_ids = split_unit(request.data["unit"], request.data["splits"])
        return Response({"created_units": new_ids})