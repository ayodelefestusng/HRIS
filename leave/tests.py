from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from django.contrib.auth import get_user_model
from employees.models import Employee
from leave.models import LeaveType, LeaveRequest

User = get_user_model()


class LeaveTests(TestCase):
    def test_create_leave_request(self):
        user = User.objects.create(username="testuser")
        emp = Employee.objects.create(
            user=user,
            employee_id="EMP001",
            first_name="Test",
            last_name="User",
            date_of_birth="1990-01-01",
            gender="M",
        )
        lt = LeaveType.objects.create(name="Annual Leave", annual_allocation_days=20)

        lr = LeaveRequest.objects.create(
            employee=emp,
            leave_type=lt,
            start_date="2025-01-01",
            end_date="2025-01-05",
        )

        self.assertEqual(lr.duration_days, 5)