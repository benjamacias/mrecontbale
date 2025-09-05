from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from clients.models import Client
from .forms import AccountEntryForm


@login_required
def client_entries(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    entries = client.entries.all()
    return render(
        request,
        "accounts/entries.html",
        {"client": client, "entries": entries},
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
