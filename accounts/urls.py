from django.urls import path

from .views import (
    UserLoginView,
    UserLogoutView,
    admin_dashboard,
    dashboard,
    home,
    learner_dashboard,
    profile,
    profile_edit,
    register,
    search_clear,
    search_delete,
    search_submit,
)

app_name = 'accounts'

urlpatterns = [
    path('', home, name='home'),
    path('register/', register, name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('dashboard/learner/', learner_dashboard, name='learner_dashboard'),
    path('dashboard/admin/', admin_dashboard, name='admin_dashboard'),
    path('search/', search_submit, name='search_submit'),
    path('search/<int:pk>/delete/', search_delete, name='search_delete'),
    path('search/clear/', search_clear, name='search_clear'),
    path('profile/', profile, name='profile'),
    path('profile/edit/', profile_edit, name='profile_edit'),
]
