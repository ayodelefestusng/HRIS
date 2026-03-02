from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Employee

User = get_user_model()


class EmployeeModelTests(TestCase):
    def test_create_employee(self):
        user = User.objects.create(username="testuser")
        emp = Employee.objects.create(
            user=user,
            employee_id="EMP001",
            first_name="Test",
            last_name="User",
            date_of_birth="1990-01-01",
            gender="M",
        )
        self.assertEqual(str(emp), "Test User (EMP001)")
