# engagement/serializers.py
from rest_framework import serializers
from employees.models import (
    Survey,
    SurveyQuestion,
    SurveyResponse,
    Poll,
    PollOption,
    PollVote,
    PulseCheck,
)

class SurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = "__all__"

class SurveyQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyQuestion
        fields = "__all__"

class SurveyResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyResponse
        fields = "__all__"

class PollSerializer(serializers.ModelSerializer):
    class Meta:
        model = Poll
        fields = "__all__"

class PollOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollOption
        fields = "__all__"

class PollVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollVote
        fields = "__all__"

class PulseCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = PulseCheck
        fields = "__all__"