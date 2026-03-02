# from decimal import Decimal
# from django.utils import timezone
# from org.models import RoleOfficerInCharge,  RoleCompetencyRequirement
# from development.models import (
#     Competency,
#     Skill,
#     CompetencySkill,
#     EmployeeSkillProfile,
#     EmployeeRoleFit,
# )
# from employees.models import Employee

# from decimal import Decimal
# from django.utils import timezone

# from development.models import (
  
#     CompetencySkill,
  
#     EmployeeSkillProfile,
#     EmployeeRoleFit,
# )
# from employees.models import Employee
# from ats.models import Candidate, CandidateSkillProfile


# def compute_role_fit_for_employee(employee: Employee, role: RoleOfficerInCharge):
#     """
#     Computes and stores the role fit of an employee.
#     """
#     result = _compute_fit_generic(
#         role=role,
#         get_skill_levels=lambda skill_ids: EmployeeSkillProfile.objects.filter(
#             employee=employee,
#             skill_id__in=skill_ids,
#         ).values_list("skill_id", "level"),
#     )

#     fit, _ = EmployeeRoleFit.objects.update_or_create(
#         employee=employee,
#         role=role,
#         defaults={
#             "score": result["final_score"],
#             "computed_at": timezone.now(),
#         },
#     )
#     return fit


# def compute_role_fit_for_candidate(candidate: Candidate, role: RoleOfficerInCharge):
#     """
#     Computes fit for a candidate without persisting to a model.
#     Returns a dict with final score and breakdown.
#     """
#     result = _compute_fit_generic(
#         role=role,
#         get_skill_levels=lambda skill_ids: CandidateSkillProfile.objects.filter(
#             candidate=candidate,
#             skill_id__in=skill_ids,
#         ).values_list("skill_id", "level"),
#     )
#     return result


# def _compute_fit_generic(role: RoleOfficerInCharge, get_skill_levels):
#     """
#     Core scoring logic used for both employees and candidates.
#     Returns:
#     {
#       "final_score": Decimal('84.50'),
#       "competencies": [
#          {
#            "id": 1,
#            "name": "Data Analysis",
#            "weight": 5,
#            "avg_level": 4.2,
#            "normalized": 0.84,
#            "weighted_contribution": 4.2
#          },
#          ...
#       ]
#     }
#     """
#     from talent.models import Competency

#     requirements = RoleCompetencyRequirement.objects.filter(role=role)

#     if not requirements.exists():
#         return {"final_score": Decimal("0.00"), "competencies": []}

#     competencies_data = []
#     total_weight = 0
#     weighted_sum = Decimal("0")

#     for req in requirements:
#         competency = req.competency
#         weight = req.weight

#         comp_skills = list(
#             CompetencySkill.objects.filter(
#                 competency=competency
#             ).values_list("skill_id", flat=True)
#         )
#         if not comp_skills:
#             continue

#         skill_levels = list(get_skill_levels(comp_skills))
#         if not skill_levels:
#             avg_level = 0
#         else:
#             levels = [lvl for _, lvl in skill_levels]
#             avg_level = sum(levels) / len(levels)

#         normalized = Decimal(avg_level) / Decimal("5") if avg_level > 0 else Decimal("0")
#         weighted = normalized * Decimal(weight)

#         competencies_data.append(
#             {
#                 "id": competency.id,
#                 "name": competency.name,
#                 "weight": weight,
#                 "avg_level": float(avg_level),
#                 "normalized": float(normalized),
#                 "weighted_contribution": float(weighted),
#             }
#         )

#         total_weight += weight
#         weighted_sum += weighted

#     if total_weight == 0:
#         final_score = Decimal("0.00")
#     else:
#         final_score = (weighted_sum / Decimal(total_weight)) * Decimal("100")
#         final_score = final_score.quantize(Decimal("0.01"))

#     return {"final_score": final_score, "competencies": competencies_data}


# def compute_role_fit_for_all_employees(role: RoleOfficerInCharge):
#     """
#     Recomputes fit score for all employees for a given role.
#     """
#     employees = Employee.objects.filter(is_active=True)
#     fits = []
#     for emp in employees:
#         fits.append(compute_role_fit_for_employee(emp, role))
#     return fits



