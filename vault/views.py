from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User

from .forms import DUPLICATE_WORD_MESSAGE, VaultEntryForm
from .models import VaultEntry

# Create your views here.

ENTRIES_PER_PAGE = 10
UNIQUE_WORD_CONSTRAINT = 'vault_entry_unique_word_per_user'


def save_entry(form):
    try:
        with transaction.atomic():
            return form.save()
    except IntegrityError as error:
        if UNIQUE_WORD_CONSTRAINT not in str(error):
            raise
        form.add_error('word', DUPLICATE_WORD_MESSAGE)
        return None


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
            entry = save_entry(form)
            if entry is not None:
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


@login_required
@role_required(User.Role.LEARNER)
def entry_update(request, pk):
    entry = get_object_or_404(VaultEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        form = VaultEntryForm(request.POST, instance=entry, user=request.user)
        if form.is_valid():
            entry = save_entry(form)
            if entry is not None:
                messages.success(request, f'"{entry.word}" was updated.')
                return redirect('vault:detail', pk=entry.pk)
        messages.error(request, 'Your changes were not saved. Please correct the errors below.')
    else:
        form = VaultEntryForm(instance=entry, user=request.user)
    return render(request, 'vault/entry_form.html', {'form': form})


@login_required
@role_required(User.Role.LEARNER)
def entry_delete(request, pk):
    entry = get_object_or_404(VaultEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        word = entry.word
        entry.delete()
        messages.success(request, f'"{word}" was deleted from your vault.')
        return redirect('vault:list')
    return render(request, 'vault/entry_confirm_delete.html', {'entry': entry})


@login_required
@role_required(User.Role.LEARNER)
@require_POST
def entry_toggle_favorite(request, pk):
    entry = get_object_or_404(VaultEntry, pk=pk, user=request.user)
    entry.is_favorite = not entry.is_favorite
    entry.save(update_fields=['is_favorite', 'updated_at'])
    if entry.is_favorite:
        messages.success(request, f'"{entry.word}" was added to your favorites.')
    else:
        messages.success(request, f'"{entry.word}" was removed from your favorites.')
    return redirect('vault:detail', pk=entry.pk)
