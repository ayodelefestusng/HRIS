from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from analytics.models import MetricSnapshot


class AnalyticsTests(TestCase):
    def test_snapshot_creation(self):
        snap = MetricSnapshot.objects.create(metrics={"test": 1})
        self.assertEqual(snap.metrics["test"], 1)