import os
import sys

from django.apps import AppConfig


class InvoicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "invoices"

    def ready(self) -> None:  # pragma: no cover - startup hook
        super().ready()

        if "runserver" not in sys.argv:
            return

        run_main = os.environ.get("RUN_MAIN")
        if run_main != "true" and "--noreload" not in sys.argv:
            return

        from .afip import refresh_wsaa_token_if_needed

        refresh_wsaa_token_if_needed()
