from django import forms
from django.forms.widgets import FileInput, TextInput


class ChatForm(forms.Form):
    message = forms.CharField(
        required=False,
        widget=TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Type your message...",
                "id": "message-input",
                "autofocus": True,
            }
        ),
    )
    attachment = forms.FileField(
        required=False,
        widget=FileInput(
            attrs={
                "class": "file-input",
                "id": "file-input",
                "accept": "image/png, image/jpeg",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        message = cleaned_data.get("message")
        attachment = cleaned_data.get("attachment")

        if not message and not attachment:
            raise forms.ValidationError("Please enter a message or attach an image.")
        return cleaned_data
