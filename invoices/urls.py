from django.urls import path

from .views import InvoiceListView

urlpatterns = [
    path("", InvoiceListView.as_view(), name="invoice-list"),
]
