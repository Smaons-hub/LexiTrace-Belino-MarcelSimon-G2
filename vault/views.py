from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import User

from .forms import DUPLICATE_WORD_MESSAGE, VaultEntryForm
from .models import VaultEntry

# Create your views here.

ENTRIES_PER_PAGE = 10
UNIQUE_WORD_CONSTRAINT = 'vault_entry_unique_word_per_user'


@login_required
@role_required(User.Role.LEARNER)
def entry_list(request):
    paginator = Paginator(request.user.vault_entries.all(), ENTRIES_PER_PAGE)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'vault/entry_list.html', {'page': page, 'total': paginator.count})


@login_required
@role_required(User.Role.LEARNER)
def entry_create(request):
    if request.method == 'POST':
        form = VaultEntryForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    entry = form.save()
            except IntegrityError as error:
                if UNIQUE_WORD_CONSTRAINT not in str(error):
                    raise
                form.add_error('word', DUPLICATE_WORD_MESSAGE)
            else:
                messages.success(request, f'"{entry.word}" was added to your vault.')
                return redirect('vault:detail', pk=entry.pk)
        messages.error(request, 'Your word was not saved. Please correct the errors below.')
    else:
        form = VaultEntryForm(user=request.user)
    return render(request, 'vault/entry_form.html', {'form': form})


@login_required
@role_required(User.Role.LEARNER)
def entry_detail(request, pk):
    entry = get_object_or_404(
        VaultEntry.objects.prefetch_related('tags'),
        pk=pk,
        user=request.user,
    )
    return render(request, 'vault/entry_detail.html', {'entry': entry})
