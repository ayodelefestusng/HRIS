from rest_framework import serializers
from .models import ShiftSchedule, AttendanceRecord, OvertimeRecord, ClockLog


class ShiftScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftSchedule
        fields = "__all__"


class AttendanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = "__all__"


class OvertimeRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = OvertimeRecord
        fields = "__all__"


class ClockLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClockLog
        fields = "__all__"