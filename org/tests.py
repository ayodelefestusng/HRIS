from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from org.models import OrgUnit


class OrgUnitTests(TestCase):
    def test_create_org_unit(self):
        unit = OrgUnit.objects.create(name="Engineering", code="ENG")
        self.assertEqual(unit.depth, 0)