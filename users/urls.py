from django.urls import path

from .views import UserListView, UserCreateView

urlpatterns = [
    path("", UserListView.as_view(), name="user-list"),
    path("new/", UserCreateView.as_view(), name="user-create"),
]
