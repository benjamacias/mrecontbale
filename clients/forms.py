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
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": (
                        "w-full rounded-xl border border-slate-300 bg-white px-4 py-2 "
                        "text-slate-700 shadow-sm transition focus:border-blue-500 "
                        "focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    ),
                    "placeholder": "Nombre legal o comercial",
                    "ng-model": "vm.formData.name",
                    "ng-model-options": "{ debounce: 200 }",
                    "autocomplete": "name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": (
                        "w-full rounded-xl border border-slate-300 bg-white px-4 py-2 "
                        "text-slate-700 shadow-sm transition focus:border-blue-500 "
                        "focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    ),
                    "placeholder": "correo@cliente.com",
                    "ng-model": "vm.formData.email",
                    "ng-model-options": "{ debounce: 200 }",
                    "autocomplete": "email",
                }
            ),
            "tax_id": forms.TextInput(
                attrs={
                    "class": (
                        "w-full rounded-xl border border-slate-300 bg-white px-4 py-2 "
                        "text-slate-700 shadow-sm transition focus:border-blue-500 "
                        "focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    ),
                    "placeholder": "00-00000000-0",
                    "ng-model": "vm.formData.tax_id",
                    "ng-model-options": "{ debounce: 200 }",
                    "autocomplete": "off",
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": (
                        "w-full rounded-xl border border-slate-300 bg-white px-4 py-2 "
                        "text-slate-700 shadow-sm transition focus:border-blue-500 "
                        "focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    ),
                    "rows": 3,
                    "placeholder": "Dirección fiscal y observaciones",
                    "ng-model": "vm.formData.address",
                    "ng-model-options": "{ debounce: 200 }",
                    "autocomplete": "street-address",
                }
            ),
        }
