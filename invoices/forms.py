from django import forms

from .models import Invoice


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["client", "number", "total", "description", "payment_method"]
        labels = {
            "client": "Cliente",
            "number": "Número",
            "description": "Descripción",
            "total": "Total",
            "payment_method": "Método de pago",
        }
        widgets = {
            "client": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-700 "
                        "shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 "
                        "focus:ring-blue-500/50"
                    ),
                    "ng-model": "vm.formData.client",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": (
                        "w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-700 "
                        "shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 "
                        "focus:ring-blue-500/50"
                    ),
                    "rows": 3,
                    "placeholder": "Detalle adicional de la operación",
                    "ng-model": "vm.formData.description",
                    "ng-model-options": "{ debounce: 200 }",
                }
            ),
            "number": forms.TextInput(
                attrs={
                    "class": (
                        "w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-700 "
                        "shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 "
                        "focus:ring-blue-500/50"
                    ),
                    "placeholder": "0001-00000001",
                    "ng-model": "vm.formData.number",
                    "ng-model-options": "{ debounce: 200 }",
                    "autocomplete": "off",
                }
            ),
            "total": forms.NumberInput(
                attrs={
                    "class": (
                        "w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-700 "
                        "shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 "
                        "focus:ring-blue-500/50"
                    ),
                    "min": 0,
                    "step": "0.01",
                    "ng-model": "vm.formData.total",
                    "ng-model-options": "{ debounce: 200 }",
                    "autocomplete": "off",
                }
            ),
            "payment_method": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-xl border border-slate-300 bg-white px-4 py-2 text-slate-700 "
                        "shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 "
                        "focus:ring-blue-500/50"
                    ),
                    "ng-model": "vm.formData.payment_method",
                }
            ),
        }
