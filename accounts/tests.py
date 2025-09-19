from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import AccountEntry
from clients.models import Client
from invoices.models import Invoice


class InvoiceFromEntriesViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester", password="pass1234"
        )
        self.client.force_login(self.user)
        self.client_record = Client.objects.create(
            owner=self.user,
            name="ACME",
            email="acme@example.com",
            tax_id="20-12345678-9",
        )

    def test_generate_invoice_from_single_entry(self):
        entry = AccountEntry.objects.create(
            client=self.client_record,
            description="Servicio mensual",
            amount=Decimal("150.00"),
        )

        response = self.client.post(
            reverse("account-entries-invoice", args=[self.client_record.id]),
            {
                "single_entry": str(entry.id),
                "invoice_type": Invoice.InvoiceType.B,
            },
        )

        self.assertRedirects(response, reverse("invoice-list"))
        invoice = Invoice.objects.get()
        self.assertEqual(invoice.client, self.client_record)
        self.assertEqual(invoice.total, Decimal("150.00"))
        self.assertEqual(invoice.description, "Servicio mensual")
        self.assertEqual(invoice.invoice_type, Invoice.InvoiceType.B)

    def test_generate_invoice_from_multiple_entries(self):
        first = AccountEntry.objects.create(
            client=self.client_record,
            description="Asesoramiento",
            amount=Decimal("200.00"),
        )
        second = AccountEntry.objects.create(
            client=self.client_record,
            description="Gestión administrativa",
            amount=Decimal("50.00"),
        )

        response = self.client.post(
            reverse("account-entries-invoice", args=[self.client_record.id]),
            {
                "entries": [str(first.id), str(second.id)],
                "invoice_type": Invoice.InvoiceType.A,
            },
        )

        self.assertRedirects(response, reverse("invoice-list"))
        invoice = Invoice.objects.get()
        self.assertEqual(invoice.total, Decimal("250.00"))
        self.assertTrue(invoice.description.startswith("Movimientos facturados:"))
        self.assertIn("Asesoramiento", invoice.description)
        self.assertIn("Gestión administrativa", invoice.description)
        self.assertEqual(invoice.invoice_type, Invoice.InvoiceType.A)

    def test_ignores_entries_from_other_client(self):
        valid_entry = AccountEntry.objects.create(
            client=self.client_record,
            description="Contabilidad",
            amount=Decimal("120.00"),
        )
        other_client = Client.objects.create(
            owner=self.user,
            name="Otro",
            email="otro@example.com",
            tax_id="20-00000000-0",
        )
        AccountEntry.objects.create(
            client=other_client,
            description="No debe incluirse",
            amount=Decimal("500.00"),
        )

        response = self.client.post(
            reverse("account-entries-invoice", args=[self.client_record.id]),
            {
                "entries": [str(valid_entry.id), "9999"],
                "invoice_type": Invoice.InvoiceType.C,
            },
        )

        self.assertRedirects(response, reverse("invoice-list"))
        invoice = Invoice.objects.get()
        self.assertEqual(invoice.total, Decimal("120.00"))
        self.assertIn("Contabilidad", invoice.description)
        self.assertEqual(invoice.invoice_type, Invoice.InvoiceType.C)

    def test_does_not_create_invoice_when_total_not_positive(self):
        entry = AccountEntry.objects.create(
            client=self.client_record,
            description="Ajuste",
            amount=Decimal("-10.00"),
        )

        response = self.client.post(
            reverse("account-entries-invoice", args=[self.client_record.id]),
            {"single_entry": str(entry.id)},
        )

        self.assertRedirects(
            response,
            reverse("account-entries", args=[self.client_record.id]),
        )
        self.assertFalse(Invoice.objects.exists())

    def test_invalid_invoice_type_is_rejected(self):
        entry = AccountEntry.objects.create(
            client=self.client_record,
            description="Servicio", 
            amount=Decimal("100.00"),
        )

        response = self.client.post(
            reverse("account-entries-invoice", args=[self.client_record.id]),
            {"single_entry": str(entry.id), "invoice_type": "Z"},
        )

        self.assertRedirects(
            response,
            reverse("account-entries", args=[self.client_record.id]),
        )
        self.assertFalse(Invoice.objects.exists())
