from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from ats.models import JobPosting,OnboardingTemplate
        


class ATSTests(TestCase):
    def test_create_job_posting(self):
        jp = JobPosting.objects.create(
            title="Software Engineer",
            department="Engineering",
            description="Build things",
            requirements="Python, Django",
            location="Remote",
        )
        self.assertEqual(str(jp), "Software Engineer")
        



class OnboardingTests(TestCase):
    def test_create_template(self):
        t = OnboardingTemplate.objects.create(name="New Hire Template")
        self.assertEqual(str(t), "New Hire Template")