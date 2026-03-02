from rest_framework import serializers
from django.utils import timezone

from .models import LeaveType, LeaveBalance, LeaveRequest
from leave.services.leave_services import get_working_days



class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type = LeaveTypeSerializer(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = "__all__"


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee = serializers.PrimaryKeyRelatedField(read_only=True)
    duration_days = serializers.ReadOnlyField()

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee",
            "leave_type",
            "start_date",
            "end_date",
            "reason",
            "status",
            "approved_by",
            "requested_at",
            "decided_at",
            "duration_days",
        ]
        read_only_fields = ("status", "approved_by", "requested_at", "decided_at")

    # ✅ CREATE
    def create(self, validated_data):
        request = self.context["request"]
        validated_data["employee"] = request.user.hr_profile
        return super().create(validated_data)

    # ✅ VALIDATION (overlap + balance)
    def validate(self, attrs):
        employee = self.context["request"].user.hr_profile
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        leave_type = attrs.get("leave_type")

        # Date order check
        if start > end:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be earlier than start date."}
            )

        # Overlap check
        overlapping = employee.leave_requests.filter(
            status__in=["PEN", "APP"],
            start_date__lte=end,
            end_date__gte=start,
        )
        if self.instance:
            overlapping = overlapping.exclude(id=self.instance.id)

        if overlapping.exists():
            raise serializers.ValidationError(
                "This leave request overlaps with an existing leave."
            )

        # Leave balance check
        year = timezone.now().year
        duration = get_working_days(start, end)

        try:
            balance = LeaveBalance.objects.get(
                employee=employee,
                leave_type=leave_type,
                year=year,
            )
        except LeaveBalance.DoesNotExist:
            raise serializers.ValidationError(
                {"leave_type": "No leave balance available for this leave type."}
            )

        if balance.balance_days < duration:
            raise serializers.ValidationError(
                {
                    "leave_type": (
                        f"Insufficient leave balance. "
                        f"Available: {balance.balance_days} days, "
                        f"Requested: {duration} days."
                    )
                }
            )

        return attrs

    # ✅ UPDATE (cancellation only)
    def update(self, instance, validated_data):
        if validated_data.get("status") == "CAN":
            if instance.status != "PEN":
                raise serializers.ValidationError(
                    {"status": "Only pending leave requests can be cancelled."}
                )
            instance.status = "CAN"
            instance.decided_at = timezone.now()
            instance.save()
            return instance

        raise serializers.ValidationError(
            "Only cancellation is allowed through this endpoint."
        )