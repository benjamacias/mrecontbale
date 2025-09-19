from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from clients.models import Client
from invoices.models import Invoice
from .forms import AccountEntryForm


@login_required
def client_entries(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    entries = client.entries.all()
    return render(
        request,
        "accounts/entries.html",
        {
            "client": client,
            "entries": entries,
            "invoice_types": Invoice.InvoiceType.choices,
            "default_invoice_type": Invoice.InvoiceType.B,
        },
    )


@login_required
def add_entry(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    if request.method == "POST":
        form = AccountEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.client = client
            entry.save()
            return redirect("account-entries", client_id=client.id)
    else:
        form = AccountEntryForm()
    return render(
        request,
        "accounts/entry_form.html",
        {"form": form, "client": client},
    )


def _build_invoice_description(entries):
    if not entries:
        return ""

    if len(entries) == 1:
        entry = entries[0]
        description = (entry.description or "").strip()
        return description or entry.date.strftime("%d/%m/%Y")

    details = []
    for entry in entries:
        detail = (entry.description or "Movimiento sin descripción").strip()
        if not detail:
            detail = "Movimiento sin descripción"
        details.append(
            f"{entry.date.strftime('%d/%m/%Y')} - {detail} (${entry.amount:.2f})"
        )
    return "Movimientos facturados:\n" + "\n".join(details)


@login_required
def create_invoice_from_entries(request, client_id):
    client = get_object_or_404(Client, id=client_id)

    if request.method != "POST":
        return redirect("account-entries", client_id=client.id)

    single_entry = request.POST.get("single_entry")
    if single_entry:
        entry_ids = [single_entry]
    else:
        entry_ids = request.POST.getlist("entries")

    invoice_type = request.POST.get("invoice_type") or Invoice.InvoiceType.B
    if invoice_type not in Invoice.InvoiceType.values:
        messages.error(
            request,
            "Seleccioná un tipo de factura válido para continuar.",
        )
        return redirect("account-entries", client_id=client.id)

    entries = list(
        client.entries.filter(id__in=entry_ids).order_by("date", "id")
    )

    if not entries:
        messages.warning(
            request,
            "Seleccioná al menos un movimiento válido para generar la factura.",
        )
        return redirect("account-entries", client_id=client.id)

    total = sum((entry.amount for entry in entries), Decimal("0"))
    if total <= Decimal("0"):
        messages.error(
            request,
            "No se puede generar una factura con un total menor o igual a cero.",
        )
        return redirect("account-entries", client_id=client.id)

    description = _build_invoice_description(entries)

    invoice = Invoice.objects.create(
        client=client,
        total=total,
        description=description or "Factura generada desde movimientos",
        invoice_type=invoice_type,
    )

    invoice_type_label = dict(Invoice.InvoiceType.choices).get(
        invoice_type, invoice_type
    )

    messages.success(
        request,
        f"{invoice_type_label} creada por ${total:.2f} a partir de {len(entries)} movimiento(s).",
    )

    return redirect("invoice-list")
