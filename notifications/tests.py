from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from django.contrib.auth import get_user_model
from notifications.models import Notification

User = get_user_model()


class NotificationTests(TestCase):
    def test_create_notification(self):
        user = User.objects.create(username="testuser", email="test@example.com")
        n = Notification.objects.create(
            recipient=user,
            title="Test",
            message="This is a test notification",
        )
        self.assertFalse(n.is_read)
        self.assertEqual(str(n), "Test → testuser")