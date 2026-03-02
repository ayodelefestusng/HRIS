from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from workflow.models import Workflow


class WorkflowTests(TestCase):
    def test_create_workflow(self):
        wf = Workflow.objects.create(name="Leave Approval")
        self.assertEqual(str(wf), "Leave Approval")