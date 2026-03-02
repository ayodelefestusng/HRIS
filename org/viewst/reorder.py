from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from org.services.reorder import reorder_units


class OrgUnitReorderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        reorder_units(request.data["parent"], request.data["order"])
        return Response({"status": "reordered"})