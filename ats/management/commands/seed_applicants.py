import random
from faker import Faker
from django.core.management.base import BaseCommand
from org.models import Tenant, Location,Town
from ats.models import Candidate, Application, JobPosting

fake = Faker()

class Command(BaseCommand):
    help = "Seed 45 applicants with balanced distribution across 4 job postings, each with locations and candidate preferred location"

    def handle(self, *args, **options):
        tenant = Tenant.objects.get(code="3LN")
        
        

        job_postings_data = [
            {
                "title": "Software Engineer",
                "description": "Develop and maintain software solutions.",
                "requirements": "Python, Django, SQL",
                "locations": ["Lagos", "Abuja"],
            },
            {
                "title": "Data Analyst",
                "description": "Analyze datasets and generate insights.",
                "requirements": "SQL, Excel, BI tools",
                "locations": ["Ibadan"],
            },
            {
                "title": "Product Manager",
                "description": "Oversee product lifecycle and strategy.",
                "requirements": "Leadership, Communication, Agile",
                "locations": ["Port Harcourt"],
            },
            {
                "title": "HR Specialist",
                "description": "Manage recruitment and employee relations.",
                "requirements": "HR policies, Communication, Organization",
                "locations": ["Abuja"],
            },
        ]

        job_postings = []
        for jp in job_postings_data:
            job, _ = JobPosting.objects.get_or_create(
                tenant=tenant,
                title=jp["title"],
                defaults={
                    "description": jp["description"],
                    "requirements": jp["requirements"],
                    "status": "OPEN",
                },
            )
            for loc_name in jp["locations"]:
                # town = Town.objects.order_by("?").first()  # or Town.objects.get(pk=random.randint(1, 10))
                town = Town.objects.get(pk=random.randint(1, 10))  # pick any valid town

                loc, _ = Location.objects.get_or_create(
                    tenant=tenant,
                    name=loc_name,
                    defaults={
        "location_id": f"LOC_{loc_name.upper()}",
        "address": f"{loc_name} Office",
        "town": Town.objects.get(pk=random.randint(1, 10)),
    },

                )
                job.locations.add(loc)
            job_postings.append(job)

        counts = [11, 11, 11, 12]
        created_count = 0
        candidate_index = 0

        for job_idx, job in enumerate(job_postings):
            job_locations = list(job.locations.all())
            for _ in range(counts[job_idx]):
                full_name = fake.name()
                email = f"user{candidate_index}@example.com"
                phone = fake.phone_number()

                preferred_location = random.choice(job_locations)

                candidate, created = Candidate.objects.get_or_create(
                    tenant=tenant,
                    email=email,
                    defaults={
                        "full_name": full_name,
                        "phone": phone,
                        "preferred_location": preferred_location,  # 👈 stored properly
                    },
                )

                if created:
                    created_count += 1

                Application.objects.get_or_create(
                    tenant=tenant,
                    candidate=candidate,
                    job_posting=job,
                    defaults={
                        "status": random.choice(
                            ["APPLIED", "INTERVIEW", "OFFER", "HIRED", "REJECTED"]
                        ),
                    },
                )

                candidate_index += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_count} new candidates with balanced distribution across 4 job postings and preferred locations"
            )
        )