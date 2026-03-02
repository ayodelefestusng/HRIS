from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from onboarding.models import OnboardingTemplate


class OnboardingTests(TestCase):
    def test_create_template(self):
        t = OnboardingTemplate.objects.create(name="New Hire Template")
        self.assertEqual(str(t), "New Hire Template")