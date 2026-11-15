from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'language_level', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    fieldsets = BaseUserAdmin.fieldsets + (
        ('LexiTrace profile', {
            'fields': (
                'role',
                'contact_number',
                'profile_photo',
                'language_level',
                'offline_download',
            ),
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('LexiTrace profile', {
            'classes': ('wide',),
            'fields': ('email', 'role'),
        }),
    )
