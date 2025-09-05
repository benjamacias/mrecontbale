from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView

from .forms import UserForm
from .models import User


class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = "users/user_list.html"


class UserCreateView(LoginRequiredMixin, CreateView):
    model = User
    form_class = UserForm
    template_name = "users/user_form.html"
    success_url = reverse_lazy("user-list")
