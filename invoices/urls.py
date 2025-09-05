from django.urls import path

from .views import InvoiceListView, InvoiceCreateView

urlpatterns = [
    path("", InvoiceListView.as_view(), name="invoice-list"),
    path("new/", InvoiceCreateView.as_view(), name="invoice-create"),
]
