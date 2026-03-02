from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.contrib.auth import get_user_model


from django.core.mail import send_mail
from django.conf import settings
User = get_user_model()
import logging

logger = logging.getLogger(__name__)


class Notification(models.Model):
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    send_email = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional: generic target (if you added this)
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    target_object_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey("target_content_type", "target_object_id")

    def __str__(self):
        return f"{self.title} → {self.recipient}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])



class NotificationService:
    @staticmethod
    def notify(recipient_emp, title, message, target=None, send_email=True):
        """
        recipient_emp: Expects an Employee instance
        """
        try:
            notification = Notification.objects.create(
                recipient=recipient_emp.user,
                title=title,
                message=message,
                target=target,
                send_email=send_email
            )

            if send_email and recipient_emp.user.email:
                send_mail(
                    subject=title,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient_emp.user.email],
                    fail_silently=True,
                )
            return notification
        except Exception as e:
            logger.error(f"Notification failed: {str(e)}")
            return None