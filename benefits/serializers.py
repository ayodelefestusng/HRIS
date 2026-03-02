from rest_framework import serializers
from .models import GradeHealthInsurance, Reimbursement

class GradeHealthInsuranceSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeHealthInsurance
        fields = "__all__"

# class GradeAllowanceSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = GradeAllowance
#         fields = "__all__"



class ReimbursementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reimbursement
        fields = "__all__"