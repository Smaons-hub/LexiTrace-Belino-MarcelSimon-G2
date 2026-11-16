from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from vault.models import VaultEntry, VaultTag

from .models import User

RECENT_WORDS_SHOWN = 3
TOP_LEARNERS_SHOWN = 5


def get_daily_review(user):
    entries = user.vault_entries.order_by('pk')
    count = entries.count()
    if not count:
        return None
    index = (timezone.localdate().toordinal() + user.pk) % count
    return entries[index]


def get_vault_summary(user):
    counts = user.vault_entries.aggregate(
        words=Count('pk'),
        favorites=Count('pk', filter=Q(is_favorite=True)),
    )
    recent = []
    if counts['words']:
        recent = list(user.vault_entries.order_by('-created_at', '-pk')[:RECENT_WORDS_SHOWN])
    return {
        'words': counts['words'],
        'favorites': counts['favorites'],
        'tags': user.vault_tags.count(),
        'recent': recent,
    }


def get_vault_overview():
    week_ago = timezone.now() - timedelta(days=7)
    totals = VaultEntry.objects.aggregate(
        words=Count('pk'),
        words_this_week=Count('pk', filter=Q(created_at__gte=week_ago)),
    )
    top_learners = (
        User.objects
        .filter(role=User.Role.LEARNER)
        .annotate(word_count=Count('vault_entries'))
        .filter(word_count__gt=0)
        .only('username')
        .order_by('-word_count', 'username')[:TOP_LEARNERS_SHOWN]
    )
    return {
        'words': totals['words'],
        'words_this_week': totals['words_this_week'],
        'tags': VaultTag.objects.count(),
        'top_learners': list(top_learners),
    }
