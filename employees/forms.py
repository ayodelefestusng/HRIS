from django import forms
from employees.models import ProfileUpdateRequest, EmployeeChangeRequest



from django import forms
class ProfileUpdateForm(forms.ModelForm):
    # Field to handle skill proficiency levels (1-10)
    # In the template, we can iterate through skills
    skill_updates = forms.JSONField(
        required=False, 
        widget=forms.HiddenInput(),
        help_text="Hidden field populated by JS skill-selector"
    )

    class Meta:
        model = ProfileUpdateRequest
        fields = ["phone_number", "address", "next_of_kin", "next_of_kin_phone", "reason", "proposed_data"]
        # widgets = {
        #     "address": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        #     "reason": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        #     # Add other styling as per your existing code
        # }


        widgets = {
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "next_of_kin": forms.TextInput(attrs={"class": "form-control"}),
            "next_of_kin_phone": forms.TextInput(attrs={"class": "form-control"}),
            "reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Why are you requesting this change?",
                }
            ),
        }
        labels = {
            "phone_number": "New Phone Number",
            "next_of_kin": "New Next of Kin Name",
            "next_of_kin_phone": "New Next of Kin Phone",
        }


    def save(self, commit=True):
        instance = super().save(commit=False)
        # Add logic here if skill_updates needs manual parsing
        if commit:
            instance.save()
        return instance



class EmployeeUpdateForm(forms.ModelForm):
    """
    Form to capture updates. We include specific fields but override 
    the save method to populate the ChangeRequest model.
    """
    new_base_pay = forms.DecimalField(required=False, label="Proposed Base Pay")
    # Skill levels can be handled via dynamic fields or a specialized widget

    class Meta:
        model = EmployeeChangeRequest
        fields = ['justification', 'approval_date']

    def clean(self):
        cleaned_data = super().clean()
        # Custom logic: Ensure no overlapping pending requests
        if EmployeeChangeRequest.objects.filter(
            employee=self.instance.employee, 
            approval_status='pending'
        ).exists():
            raise forms.ValidationError("This employee already has a pending update request.")
        return cleaned_data



class ProfileUpdateFormv1(forms.ModelForm):
    class Meta:
        model = ProfileUpdateRequest
        fields = [
            "phone_number",
            "address",
            "next_of_kin",
            "next_of_kin_phone",
            "reason",
        ]
        widgets = {
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "next_of_kin": forms.TextInput(attrs={"class": "form-control"}),
            "next_of_kin_phone": forms.TextInput(attrs={"class": "form-control"}),
            "reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Why are you requesting this change?",
                }
            ),
        }
        labels = {
            "phone_number": "New Phone Number",
            "next_of_kin": "New Next of Kin Name",
            "next_of_kin_phone": "New Next of Kin Phone",
        }
