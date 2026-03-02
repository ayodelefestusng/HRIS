from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from talent.models import (
    RoleProfile,
    Competency,
    Skill,
    RoleCompetencyRequirement,
    EmployeeSkillProfile,
    EmployeeRoleFit,
)
from talent.serializers import (
    RoleProfileSerializer,
    CompetencySerializer,
    SkillSerializer,
    RoleCompetencyRequirementSerializer,
    EmployeeSkillProfileSerializer,
    EmployeeRoleFitSerializer,
)
from development.services import compute_role_fit_for_employee
from rbac.permissions import make_permission_class

    
from development.services import compute_role_fit_for_candidate
from ats.models import Candidate
ManageRolesPermission = make_permission_class("manage_roles")
ManageCompetenciesPermission = make_permission_class("manage_competencies")
ManageSkillsPermission = make_permission_class("manage_skills")
ViewTalentAnalyticsPermission = make_permission_class("view_talent_analytics")


class RoleProfileViewSet(viewsets.ModelViewSet):
    queryset = RoleProfile.objects.all()
    serializer_class = RoleProfileSerializer
    permission_classes = [permissions.IsAuthenticated, ManageRolesPermission]


class CompetencyViewSet(viewsets.ModelViewSet):
    queryset = Competency.objects.all()
    serializer_class = CompetencySerializer
    permission_classes = [permissions.IsAuthenticated, ManageCompetenciesPermission]


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAuthenticated, ManageSkillsPermission]


class RoleCompetencyRequirementViewSet(viewsets.ModelViewSet):
    queryset = RoleCompetencyRequirement.objects.select_related("role", "competency")
    serializer_class = RoleCompetencyRequirementSerializer
    permission_classes = [permissions.IsAuthenticated, ManageRolesPermission]


class EmployeeSkillProfileViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSkillProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return EmployeeSkillProfile.objects.filter(employee=user.employee)


class EmployeeRoleFitView(APIView):
    """
    Returns (and recomputes) the role fit for the current user vs a given role.
    """
    permission_classes = [permissions.IsAuthenticated, ViewTalentAnalyticsPermission]

    def get(self, request, role_id):
        employee = request.user.employee
        role = RoleProfile.objects.get(pk=role_id)

        fit = compute_role_fit_for_employee(employee, role)
        data = EmployeeRoleFitSerializer(fit).data
        return Response(data, status=status.HTTP_200_OK)
    
    
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from talent.serializers import AppraisalSerializer, AppraisalSkillRatingSerializer
from rbac.permissions import make_permission_class

ManagerAppraisePermission = make_permission_class("manager_appraise")


class AppraisalViewSet(viewsets.ModelViewSet):
    serializer_class = AppraisalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        employee = getattr(user, "employee", None)
        if user.is_staff:
            return Appraisal.objects.all()
        return Appraisal.objects.filter(employee=employee)


class SubmitSelfRatingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, appraisal_id):
        appraisal = get_object_or_404(Appraisal, pk=appraisal_id)
        if appraisal.employee != request.user.employee:
            return Response({"detail": "Not your appraisal."}, status=403)

        ratings = request.data.get("ratings", [])
        for item in ratings:
            skill_id = item["skill"]
            rating = item["rating"]
            comment = item.get("comment", "")

            AppraisalSkillRating.objects.update_or_create(
                appraisal=appraisal,
                skill_id=skill_id,
                source="SELF",
                defaults={"rating": rating, "comment": comment},
            )

        appraisal.status = "SUBMITTED"
        appraisal.submitted_at = timezone.now()
        appraisal.save(update_fields=["status", "submitted_at"])

        # Optionally: notify manager here

        return Response({"detail": "Self ratings submitted."}, status=200)
    
    
class ManagerReviewAppraisalView(APIView):
    permission_classes = [permissions.IsAuthenticated, ManagerAppraisePermission]

    def post(self, request, appraisal_id):
        appraisal = get_object_or_404(Appraisal, pk=appraisal_id)
        # You can add a check: is this employee in manager's team?

        ratings = request.data.get("ratings", [])
        for item in ratings:
            skill_id = item["skill"]
            rating = item["rating"]
            comment = item.get("comment", "")

            AppraisalSkillRating.objects.update_or_create(
                appraisal=appraisal,
                skill_id=skill_id,
                source="MANAGER",
                defaults={"rating": rating, "comment": comment},
            )

        appraisal.status = "COMPLETED"
        appraisal.manager_reviewed_at = timezone.now()
        appraisal.finalized_at = timezone.now()
        appraisal.save(update_fields=["status", "manager_reviewed_at", "finalized_at"])

        # Optionally: compute overall_score here and notify employee

        return Response({"detail": "Manager review submitted."}, status=200)
    
class TeamCompetencyHeatmapView(APIView):
    """
    Returns aggregated competency levels for a given team.
    """
    permission_classes = [permissions.IsAuthenticated, ViewTalentAnalyticsPermission]

    def get(self, request):
        # For now, assume manager sees their direct team
        from employees.models import JobAssignment

        manager_emp = request.user.employee
        employee_ids = JobAssignment.objects.filter(
            manager__employee=manager_emp,
            is_active=True,
        ).values_list("employee_id", flat=True)

        # Fetch skills and competencies
        skill_profiles = EmployeeSkillProfile.objects.filter(
            employee_id__in=employee_ids
        ).select_related("employee", "skill")

        comp_map = {}  # competency_id -> {employee_id: [levels]}
        from talent.models import CompetencySkill, Competency

        skill_to_comp_ids = {}
        for cs in CompetencySkill.objects.all():
            skill_to_comp_ids.setdefault(cs.skill_id, []).append(cs.competency_id)

        for sp in skill_profiles:
            skill_id = sp.skill_id
            emp_id = sp.employee_id
            for comp_id in skill_to_comp_ids.get(skill_id, []):
                comp_map.setdefault(comp_id, {}).setdefault(emp_id, []).append(sp.level)

        # Build response structure
        competencies = Competency.objects.filter(id__in=comp_map.keys())
        result = []
        for comp in competencies:
            emp_levels = []
            for emp_id, levels in comp_map[comp.id].items():
                avg_level = sum(levels) / len(levels)
                emp_levels.append({"employee_id": emp_id, "avg_level": avg_level})
            result.append(
                {
                    "competency_id": comp.id,
                    "competency_name": comp.name,
                    "employees": emp_levels,
                }
            )

        return Response(result)
    

        
class CandidateRoleFitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, candidate_id, role_id):
        candidate = Candidate.objects.get(pk=candidate_id)
        role = RoleProfile.objects.get(pk=role_id)

        score = compute_role_fit_for_candidate(candidate, role)
        return Response({"candidate": candidate.full_name, "role": role.name, "score": score})
    
            
class EmployeeRoleFitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, role_id):
        employee = request.user.employee
        role = RoleProfile.objects.get(pk=role_id)

        fit = compute_role_fit_for_employee(employee, role)
        return Response({"role": role.name, "score": fit.score})
    
    
class OrgChartDataView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from employees.models import JobAssignment

        rows = []

        assignments = JobAssignment.objects.filter(is_active=True).select_related(
            "employee", "manager__employee"
        )

        for ja in assignments:
            employee_name = ja.employee.full_name
            manager_name = ja.manager.employee.full_name if ja.manager else ""

            rows.append({
                "name": employee_name,
                "manager": manager_name,
                "title": ja.job_title,
            })

        return Response(rows)
    
