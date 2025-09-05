from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, View
from django.shortcuts import redirect, get_object_or_404

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


class InvoiceSendView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        invoice.send_email()
        return redirect("invoice-list")
