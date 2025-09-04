from django.db import models


class AccountEntry(models.Model):
    """Represents a movement in a client's current account."""

    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="entries",
    )
    date = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["-date", "id"]

    def __str__(self):
        return f"{self.client} {self.amount} on {self.date}"

    @property
    def balance(self):
        total = (
            AccountEntry.objects.filter(client=self.client, date__lte=self.date)
            .aggregate(models.Sum("amount"))
            .get("amount__sum")
            or 0
        )
        return total
