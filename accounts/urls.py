from django.urls import path

from .views import UserLoginView, UserLogoutView, dashboard, home, register

app_name = 'accounts'

urlpatterns = [
    path('', home, name='home'),
    path('register/', register, name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
]
