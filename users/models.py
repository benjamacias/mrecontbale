from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Modelo de usuario personalizado con acceso basado en roles."""

    class Roles(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        ACCOUNTANT = "ACCOUNTANT", "Contador"
        CLIENT = "CLIENT", "Cliente"

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.CLIENT,
        help_text="Determina el nivel de acceso del usuario.",
    )
