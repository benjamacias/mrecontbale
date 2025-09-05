from django.urls import path

from .views import ClientListView, ClientCreateView

urlpatterns = [
    path("", ClientListView.as_view(), name="client-list"),
    path("new/", ClientCreateView.as_view(), name="client-create"),
]
