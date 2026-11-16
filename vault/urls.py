from django.urls import path

from .views import (
    entry_create,
    entry_delete,
    entry_detail,
    entry_list,
    entry_toggle_favorite,
    entry_update,
)

app_name = 'vault'

urlpatterns = [
    path('', entry_list, name='list'),
    path('new/', entry_create, name='create'),
    path('<int:pk>/', entry_detail, name='detail'),
    path('<int:pk>/edit/', entry_update, name='update'),
    path('<int:pk>/delete/', entry_delete, name='delete'),
    path('<int:pk>/favorite/', entry_toggle_favorite, name='toggle_favorite'),
]
