from rest_framework import serializers
from .models import Workflow, WorkflowStage, WorkflowInstance, WorkflowAction


class WorkflowStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStage
        fields = "__all__"


class WorkflowSerializer(serializers.ModelSerializer):
    steps = WorkflowStepSerializer(many=True, read_only=True)

    class Meta:
        model = Workflow
        fields = ["id", "name", "description", "steps"]


class WorkflowActionSerializer(serializers.ModelSerializer):
    actor = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = WorkflowAction
        fields = "__all__"
        read_only_fields = ("actor", "created_at")


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    actions = WorkflowActionSerializer(many=True, read_only=True)

    class Meta:
        model = WorkflowInstance
        fields = [
            "id",
            "workflow",
            "content_type",
            "object_id",
            "started_by",
            "started_at",
            "completed_at",
            "current_step",
            "actions",
        ]
        read_only_fields = ("started_by", "started_at")