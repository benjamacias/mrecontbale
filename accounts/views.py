from django.shortcuts import get_object_or_404, render

from clients.models import Client


def client_entries(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    entries = client.entries.all()
    return render(
        request,
        "accounts/entries.html",
        {"client": client, "entries": entries},
    )
