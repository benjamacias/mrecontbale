from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from .models import Client


class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = "clients/client_list.html"
