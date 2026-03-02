# leave/forms.py
from django import forms
from .models import LeaveRequest, LeaveType

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ["leave_type", "start_date", "end_date", "reason", "attachment"]

    def __init__(self, *args, **kwargs):
        # Pop request out of kwargs so BaseModelForm doesn't see it
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Filter leave types by tenant
        if self.request:
            self.fields["leave_type"].queryset = LeaveType.objects.filter(
                tenant=self.request.user.tenant
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.request:
            instance.tenant = self.request.user.tenant
            instance.employee = self.request.user.hr_profile
        # if commit:
        instance.save()
        return instance