from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

from employees.models import JobAssignment

class OrgChartDataView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        assignments = JobAssignment.objects.filter(is_active=True).select_related(
            "employee", "manager__employee", "department", "unit", "job_title"
        )

        rows = []
        for ja in assignments:
            rows.append({
                "employee_id": ja.employee.id,
                "name": ja.employee.full_name,
                "manager": ja.manager.employee.full_name if ja.manager else "",
                "manager_id": ja.manager.employee.id if ja.manager else None,
                "title": ja.job_title.name,
                "department": ja.department.name,
                "unit": ja.unit.name if ja.unit else "",
                "employment_status": ja.employment_status,
                "start_date": str(ja.start_date),
            })

        return Response(rows)  


from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def orgchart_page(request):
    api_url = "/org/orgchart/data/"
    return render(request, "org/orgchart.html", {"api_url": api_url})



class OrgChartDataView1(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Example data — replace with your real logic
        data = [
            ["Employee", "Manager"],
            ["CEO", ""],
            ["Manager A", "CEO"],
            ["Staff 1", "Manager A"],
        ]
        return Response(data)


