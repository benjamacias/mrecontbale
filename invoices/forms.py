from django import forms

from .models import Invoice


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["client", "number", "total", "payment_method"]
        labels = {
            "client": "Cliente",
            "number": "Número",
            "total": "Total",
            "payment_method": "Método de pago",
        }
