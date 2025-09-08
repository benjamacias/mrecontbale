from django import forms

from .models import AccountEntry


class AccountEntryForm(forms.ModelForm):
    class Meta:
        model = AccountEntry
        fields = ["description", "amount"]
        labels = {
            "description": "Descripción",
            "amount": "Monto",
        }
