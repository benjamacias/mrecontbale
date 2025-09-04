from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "tax_id", "owner")
    search_fields = ("name", "tax_id")
    list_filter = ("owner",)
