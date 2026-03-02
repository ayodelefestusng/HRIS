from rest_framework import serializers
from talent.models import (
    RoleProfile,
    Competency,
    Skill,
    CompetencySkill,
    RoleCompetencyRequirement,
    EmployeeSkillProfile,
    EmployeeRoleFit,
)


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = "__all__"


class CompetencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Competency
        fields = "__all__"


class RoleProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleProfile
        fields = "__all__"


class CompetencySkillSerializer(serializers.ModelSerializer):
    competency = CompetencySerializer(read_only=True)
    skill = SkillSerializer(read_only=True)

    class Meta:
        model = CompetencySkill
        fields = "__all__"


class RoleCompetencyRequirementSerializer(serializers.ModelSerializer):
    competency = CompetencySerializer(read_only=True)
    competency_id = serializers.PrimaryKeyRelatedField(
        queryset=Competency.objects.all(),
        source="competency",
        write_only=True,
    )

    class Meta:
        model = RoleCompetencyRequirement
        fields = [
            "id",
            "role",
            "competency",
            "competency_id",
            "weight",
            "required_level",
        ]


class EmployeeSkillProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeSkillProfile
        fields = "__all__"
        read_only_fields = ("employee",)

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["employee"] = request.user.hr_profile
        return super().create(validated_data)


class EmployeeRoleFitSerializer(serializers.ModelSerializer):
    role = RoleProfileSerializer(read_only=True)

    class Meta:
        model = EmployeeRoleFit
        fields = ["id", "employee", "role", "score", "computed_at"]
        read_only_fields = ("employee", "score", "computed_at")
        
        
from talent.models import Appraisal, AppraisalSkillRating
from rest_framework import serializers

class AppraisalSkillRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppraisalSkillRating
        fields = ["id", "skill", "source", "rating", "comment"]


class AppraisalSerializer(serializers.ModelSerializer):
    skill_ratings = AppraisalSkillRatingSerializer(many=True, read_only=True)

    class Meta:
        model = Appraisal
        fields = [
            "id",
            "employee",
            "role",
            "period_label",
            "status",
            "created_at",
            "submitted_at",
            "manager_reviewed_at",
            "finalized_at",
            "overall_score",
            "skill_ratings",
        ]
        read_only_fields = (
            "employee",
            "status",
            "created_at",
            "submitted_at",
            "manager_reviewed_at",
            "finalized_at",
            "overall_score",
        )

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["employee"] = request.user.hr_profile
        return super().create(validated_data)
    
