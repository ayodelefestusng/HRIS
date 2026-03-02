from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from ats.models import JobPosting, Application, Candidate
from org.models import (
    Tenant,
    JobRole,
    OrgUnit,
    JobTitle,
    Location,
    Town,
    State,
    Country,
)
from employees.models import Employee, Grade
from django.utils import timezone
import datetime

User = get_user_model()


class AtsDisplayTest(TestCase):
    def setUp(self):
        # Create Tenant
        self.tenant = Tenant.objects.create(
            name="Test Tenant", code="TT", subdomain="test"
        )

        # Create User
        self.user = User.objects.create_user(
            username="testuser", password="password", tenant=self.tenant
        )

        # Create Location Structure
        self.country = Country.objects.create(name="Test Country", tenant=self.tenant)
        self.state = State.objects.create(
            name="Test State", country=self.country, tenant=self.tenant
        )
        self.town = Town.objects.create(
            name="Test Town", state=self.state, tenant=self.tenant
        )
        self.location = Location.objects.create(
            location_id="LOC001",
            name="Test Location",
            town=self.town,
            tenant=self.tenant,
        )

        # Create Job Role Structure
        self.org_unit = OrgUnit.objects.create(
            name="Test Unit", code="TU", location=self.location, tenant=self.tenant
        )
        self.job_title = JobTitle.objects.create(
            name="Software Engineer", tenant=self.tenant
        )
        self.job_role = JobRole.objects.create(
            org_unit=self.org_unit,
            job_title=self.job_title,
            role_type="MEMBER",
            tenant=self.tenant,
        )

        # Create Job Posting
        self.job_posting = JobPosting.objects.create(
            role=self.job_role,
            description="Test Description",
            requirements="Test Requirements",
            tenant=self.tenant,
            closing_date=timezone.now().date() + datetime.timedelta(days=10),
        )
        self.job_posting.locations.add(self.location)

        # Create Candidate & Application
        self.candidate = Candidate.objects.create(
            full_name="John Doe",
            email="john@example.com",
            phone="08012345678",
            tenant=self.tenant,
        )
        self.application = Application.objects.create(
            candidate=self.candidate, job_posting=self.job_posting, tenant=self.tenant
        )

        self.client = Client()
        self.client.force_login(self.user)

    def test_job_posting_title_property(self):
        """Test that the title property works correctly"""
        print(f"\nExpected Title: Software Engineer")
        print(f"Actual Title: {self.job_posting.title}")
        self.assertEqual(self.job_posting.title, "Software Engineer")

    def test_manage_candidates_template(self):
        """Test that manage_candidates.html displays title and location"""
        response = self.client.get("/ats/manage-candidates/")
        content = response.content.decode("utf-8")

        print("\nChecking manage_candidates.html content:")
        if "Software Engineer" in content:
            print(" PASS: Job Title found")
        else:
            print(" FAIL: Job Title not found")

        if "Test Location" in content:
            print(" PASS: Location found")
        else:
            print(" FAIL: Location not found")

        self.assertIn("Software Engineer", content)
        self.assertIn("Test Location", content)

    def test_candidate_application_template(self):
        """Test that candidate_application.html displays title and location"""
        url = f"/ats/application/{self.application.pk}/"
        response = self.client.get(url)
        content = response.content.decode("utf-8")

        print(f"\nChecking candidate_application.html ({url}) content:")
        if "Software Engineer" in content:
            print(" PASS: Job Title found")
        else:
            print(" FAIL: Job Title not found")

        if "Test Location" in content:
            print(" PASS: Location found")
        else:
            print(" FAIL: Location not found")

        self.assertIn("Software Engineer", content)
        self.assertIn("Test Location", content)
