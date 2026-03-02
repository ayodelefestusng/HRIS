from django.core.management.base import BaseCommand
from talent.models import Competency, Skill, CompetencySkill
from org.models import Tenant

class Command(BaseCommand):
    help = "Seed 6 competencies and 15 skills with links"

    def handle(self, *args, **options):
        try:
            tenant = Tenant.objects.get(code="3LN")  # 👈 adjust tenant code
        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR("Tenant not found"))
            return

        competencies = [
            {"name": "Data Analysis", "description": "Ability to interpret and analyze data"},
            {"name": "Leadership", "description": "Guiding teams and organizations"},
            {"name": "Communication", "description": "Effective verbal and written communication"},
            {"name": "Technical Expertise", "description": "Specialized technical knowledge"},
            {"name": "Problem Solving", "description": "Identifying and resolving issues"},
            {"name": "Innovation", "description": "Creating new ideas and solutions"},
        ]

        skills = [
            {"name": "Python", "description": "Programming in Python"},
            {"name": "SQL", "description": "Database querying"},
            {"name": "Excel", "description": "Spreadsheet analysis"},
            {"name": "Public Speaking", "description": "Delivering presentations"},
            {"name": "Writing", "description": "Clear written communication"},
            {"name": "Team Management", "description": "Managing people"},
            {"name": "Conflict Resolution", "description": "Handling disputes"},
            {"name": "Networking", "description": "Building professional relationships"},
            {"name": "Cloud Computing", "description": "AWS, Azure, GCP"},
            {"name": "Cybersecurity", "description": "Protecting systems"},
            {"name": "Critical Thinking", "description": "Logical reasoning"},
            {"name": "Creativity", "description": "Generating new ideas"},
            {"name": "Design Thinking", "description": "Human-centered design"},
            {"name": "Machine Learning", "description": "Building predictive models"},
            {"name": "Project Management", "description": "Planning and executing projects"},
        ]

        competency_objs = []
        for comp in competencies:
            obj, _ = Competency.objects.get_or_create(
                tenant=tenant,
                name=comp["name"],
                defaults={"description": comp["description"]},
            )
            competency_objs.append(obj)

        skill_objs = []
        for skl in skills:
            obj, _ = Skill.objects.get_or_create(
                tenant=tenant,
                name=skl["name"],
                defaults={"description": skl["description"]},
            )
            skill_objs.append(obj)

        # Link skills to competencies (simple distribution)
        links = {
            "Data Analysis": ["Python", "SQL", "Excel"],
            "Leadership": ["Team Management", "Conflict Resolution", "Project Management"],
            "Communication": ["Public Speaking", "Writing", "Networking"],
            "Technical Expertise": ["Cloud Computing", "Cybersecurity", "Machine Learning"],
            "Problem Solving": ["Critical Thinking", "Design Thinking"],
            "Innovation": ["Creativity"],
        }

        for comp_name, skill_names in links.items():
            comp = Competency.objects.get(name=comp_name, tenant=tenant)
            for skill_name in skill_names:
                skill = Skill.objects.get(name=skill_name, tenant=tenant)
                CompetencySkill.objects.get_or_create(
                    tenant=tenant,
                    competency=comp,
                    skill=skill,
                )

        self.stdout.write(self.style.SUCCESS("Seeded 6 competencies and 15 skills"))