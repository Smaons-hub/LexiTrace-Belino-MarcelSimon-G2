from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils import timezone

from .decorators import role_required
from .forms import LoginForm, RegisterForm
from .models import User

# Create your views here.


def home(request):
    return render(request, 'accounts/home.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully. You can now log in.')
            return redirect('accounts:login')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Welcome back, {form.get_user().display_name}!')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Login failed. Check your credentials and try again.')
        return super().form_invalid(form)


class UserLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, 'You have been logged out.')
        return response


@login_required
def dashboard(request):
    if request.user.role == User.Role.ADMIN:
        return redirect('accounts:admin_dashboard')
    return redirect('accounts:learner_dashboard')


@role_required(User.Role.LEARNER)
def learner_dashboard(request):
    return render(request, 'accounts/learner_dashboard.html')


@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    week_ago = timezone.now() - timedelta(days=7)
    stats = User.objects.aggregate(
        total=Count('pk'),
        learners=Count('pk', filter=Q(role=User.Role.LEARNER)),
        admins=Count('pk', filter=Q(role=User.Role.ADMIN)),
        new_this_week=Count('pk', filter=Q(date_joined__gte=week_ago)),
    )
    recent_users = (
        User.objects
        .only('username', 'email', 'role', 'date_joined', 'is_active')
        .order_by('-date_joined', '-pk')[:10]
    )
    return render(request, 'accounts/admin_dashboard.html', {
        'stats': stats,
        'recent_users': recent_users,
    })
