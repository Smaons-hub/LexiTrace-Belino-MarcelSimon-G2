from django.urls import path

from .views import entry_create, entry_detail, entry_list

app_name = 'vault'

urlpatterns = [
    path('', entry_list, name='list'),
    path('new/', entry_create, name='create'),
    path('<int:pk>/', entry_detail, name='detail'),
]
