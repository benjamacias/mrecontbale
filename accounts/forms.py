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
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "class": (
                        "w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-700 "
                        "shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 "
                        "focus:ring-blue-500/50"
                    ),
                    "rows": 3,
                    "placeholder": "Detalle del movimiento",
                    "ng-model": "vm.formData.description",
                    "ng-model-options": "{ debounce: 200 }",
                }
            ),
            "amount": forms.NumberInput(
                attrs={
                    "class": (
                        "w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-700 "
                        "shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 "
                        "focus:ring-blue-500/50"
                    ),
                    "step": "0.01",
                    "ng-model": "vm.formData.amount",
                    "ng-model-options": "{ debounce: 200 }",
                    "placeholder": "0.00",
                }
            ),
        }
