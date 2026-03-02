from rest_framework import serializers
from .models import Course, TrainingSession, Enrollment, Certification, SkillMatrix

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = "__all__"

class TrainingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingSession
        fields = "__all__"

class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = "__all__"

class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = "__all__"

class SkillMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillMatrix
        fields = "__all__"
