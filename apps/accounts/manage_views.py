"""系統帳號的後台管理頁（只有管理員能進）。"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView

from apps.backoffice.views import ManageCreateView, ManageListView, ManageMixin, ManageUpdateView

from .forms import UserCreateForm, UserPasswordForm, UserUpdateForm
from .models import User


class UserMixin:
    model = User
    page_key = "manage-users"
    list_url_name = "accounts_manage:user_list"

    def get_queryset(self):
        return User.objects.order_by("username")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["editor"] = self.request.user
        return kwargs


class UserList(UserMixin, ManageListView):
    columns = [
        ("工號", "username"),
        ("姓名", "name"),
        ("身分", "level_display"),
        ("啟用", "is_active"),
        ("最後登入", lambda o: o.last_login.strftime("%Y-%m-%d %H:%M") if o.last_login else ""),
    ]
    search_fields = ["username", "name"]
    search_placeholder = "工號或姓名"
    create_url_name = "accounts_manage:user_create"
    edit_url_name = "accounts_manage:user_edit"


class UserCreate(UserMixin, ManageCreateView):
    form_class = UserCreateForm


class UserUpdate(UserMixin, ManageUpdateView):
    form_class = UserUpdateForm
    template_name = "accounts/user_form.html"


class UserPassword(UserMixin, ManageMixin, FormView):
    """幫使用者重設密碼（忘記密碼時使用）。"""

    template_name = "backoffice/form.html"
    form_class = UserPasswordForm

    def get_target(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])

    def get_form_kwargs(self):
        kwargs = FormView.get_form_kwargs(self)
        kwargs["user"] = self.get_target()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = f"{context['form'].user}／重設密碼"
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f"已重設 {form.user} 的密碼。")
        return redirect(reverse("accounts_manage:user_edit", args=[form.user.pk]))
