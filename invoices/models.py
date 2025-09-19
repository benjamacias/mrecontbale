from django.conf import settings
from django.core.mail import send_mail
from django.db import models

from .afip import create_invoice_afip


class Invoice(models.Model):
    """Representa una factura emitida para un cliente y opcionalmente autorizada por AFIP."""

    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    class InvoiceType(models.TextChoices):
        A = "A", "Factura A"
        B = "B", "Factura B"
        C = "C", "Factura C"

    description = models.TextField(blank=True, default="")
    number = models.CharField(max_length=30, blank=True)
    issued_at = models.DateField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    afip_authorization_code = models.CharField(max_length=64, blank=True)
    invoice_type = models.CharField(
        max_length=1,
        choices=InvoiceType.choices,
        default=InvoiceType.B,
    )
    
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Efectivo"
        CARD = "card", "Tarjeta de crédito"
        TRANSFER = "transfer", "Transferencia bancaria"

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )

    class Meta:
        ordering = ["-issued_at", "id"]

    def __str__(self):
        return f"Factura {self.number or 'sin número'} ({self.get_invoice_type_display()}) - {self.client}"

    def authorize_with_afip(self):
        """Enviar los datos de la factura al servicio de AFIP y guardar el código de autorización."""
        self.afip_authorization_code = create_invoice_afip(self)
        self.save(update_fields=["afip_authorization_code"])

    def send_email(self):
        """Enviar la factura al correo del cliente."""
        if self.client.email:
            message_lines = [f"Total: {self.total}"]
            if self.description:
                message_lines.append(f"Descripción: {self.description}")
            send_mail(
                subject=f"Factura {self.number}",
                message="\n".join(message_lines),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[self.client.email],
            )
