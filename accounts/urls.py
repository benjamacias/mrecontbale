from django.urls import path

from . import views

urlpatterns = [
    path("<int:client_id>/", views.client_entries, name="account-entries"),
]
