from django.urls import path

from .views import (
    admin_entry_delete,
    admin_entry_detail,
    admin_entry_list,
    entry_create,
    entry_delete,
    entry_detail,
    entry_list,
    entry_toggle_favorite,
    entry_update,
    tag_delete,
    tag_list,
)

app_name = 'vault'

urlpatterns = [
    path('', entry_list, name='list'),
    path('new/', entry_create, name='create'),
    path('tags/', tag_list, name='tag_list'),
    path('tags/<int:pk>/delete/', tag_delete, name='tag_delete'),
    path('admin/entries/', admin_entry_list, name='admin_entry_list'),
    path('admin/entries/<int:pk>/', admin_entry_detail, name='admin_entry_detail'),
    path('admin/entries/<int:pk>/delete/', admin_entry_delete, name='admin_entry_delete'),
    path('<int:pk>/', entry_detail, name='detail'),
    path('<int:pk>/edit/', entry_update, name='update'),
    path('<int:pk>/delete/', entry_delete, name='delete'),
    path('<int:pk>/favorite/', entry_toggle_favorite, name='toggle_favorite'),
]
