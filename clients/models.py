from django.conf import settings
from django.db import models


class Client(models.Model):
    """Representa a un cliente del estudio contable."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clients",
        help_text="Contador responsable de este cliente.",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    tax_id = models.CharField(
        max_length=20,
        help_text="CUIT o número de identificación fiscal",
    )
    address = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name
