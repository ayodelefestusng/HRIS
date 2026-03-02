from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from rbac.models import Role


class RBACTests(TestCase):
    def test_create_role(self):
        r = Role.objects.create(name="HR")
        self.assertEqual(str(r), "HR")