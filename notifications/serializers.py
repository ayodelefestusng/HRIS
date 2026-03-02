from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient",
            "title",
            "message",
            "target_content_type",
            "target_object_id",
            "is_read",
            "created_at",
            "read_at",
            "send_email",
        ]
        read_only_fields = ("created_at", "read_at", "recipient")
