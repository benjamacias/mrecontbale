from django.contrib import admin

from .models import AccountEntry


@admin.register(AccountEntry)
class AccountEntryAdmin(admin.ModelAdmin):
    list_display = ("client", "date", "description", "amount", "balance")
    list_filter = ("client",)
    search_fields = ("client__name", "description")
