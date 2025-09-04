from django.contrib import admin

from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "client", "total", "afip_authorization_code")
    search_fields = ("number", "client__name")
    list_filter = ("client",)
