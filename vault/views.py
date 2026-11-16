from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme, urlencode
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User

from .forms import DUPLICATE_WORD_MESSAGE, VaultEntryForm
from .models import VaultEntry, VaultTag

# Create your views here.

ENTRIES_PER_PAGE = 10
ADMIN_ENTRIES_PER_PAGE = 10
ADMIN_SEARCH_MAX_LENGTH = 100
VAULT_SEARCH_MAX_LENGTH = 100
DEFAULT_SORT = 'newest'
SORT_ORDERS = {
    'newest': ('-created_at', '-pk'),
    'oldest': ('created_at', 'pk'),
    'az': (Lower('word'), 'pk'),
}
SORT_CHOICES = (
    ('newest', 'Newest first'),
    ('oldest', 'Oldest first'),
    ('az', 'Word A to Z'),
)
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


def list_url(query='', favorites_only=False, tag=None, sort=DEFAULT_SORT):
    params = {}
    if query:
        params['q'] = query
    if favorites_only:
        params['fav'] = '1'
    if tag is not None:
        params['tag'] = tag.pk
    if sort != DEFAULT_SORT:
        params['sort'] = sort
    base = reverse('vault:list')
    return f'{base}?{urlencode(params)}' if params else base


@login_required
@role_required(User.Role.LEARNER)
def entry_list(request):
    user_tags = list(request.user.vault_tags.annotate(entry_count=Count('entries')))
    requested_tag = request.GET.get('tag', '')
    active_tag = None
    if requested_tag.isascii() and requested_tag.isdigit():
        active_tag = next((tag for tag in user_tags if tag.pk == int(requested_tag)), None)
    query = request.GET.get('q', '').strip()[:VAULT_SEARCH_MAX_LENGTH].strip()
    favorites_only = request.GET.get('fav') == '1'
    sort = request.GET.get('sort')
    if sort not in SORT_ORDERS:
        sort = DEFAULT_SORT
    entries = request.user.vault_entries.prefetch_related('tags')
    total = entries.count()
    if active_tag is not None:
        entries = entries.filter(tags=active_tag)
    if query:
        entries = entries.filter(
            Q(word__icontains=query)
            | Q(meaning__icontains=query)
            | Q(example__icontains=query)
            | Q(memory_anchor__icontains=query)
        )
    if favorites_only:
        entries = entries.filter(is_favorite=True)
    paginator = Paginator(entries.order_by(*SORT_ORDERS[sort]), ENTRIES_PER_PAGE)
    page = paginator.get_page(request.GET.get('page'))
    filter_tags = [tag for tag in user_tags if tag.entry_count or tag == active_tag]
    for tag in filter_tags:
        tag.filter_url = list_url(query, favorites_only, tag, sort)
    page_query = list_url(query, favorites_only, active_tag, sort).partition('?')[2]
    context = {
        'page': page,
        'total': total,
        'result_total': paginator.count,
        'active_tag': active_tag,
        'filter_tags': filter_tags,
        'has_tags': bool(user_tags),
        'query': query,
        'favorites_only': favorites_only,
        'sort': sort,
        'sort_choices': SORT_CHOICES,
        'filters_active': bool(query or favorites_only or active_tag),
        'all_tags_url': list_url(query, favorites_only, None, sort),
        'favorites_url': list_url(query, not favorites_only, active_tag, sort),
        'page_query': f'&{page_query}' if page_query else '',
    }
    return render(request, 'vault/entry_list.html', context)


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
    next_url = request.POST.get('next', '')
    if next_url.startswith('/') and url_has_allowed_host_and_scheme(next_url, allowed_hosts=None):
        return redirect(next_url)
    return redirect('vault:list')


@login_required
@role_required(User.Role.LEARNER)
def tag_list(request):
    tags = request.user.vault_tags.annotate(entry_count=Count('entries'))
    return render(request, 'vault/tag_list.html', {'tags': tags})


@login_required
@role_required(User.Role.LEARNER)
def tag_delete(request, pk):
    tag = get_object_or_404(
        VaultTag.objects.annotate(entry_count=Count('entries')),
        pk=pk,
        user=request.user,
    )
    if request.method == 'POST':
        name = tag.name
        tag.delete()
        messages.success(request, f'Tag "{name}" was deleted. Your words were kept.')
        return redirect('vault:tag_list')
    return render(request, 'vault/tag_confirm_delete.html', {'tag': tag})


@login_required
@role_required(User.Role.ADMIN)
def admin_entry_list(request):
    query = request.GET.get('q', '').strip()[:ADMIN_SEARCH_MAX_LENGTH]
    entries = (
        VaultEntry.objects
        .select_related('user')
        .only('word', 'created_at', 'user__username')
        .prefetch_related('tags')
        .order_by('-created_at', '-pk')
    )
    if query:
        entries = entries.filter(Q(word__icontains=query) | Q(user__username__icontains=query))
    paginator = Paginator(entries, ADMIN_ENTRIES_PER_PAGE)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'vault/admin_entry_list.html', {'page': page, 'query': query, 'total': paginator.count})


def get_admin_entry(pk):
    return get_object_or_404(
        VaultEntry.objects
        .select_related('user')
        .only(
            'word', 'meaning', 'example', 'memory_anchor', 'is_favorite',
            'created_at', 'updated_at', 'user__username',
        ),
        pk=pk,
    )


@login_required
@role_required(User.Role.ADMIN)
def admin_entry_detail(request, pk):
    entry = get_admin_entry(pk)
    return render(request, 'vault/admin_entry_detail.html', {'entry': entry, 'tags': list(entry.tags.all())})


@login_required
@role_required(User.Role.ADMIN)
def admin_entry_delete(request, pk):
    entry = get_admin_entry(pk)
    if request.method == 'POST':
        word = entry.word
        username = entry.user.username
        entry.delete()
        messages.success(request, f'Entry "{word}" by {username} was removed.')
        return redirect('vault:admin_entry_list')
    return render(request, 'vault/admin_entry_confirm_delete.html', {'entry': entry})
