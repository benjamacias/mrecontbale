from django.conf import settings
from django.core.mail import send_mail
from django.db import models

from .afip import create_invoice_afip


class Invoice(models.Model):
    """Represents an invoice emitted for a client and optionally authorized by AFIP."""

    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    number = models.CharField(max_length=30, blank=True)
    issued_at = models.DateField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    afip_authorization_code = models.CharField(max_length=64, blank=True)
    
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Credit Card"
        TRANSFER = "transfer", "Bank Transfer"

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )

    class Meta:
        ordering = ["-issued_at", "id"]

    def __str__(self):
        return f"Invoice {self.number} - {self.client}"

    def authorize_with_afip(self):
        """Send invoice data to AFIP service and store authorization code."""
        self.afip_authorization_code = create_invoice_afip(self)
        self.save(update_fields=["afip_authorization_code"])

    def send_email(self):
        """Send the invoice to the client's email."""
        if self.client.email:
            send_mail(
                subject=f"Invoice {self.number}",
                message=f"Total: {self.total}",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[self.client.email],
            )
