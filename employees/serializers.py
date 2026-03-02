from rest_framework import serializers
from .models import (
    Employee,
    JobAssignment,
    CompensationRecord,
    Department,
    JobTitle,
    EmployeeDocument,
)


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class JobTitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobTitle
        fields = "__all__"


class JobAssignmentSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source="department", write_only=True
    )
    job_title = JobTitleSerializer(read_only=True)
    job_title_id = serializers.PrimaryKeyRelatedField(
        queryset=JobTitle.objects.all(), source="job_title", write_only=True
    )

    class Meta:
        model = JobAssignment
        fields = [
            "id",
            "employee",
            "department",
            "department_id",
            "job_title",
            "job_title_id",
            "manager",
            "employment_status",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
        ]
        read_only_fields = ("employee", "created_at")


class CompensationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompensationRecord
        fields = "__all__"
        read_only_fields = ("employee", "created_at")


class EmployeeSerializer(serializers.ModelSerializer):
    job_history = JobAssignmentSerializer(many=True, read_only=True)
    comp_history = CompensationRecordSerializer(many=True, read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "user",
            "employee_id",
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "personal_email",
            "phone_number",
            "nationality",
            "mother_maiden_name",
            "address",
            "house_number",
            "city",
            "state",
            "country",
            "passport_number",
            "national_id_number",
            "driver_license_number",
            "next_of_kin",
            "next_of_kin_phone_number",
            "next_of_kin_email",
            "emergency_contact_name",
            "emergency_contact_phone_number",
            "is_active",
            "is_deleted",
            "created_at",
            "last_updated",
            "job_history",
            "comp_history",
        ]
        read_only_fields = ("created_at", "last_updated", "is_deleted")
        
        


# employees/serializers.py
from rest_framework import serializers
from .models import PolicyAcknowledgement

class PolicyAcknowledgementSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyAcknowledgement
        fields = "__all__"
        
        

class EmployeeDocumentSerializer(serializers.ModelSerializer):
    # Nested acknowledgements

    acknowledgements = PolicyAcknowledgementSerializer(many=True, read_only=True)

    class Meta:
        model = EmployeeDocument
        fields = "__all__"
        read_only_fields = ("uploaded_at",)

