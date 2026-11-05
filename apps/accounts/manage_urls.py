from django.urls import path

from . import manage_views as views

app_name = "accounts_manage"

urlpatterns = [
    path("users/", views.UserList.as_view(), name="user_list"),
    path("users/new/", views.UserCreate.as_view(), name="user_create"),
    path("users/<int:pk>/", views.UserUpdate.as_view(), name="user_edit"),
    path("users/<int:pk>/password/", views.UserPassword.as_view(), name="user_password"),
]
