from rest_framework import serializers
from .models import (
    PayrollPeriod,
    PayrollEntry,
    # Deduction,
    # PayrollAllowanceItem,
    # PayrollDeductionItem,
)


class PayrollPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollPeriod
        fields = "__all__"




# class DeductionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Deduction
#         fields = "__all__"


# class PayrollAllowanceItemSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PayrollAllowanceItem
#         fields = "__all__"


# class PayrollDeductionItemSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PayrollDeductionItem
#         fields = "__all__"


# class PayrollEntrySerializer(serializers.ModelSerializer):
#     allowance_items = PayrollAllowanceItemSerializer(many=True, read_only=True)
#     deduction_items = PayrollDeductionItemSerializer(many=True, read_only=True)

#     class Meta:
#         model = PayrollEntry
#         fields = "__all__"
#         read_only_fields = ("created_at",)