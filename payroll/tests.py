from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from payroll.models import PayrollPeriod


class PayrollTests(TestCase):
    def test_create_period(self):
        p = PayrollPeriod.objects.create(
            name="January 2025",
            start_date="2025-01-01",
            end_date="2025-01-31",
        )
        self.assertEqual(str(p), "January 2025")