from django.urls import path

from .views import InvoiceListView, InvoiceCreateView, InvoiceSendView

urlpatterns = [
    path("", InvoiceListView.as_view(), name="invoice-list"),
    path("new/", InvoiceCreateView.as_view(), name="invoice-create"),
    path("<int:pk>/send/", InvoiceSendView.as_view(), name="invoice-send"),
]
