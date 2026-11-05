# 僅供緊急備用，平常請用後台管理（/manage/）
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "name", "is_admin", "is_active")
    list_filter = ("is_admin", "is_active")
    search_fields = ("username", "name")
    ordering = ("username",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("個人資料", {"fields": ("name", "email")}),
        ("狀態", {"fields": ("is_admin", "is_active", "is_staff", "is_superuser")}),
        ("重要日期", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("username", "name", "password1", "password2")}),
    )
