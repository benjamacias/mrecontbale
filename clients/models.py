from django.conf import settings
from django.db import models


class Client(models.Model):
    """Represents a client for the accounting firm."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clients",
        help_text="Accountant responsible for this client.",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    tax_id = models.CharField(max_length=20, help_text="CUIT or tax identification number")
    address = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name
