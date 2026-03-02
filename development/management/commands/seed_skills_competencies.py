import random
import logging
from django.core.management.base import BaseCommand
from django.db import transaction

from development.models import Skill, Competency, CompetencySkill, EmployeeSkillProfile
from employees.models import Employee

logger = logging.getLogger(__name__)

# --- Skills to seed ---
SKILLS = [
    "Communication", "Python", "Java", "Sales Force",
    "Figma", "Airtable", "Negotiation", "Planning"
]

# --- Competencies and their skills ---
COMPETENCIES = {
    "Analytics": {
        "description": "Core competency in data analysis",
        "skills": ["Python", "Communication", "Ms Excel", "Power BI"],
    },
    "Sales": {
        "description": "Core competency in sales and client engagement",
        "skills": ["Sales Force", "Negotiation", "Communication"],
    },
    "Project Management": {
        "description": "Core competency in planning and execution",
        "skills": ["Planning", "Negotiation", "Communication"],
    },
}


class Command(BaseCommand):
    help = "Seed Skills, Competencies, and assign random skills to employees"

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write(self.style.SUCCESS("🚀 Starting seeding process..."))

            # 1. Create Skills if they don’t exist
            for skill_name in SKILLS + [s for comp in COMPETENCIES.values() for s in comp["skills"]]:
                skill, created = Skill.objects.get_or_create(
                    name=skill_name,
                    defaults={"description": f"Core skill in {skill_name}"}
                )
                if created:
                    logger.info(f"Created skill: {skill_name}")
                else:
                    logger.info(f"Skill already exists: {skill_name}")

            # 2. Create/Update Competencies and assign skills via CompetencySkill
            for comp_name, comp_data in COMPETENCIES.items():
                comp, created = Competency.objects.get_or_create(
                    name=comp_name,
                    defaults={"description": comp_data["description"]}
                )
                if not created:
                    comp.description = comp_data["description"]
                    comp.save()
                    logger.info(f"Updated competency: {comp_name}")
                else:
                    logger.info(f"Created competency: {comp_name}")

                # Map skills to competency (enforce uniqueness via CompetencySkill)
                for skill_name in comp_data["skills"]:
                    try:
                        skill = Skill.objects.get(name=skill_name)
                        cs, created = CompetencySkill.objects.get_or_create(
                            competency=comp,
                            skill=skill
                        )
                        if created:
                            logger.info(f"Linked {skill_name} → {comp_name}")
                        else:
                            logger.info(f"Link already exists: {skill_name} → {comp_name}")
                    except Skill.DoesNotExist:
                        logger.warning(f"Skill {skill_name} not found for competency {comp_name}")

            # 3. Assign random skills and levels to employees
            employees = Employee.objects.all()
            all_skills = list(Skill.objects.all())

            for emp in employees:
                num_skills = random.randint(2, 5)
                chosen_skills = random.sample(all_skills, num_skills)

                for skill in chosen_skills:
                    profile, created = EmployeeSkillProfile.objects.get_or_create(
                        employee=emp,
                        skill=skill,
                        defaults={
                            "level": random.randint(1, 10),
                            "source": "system",
                            "comment": "Auto-assigned by seeding script",
                        }
                    )
                    if created:
                        logger.info(f"Assigned {skill.name} (lvl {profile.level}) to {emp}")
                    else:
                        logger.info(f"Skill {skill.name} already assigned to {emp}")

            self.stdout.write(self.style.SUCCESS("✅ Seeding completed successfully!"))
