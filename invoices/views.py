from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from .models import Invoice


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "invoices/invoice_list.html"
