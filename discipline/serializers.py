# discipline/serializers.py
from rest_framework import serializers
from .models import Warning, Suspension, Investigation

class WarningSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warning
        fields = "__all__"

class SuspensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Suspension
        fields = "__all__"

class InvestigationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Investigation
        fields = "__all__"