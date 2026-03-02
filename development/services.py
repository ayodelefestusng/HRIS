from decimal import Decimal
from django.utils import timezone
from development.models import (
    SkillMatrix,
    Enrollment,
    GradeRequirement,
    Competency,
    Skill,
    CompetencySkill,
    EmployeeSkillProfile,
    EmployeeRoleFit,
)
from org.models import Grade, RoleCompetencyRequirement, JobRole
from employees.models import Employee
from ats.models import Candidate, CandidateSkillProfile
import logging

logger = logging.getLogger(__name__)


class SkillAnalyticsService:
    def __init__(self, tenant):
        self.tenant = tenant

    def identify_skill_gaps(self, employee):
        """
        Compares an employee's current skill levels against
        the 'Required Skills' for their current Grade.
        """
        try:
            # Note: This assumes Grade model has a 'required_skills' ManyToManyField
            required_skills = employee.grade.required_skills.all()
            current_skills = SkillMatrix.objects.filter(
                employee=employee, tenant=self.tenant
            )

            gap_report = []
            for req in required_skills:
                current = current_skills.filter(skill=req).first()
                current_level = current.level if current else 0

                # If current level is lower than the grade requirement (e.g., Level 3)
                if current_level < 3:
                    gap_report.append(
                        {
                            "skill": req.name,
                            "current": current_level,
                            "target": 3,
                            "gap": 3 - current_level,
                        }
                    )

            return gap_report
        except Exception as e:
            logger.error(
                f"Error identifying skill gaps for {employee}: {e}", exc_info=True
            )
            return []


class CareerPathService:
    def __init__(self, tenant):
        self.tenant = tenant

    def evaluate_readiness(self, employee, target_grade=None):
        """
        Calculates a 'Readiness Score' based on Skills and Course Completions.
        """
        try:
            target = target_grade or employee.grade
            requirements = GradeRequirement.objects.filter(
                grade=target, tenant=self.tenant
            )

            if not requirements.exists():
                return {"score": 100, "status": "No Requirements Defined"}

            total_criteria = 0
            met_criteria = 0
            gaps = []

            for req in requirements:
                # 1. Check Skill Level
                total_criteria += 1
                user_skill = SkillMatrix.objects.filter(
                    employee=employee, skill=req.skill, tenant=self.tenant
                ).first()

                current_level = user_skill.level if user_skill else 0
                if current_level >= req.minimum_level:
                    met_criteria += 1
                else:
                    gaps.append(
                        f"Skill Gap: {req.skill.name} (Current: {current_level}, Required: {req.minimum_level})"
                    )

                # 2. Check Mandatory Courses
                for course in req.mandatory_courses.all():
                    total_criteria += 1
                    completed = Enrollment.objects.filter(
                        employee=employee,
                        session__course=course,
                        status="COM",
                        tenant=self.tenant,
                    ).exists()

                    if completed:
                        met_criteria += 1
                    else:
                        gaps.append(f"Missing Course: {course.title}")

            readiness_score = (
                (met_criteria / total_criteria) * 100 if total_criteria > 0 else 0
            )

            return {
                "target_grade": target.name,
                "readiness_score": round(readiness_score, 2),
                "is_ready": readiness_score == 100,
                "gaps": gaps,
            }
        except Exception as e:
            logger.error(
                f"Error evaluating readiness for {employee}: {e}", exc_info=True
            )
            return {"score": 0, "status": "Error", "gaps": [str(e)]}


def compute_role_fit_for_employee(employee: Employee, role: JobRole):
    """
    Computes and stores the role fit of an employee.
    """
    try:
        result = _compute_fit_generic(
            role=role,
            get_skill_levels=lambda skill_ids: EmployeeSkillProfile.objects.filter(
                employee=employee,
                skill_id__in=skill_ids,
            ).values_list("skill_id", "level"),
        )

        fit, _ = EmployeeRoleFit.objects.update_or_create(
            employee=employee,
            role=role,
            defaults={
                "score": result["final_score"],
                "computed_at": timezone.now(),
            },
        )
        return fit
    except Exception as e:
        logger.error(
            f"Error computing role fit for employee {employee}: {e}", exc_info=True
        )
        return None


def compute_role_fit_for_candidate(candidate: Candidate, role: JobRole):
    """
    Computes fit for a candidate without persisting to a model.
    Returns a dict with final score and breakdown.
    """
    try:
        result = _compute_fit_generic(
            role=role,
            get_skill_levels=lambda skill_ids: CandidateSkillProfile.objects.filter(
                candidate=candidate,
                skill_id__in=skill_ids,
            ).values_list("skill_id", "level"),
        )
        return result
    except Exception as e:
        logger.error(
            f"Error computing role fit for candidate {candidate}: {e}", exc_info=True
        )
        return {"final_score": Decimal("0.00"), "competencies": []}


def _compute_fit_generic(role: JobRole, get_skill_levels):
    """
    Core scoring logic used for both employees and candidates.
    """
    requirements = RoleCompetencyRequirement.objects.filter(role=role)

    if not requirements.exists():
        return {"final_score": Decimal("0.00"), "competencies": []}

    competencies_data = []
    total_weight = 0
    weighted_sum = Decimal("0")

    for req in requirements:
        competency = req.competency
        weight = req.weight

        comp_skills = list(
            CompetencySkill.objects.filter(competency=competency).values_list(
                "skill_id", flat=True
            )
        )
        if not comp_skills:
            continue

        skill_levels = list(get_skill_levels(comp_skills))
        if not skill_levels:
            avg_level = 0
        else:
            levels = [lvl for _, lvl in skill_levels]
            avg_level = sum(levels) / len(levels)

        normalized = (
            Decimal(avg_level) / Decimal("5") if avg_level > 0 else Decimal("0")
        )
        weighted = normalized * Decimal(weight)

        competencies_data.append(
            {
                "id": competency.id,
                "name": competency.name,
                "weight": weight,
                "avg_level": float(avg_level),
                "normalized": float(normalized),
                "weighted_contribution": float(weighted),
            }
        )

        total_weight += weight
        weighted_sum += weighted

    if total_weight == 0:
        final_score = Decimal("0.00")
    else:
        final_score = (weighted_sum / Decimal(total_weight)) * Decimal("100")
        final_score = final_score.quantize(Decimal("0.01"))

    return {"final_score": final_score, "competencies": competencies_data}


def compute_role_fit_for_all_employees(role: JobRole):
    """
    Recomputes fit score for all employees for a given role.
    """
    employees = Employee.objects.filter(is_active=True)
    fits = []
    for emp in employees:
        fits.append(compute_role_fit_for_employee(emp, role))
    return fits


def finalize_enrollment(enrollment_id):
    try:
        enrollment = Enrollment.objects.get(id=enrollment_id)
        enrollment.status = "COM"
        enrollment.save()  # This triggers enrollment.update_employee_skills() internally

        logger.info(
            f"[TRAINING_COMPLETE] Employee: {enrollment.employee.id} | "
            f"Course: {enrollment.session.course.title} | "
            f"Tenant: {enrollment.tenant.id} | "
            f"Skills Boosted: {[s.name for s in enrollment.session.course.skills_taught.all()]}"
        )
    except Exception as e:
        logger.error(f"Error finalizing enrollment {enrollment_id}: {e}", exc_info=True)
