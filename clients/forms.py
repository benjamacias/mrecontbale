from django import forms

from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "email", "tax_id", "address"]
        labels = {
            "name": "Nombre",
            "email": "Correo electrónico",
            "tax_id": "CUIT",
            "address": "Dirección",
        }
