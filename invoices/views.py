from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView

from .forms import InvoiceForm
from .models import Invoice


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "invoices/invoice_list.html"


class InvoiceCreateView(LoginRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "invoices/invoice_form.html"
    success_url = reverse_lazy("invoice-list")
