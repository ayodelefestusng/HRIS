from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from org.services.dashboard import get_headcount_and_budget_dashboard
from payroll.models import PayrollPeriod

class HeadcountBudgetDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period_id = request.query_params.get("period_id")
        period = None

        if period_id:
            try:
                period = PayrollPeriod.objects.get(id=period_id)
            except PayrollPeriod.DoesNotExist:
                return Response({"detail": "Invalid period_id"}, status=400)

        data = get_headcount_and_budget_dashboard(period=period)
        return Response(data)
    
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from org.services.dashboard import get_headcount_and_budget_dashboard
from payroll.models import PayrollPeriod

class HeadcountBudgetDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period_id = request.query_params.get("period_id")
        period = None

        if period_id:
            try:
                period = PayrollPeriod.objects.get(id=period_id)
            except PayrollPeriod.DoesNotExist:
                return Response({"detail": "Invalid period_id"}, status=400)

        data = get_headcount_and_budget_dashboard(period=period)
        return Response(data)