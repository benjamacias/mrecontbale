from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model supporting simple role-based access."""

    class Roles(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        ACCOUNTANT = "ACCOUNTANT", "Accountant"
        CLIENT = "CLIENT", "Client"

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.CLIENT,
        help_text="Determines the level of access for the user.",
    )
