from rest_framework import serializers
from ats.models import (
    OnboardingTemplate,
    OnboardingTaskTemplate,
    OnboardingPlan,
    OnboardingTask,
)


class OnboardingTaskTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingTaskTemplate
        fields = "__all__"


class OnboardingTemplateSerializer(serializers.ModelSerializer):
    task_templates = OnboardingTaskTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = OnboardingTemplate
        fields = "__all__"


class OnboardingTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingTask
        fields = "__all__"
        read_only_fields = ("created_at", "completed_at")


class OnboardingPlanSerializer(serializers.ModelSerializer):
    tasks = OnboardingTaskSerializer(many=True, read_only=True)

    class Meta:
        model = OnboardingPlan
        fields = "__all__"
        read_only_fields = ("created_at", "completed_at")