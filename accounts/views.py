from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import RegisterForm

# Create your views here.


def home(request):
    return render(request, 'accounts/home.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully. You can now log in.')
            return redirect('accounts:home')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})
