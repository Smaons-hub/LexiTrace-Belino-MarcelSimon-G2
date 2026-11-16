from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import role_required
from .forms import LoginForm, ProfileForm, RegisterForm, SearchForm
from .models import SearchHistory, User

RECENT_SEARCHES_SHOWN = 5
SEARCH_HISTORY_LIMIT = 20

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


def search_panel_context(request):
    return {
        'search_form': SearchForm(),
        'recent_searches': request.user.search_history.all()[:RECENT_SEARCHES_SHOWN],
    }


@role_required(User.Role.LEARNER)
def learner_dashboard(request):
    return render(request, 'accounts/learner_dashboard.html', search_panel_context(request))


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
        **search_panel_context(request),
    })


@login_required
@require_POST
def search_submit(request):
    form = SearchForm(request.POST)
    if not form.is_valid():
        messages.error(request, form.errors['query'][0])
        return redirect('accounts:dashboard')
    query = form.cleaned_data['query']
    history = request.user.search_history
    with transaction.atomic():
        existing = history.select_for_update().filter(query__iexact=query).first()
        if existing:
            existing.created_at = timezone.now()
            existing.save(update_fields=['created_at'])
        else:
            history.create(query=query)
        keep = history.values_list('pk', flat=True)[:SEARCH_HISTORY_LIMIT]
        history.exclude(pk__in=list(keep)).delete()
    messages.success(request, f'Search for "{query}" saved. Dictionary results are not available yet.')
    return redirect('accounts:dashboard')


@login_required
@require_POST
def search_delete(request, pk):
    entry = get_object_or_404(SearchHistory, pk=pk, user=request.user)
    entry.delete()
    messages.success(request, f'Removed "{entry.query}" from your recent searches.')
    return redirect('accounts:dashboard')


@login_required
@require_POST
def search_clear(request):
    deleted, _ = request.user.search_history.all().delete()
    if deleted:
        messages.success(request, 'Your recent searches have been cleared.')
    else:
        messages.info(request, 'You have no recent searches to clear.')
    return redirect('accounts:dashboard')


@login_required
def profile(request):
    return render(request, 'accounts/profile.html')


@login_required
def profile_edit(request):
    account = User.objects.get(pk=request.user.pk)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
        messages.error(request, 'Could not update your profile. Please correct the errors below.')
    else:
        form = ProfileForm(instance=account)
    return render(request, 'accounts/profile_edit.html', {'form': form})
