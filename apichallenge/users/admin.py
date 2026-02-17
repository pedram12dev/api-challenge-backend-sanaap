from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apichallenge.users.models import BaseUser


@admin.register(BaseUser)
class BaseUserAdmin(BaseUserAdmin):
    list_display = ("id", "username", "role", "is_active", "is_admin", "created_at")
    list_filter = ("role", "is_active", "is_admin")
    search_fields = ("username",)
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Role", {"fields": ("role",)}),
        ("Permissions", {"fields": ("is_active", "is_admin", "is_superuser")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("username", "password1", "password2", "role")}),
    )
